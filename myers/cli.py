"""CLI — the local demo entrypoint. Runs with zero external services.

    python -m myers review <diff-file> [--mode baseline|llm|specialists]
    python -m myers eval [--report] [--min-precision F]
    python -m myers trace <review_id>            (M4)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from myers.agents import BaselineAgent, LLMReviewAgent, build_specialists
from myers.evaluation import evaluate
from myers.hitl import ApprovalQueue, TicketStatus
from myers.models import Decision
from myers.orchestrator import ReviewPipeline


def _groq_client():
    from myers.tools import GroqLLMClient
    try:
        return GroqLLMClient()
    except RuntimeError as exc:
        raise SystemExit(str(exc))


def _agents_for_mode(mode: str):
    if mode == "baseline":
        return [BaselineAgent()], "baseline"
    if mode == "llm":
        # One LLM reviewer, backed by Groq (free tier). FakeLLM is used only in tests.
        return [LLMReviewAgent(_groq_client())], "llm"
    if mode == "specialists":
        # Four grounded specialists (security/quality/tests/docs) fanned out in parallel.
        return build_specialists(_groq_client()), "specialists"
    raise SystemExit(f"unknown mode: {mode}")


def cmd_review(args) -> int:
    diff_path = Path(args.diff)
    if not diff_path.exists():
        print(f"error: no such diff file: {diff_path}", file=sys.stderr)
        return 2
    diff_text = diff_path.read_text(encoding="utf-8")
    agents, mode = _agents_for_mode(args.mode)

    # Build the grounding memory: a real repo snapshot if given, else the diff's own context.
    from myers.diffing import parse_unified_diff
    from myers.memory import InMemoryCodeStore
    store = InMemoryCodeStore()
    if args.repo:
        n = store.ingest_directory(args.repo)
        print(f"[grounding: indexed {n} chunks from {args.repo}]")
    store.ingest_diff_context(parse_unified_diff(diff_text))

    pipeline = ReviewPipeline(agents, mode, daily_cap_usd=args.cap, retriever=store.hybrid_search)
    review = pipeline.review_text(diff_text)
    print(review.render())

    # Confidence-routed HITL: auto-post, or hold for a human.
    ticket = ApprovalQueue(events=pipeline.events).submit(review)
    if ticket.status is TicketStatus.PENDING:
        print(f"\n[HITL] queued for human approval — {ticket.reason}")
    else:
        print("\n[HITL] auto-posted (confident, no CRITICAL, no injection)")

    if args.emit_events:
        pipeline.events.flush_jsonl(args.emit_events)
        print(f"[events -> {args.emit_events}]  (reconstruct with: myers trace {review.review_id} --events {args.emit_events})")
    # CI-friendly exit code: 0 clean, 1 changes/escalation requested.
    return 0 if (review.decision is Decision.APPROVE and not review.escalated) else 1


def cmd_eval(args) -> int:
    agents, mode = _agents_for_mode(args.mode)
    report = evaluate(agents, mode, daily_cap_usd=args.cap)
    print(report.render())
    if args.report:
        import json
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        print(f"\n[report -> {args.report}]")
    if args.min_precision is not None and report.precision < args.min_precision:
        print(f"\nREGRESSION GATE FAILED: precision {report.precision:.2f} "
              f"< min {args.min_precision:.2f}", file=sys.stderr)
        return 1
    return 0


def cmd_trace(args) -> int:
    from myers.observability.trace import load_events, render_trace
    if not args.events:
        print("error: pass --events PATH (write it during review with --emit-events PATH)", file=sys.stderr)
        return 2
    if not Path(args.events).exists():
        print(f"error: no such events file: {args.events}", file=sys.stderr)
        return 2
    print(render_trace(load_events(args.events), args.review_id))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="myers", description="Selective, grounded, failure-aware PR reviewer.")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("review", help="review a unified diff file")
    r.add_argument("diff")
    r.add_argument("--mode", default="baseline", choices=["baseline", "llm", "specialists"])
    r.add_argument("--cap", type=float, default=None, metavar="USD",
                   help="daily budget cap; the LLM is hard-blocked once spend reaches it (ADR-004)")
    r.add_argument("--repo", metavar="DIR",
                   help="index this repo snapshot for retrieval grounding (specialists mode)")
    r.add_argument("--emit-events", metavar="PATH", help="flush the event spine to a JSONL file")
    r.set_defaults(func=cmd_review)

    e = sub.add_parser("eval", help="score the golden PRs")
    e.add_argument("--mode", default="baseline", choices=["baseline", "llm", "specialists"])
    e.add_argument("--cap", type=float, default=None, metavar="USD", help="daily budget cap for LLM modes")
    e.add_argument("--report", metavar="PATH", help="write the eval report as JSON to PATH")
    e.add_argument("--min-precision", type=float, default=None, help="regression gate threshold")
    e.set_defaults(func=cmd_eval)

    t = sub.add_parser("trace", help="reconstruct a review from the event spine")
    t.add_argument("review_id")
    t.add_argument("--events", metavar="PATH", help="JSONL events file (from review --emit-events)")
    t.set_defaults(func=cmd_trace)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
