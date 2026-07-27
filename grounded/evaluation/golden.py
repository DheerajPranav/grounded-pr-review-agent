"""Golden PR loader.

A golden case = a diff + the set of issues a correct reviewer should raise, each labeled
by (category, file_path, line_start). Matching on category (not the mode-specific rule_id)
lets a regex baseline and an LLM be scored on the SAME ground truth. Cases live as pairs
under evaluation/golden/:
    <name>.diff            the pull-request diff
    <name>.expected.json   {"expected": [{"category","file_path","line_start", ...}, ...]}
A clean case with an empty expected list guards against false positives.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

_GOLDEN_DIR = Path(__file__).parent / "golden"


@dataclass(frozen=True)
class GoldenCase:
    name: str
    diff_text: str
    expected: frozenset[tuple[str, str, int]]  # (category, file_path, line_start)


def load_golden_cases(directory: Path | None = None) -> list[GoldenCase]:
    d = directory or _GOLDEN_DIR
    cases: list[GoldenCase] = []
    for diff_path in sorted(d.glob("*.diff")):
        exp_path = diff_path.with_suffix(".expected.json")
        expected: set[tuple[str, str, int]] = set()
        if exp_path.exists():
            data = json.loads(exp_path.read_text(encoding="utf-8"))
            for e in data.get("expected", []):
                expected.add((e["category"], e["file_path"], int(e["line_start"])))
        cases.append(GoldenCase(
            name=diff_path.stem,
            diff_text=diff_path.read_text(encoding="utf-8"),
            expected=frozenset(expected),
        ))
    return cases
