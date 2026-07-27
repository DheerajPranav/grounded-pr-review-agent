"""The four specialists (M3). Each is an LLMReviewAgent scoped to one domain, grounded by
hybrid retrieval, running in parallel and merged by the aggregator.

Independent domain prompts (not one prompt asked to do everything) are the defense against
correlated-agent hallucination: four narrow reviewers disagree usefully; the aggregator records
where they agree and keeps the highest-confidence copy.
"""

from __future__ import annotations

from myers.agents.llm_agent import _SYSTEM, LLMReviewAgent
from myers.core.llm import LLMClient
from myers.models import AgentType, Category

_DOMAIN_GUIDANCE: dict[Category, tuple[AgentType, str]] = {
    Category.SECURITY: (AgentType.SECURITY,
        "SECURITY only: injection (SQL/command), hardcoded secrets or credentials, unsafe "
        "eval/exec, insecure deserialization, disabled TLS verification, XSS, SSRF, auth gaps. "
        "Report only security-category findings."),
    Category.QUALITY: (AgentType.QUALITY,
        "CODE QUALITY only: correctness bugs, wrong/broad error handling, resource leaks, "
        "misuse of APIs (e.g. missing required arguments), dead or debug code, readability. "
        "Report only quality-category findings."),
    Category.TESTS: (AgentType.TESTS,
        "TESTS only: missing or inadequate test coverage for the changed behavior, untested "
        "edge cases or error paths. If source changed with no accompanying test, flag it. "
        "Report only tests-category findings."),
    Category.DOCS: (AgentType.DOCS,
        "DOCUMENTATION only: missing or incorrect docstrings/comments for new public functions "
        "or APIs, misleading names, undocumented parameters. Report only docs-category findings."),
}


def build_specialists(client: LLMClient, model: str | None = None,
                      retrieve_k: int = 3) -> list[LLMReviewAgent]:
    specialists: list[LLMReviewAgent] = []
    for category, (agent_type, guidance) in _DOMAIN_GUIDANCE.items():
        specialists.append(LLMReviewAgent(
            client, model=model, agent_type=agent_type, name=agent_type.value,
            system=f"{_SYSTEM}\n\nYOUR DOMAIN — {guidance}",
            only_category=category, retrieve_k=retrieve_k,
        ))
    return specialists
