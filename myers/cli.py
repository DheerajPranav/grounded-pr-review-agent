"""CLI — the local demo entrypoint. Runs with zero external services.

    python -m myers review <diff-file> [--mode baseline|llm|specialists]
    python -m myers eval [--report] [--min-precision F]
    python -m myers trace <review_id>            (M4)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from myers.agents import BaselineAgent
from myers.evaluation import evaluate
from myers.models import Decision
from myers.orchestrator import ReviewPipeline


def _agents_for_mode(mode: str):
    if mode == "baseline":
        return [BaselineAgent()], "baseline"
    if mode in ("llm", "specialists"):
        # M2/M3: real LLM reviewer / four grounded specialists behind core.llm + workflow_engine.
        raise SystemExit(
            f"mode '{mode}' arrives in a later milestone (see .genesis/PLAN.md). "
            f"'baseline' is implemented and runs today."
        )
    raise SystemExit(f"unknown mode: {mode}")


def cmd_review(args) -> int:
    diff_path = Path(args.diff)
    if not diff_path.exists():
        print(f"error: no such diff file: {diff_path}", file=sys.stderr)
        return 2
    agents, mode = _agents_for_mode(args.mode)
    pipeline = ReviewPipeline(agents, mode)
    review = pipeline.review_text(diff_path.read_text(encoding="utf-8"))
    print(review.render())
    if args.emit_events:
        pipeline.events.flush_jsonl(args.emit_events)
        print(f"\n[events -> {args.emit_events}]")
    # CI-friendly exit code: 0 clean, 1 changes/escalation requested.
    return 0 if (review.decision is Decision.APPROVE and not review.escalated) else 1


def cmd_eval(args) -> int:
    agents, mode = _agents_for_mode(args.mode)
    report = evaluate(agents, mode)
    print(report.render())
    if args.min_precision is not None and report.precision < args.min_precision:
        print(f"\nREGRESSION GATE FAILED: precision {report.precision:.2f} "
              f"< min {args.min_precision:.2f}", file=sys.stderr)
        return 1
    return 0


def cmd_trace(args) -> int:
    print("trace: the event-spine trace viewer arrives at M4 (see .genesis/PLAN.md).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="myers", description="Selective, grounded, failure-aware PR reviewer.")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("review", help="review a unified diff file")
    r.add_argument("diff")
    r.add_argument("--mode", default="baseline", choices=["baseline", "llm", "specialists"])
    r.add_argument("--emit-events", metavar="PATH", help="flush the event spine to a JSONL file")
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("eval", help="score the golden PRs")
    e.add_argument("--mode", default="baseline", choices=["baseline", "llm", "specialists"])
    e.add_argument("--report", action="store_true", help="(reserved) write a persisted report")
    e.add_argument("--min-precision", type=float, default=None, help="regression gate threshold")
    e.set_defaults(func=cmd_eval)

    t = sub.add_parser("trace", help="reconstruct a review from the event spine (M4)")
    t.add_argument("review_id")
    t.set_defaults(func=cmd_trace)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
