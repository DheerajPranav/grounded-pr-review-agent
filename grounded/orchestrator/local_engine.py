"""LocalFanoutEngine — an in-process implementation of core.workflow_engine.

Runs the specialist nodes in PARALLEL (the M3 fan-out) with a per-node timeout, so one
stalled or failing specialist cannot hang the join — the review completes with partial
results and a recorded degradation (degrade slower-but-correct). State is checkpointed per
workflow_id so a caller can inspect/resume completed nodes.

This is the local realization of the LangGraph Send-API fan-out described in the architecture
(ADR-001). All orchestrator code depends only on core.workflow_engine; swapping in a LangGraph
or Temporal engine at scale changes this one file.
"""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Any

from grounded.agents.base import Agent
from grounded.core.context import ReviewContext
from grounded.core.workflow_engine import WorkflowEngine
from grounded.models import Finding


@dataclass
class FanoutInput:
    agents: list[Agent]
    diff: Any
    context_for: Callable[[str], ReviewContext]
    emit_span: Callable[..., None] = lambda **kw: None


@dataclass
class FanoutResult:
    results: dict[str, list[Finding]] = field(default_factory=dict)
    degraded: list[str] = field(default_factory=list)


class LocalFanoutEngine(WorkflowEngine):
    def __init__(self, node_timeout_s: float = 30.0) -> None:
        self.node_timeout_s = node_timeout_s
        self._state: dict[str, FanoutResult] = {}

    def run(self, workflow_id: str, input: FanoutInput) -> FanoutResult:
        result = FanoutResult()
        agents = input.agents
        if not agents:
            self._state[workflow_id] = result
            return result

        with ThreadPoolExecutor(max_workers=len(agents)) as ex:
            futures = {}
            for agent in agents:
                input.emit_span(agent=agent.name, event_type="span.start")
                futures[agent] = ex.submit(agent.review, input.diff, input.context_for(agent.name))
            # Gather. Each result() waits up to the timeout; work already runs in parallel.
            for agent, fut in futures.items():
                try:
                    findings = fut.result(timeout=self.node_timeout_s)
                    result.results[agent.name] = findings
                    input.emit_span(agent=agent.name, event_type="span.end",
                                    payload={"n_findings": len(findings)})
                except FuturesTimeout:
                    result.degraded.append(f"{agent.name}: timeout")
                    input.emit_span(agent=agent.name, event_type="span.end",
                                    outcome="degraded", payload={"error": "timeout"})
                except Exception as exc:  # degrade, never crash the review
                    result.degraded.append(f"{agent.name}: {type(exc).__name__}")
                    input.emit_span(agent=agent.name, event_type="span.end",
                                    outcome="degraded", payload={"error": type(exc).__name__})

        self._state[workflow_id] = result
        return result

    def resume(self, workflow_id: str, state: Any) -> Any:
        # Greenfield local engine: resume returns the checkpointed partial state, if any.
        return self._state.get(workflow_id, state)

    def get_state(self, workflow_id: str) -> Any:
        return self._state.get(workflow_id)
