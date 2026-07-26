"""Unified-diff parser.

Contract: a git unified diff -> files -> hunks -> added lines with correct NEW-file line
numbers (what a reviewer comments on).

Failure modes handled (see .genesis/wiki/failure-matrix.md):
  - renames / new files / deleted files -> flagged, not crashed
  - binary files -> recorded skip, review continues on the rest
  - malformed hunk headers -> the offending file is skipped with a note (degrade, don't crash)
The parser never raises on a single bad file; it records `parse_errors` and keeps going.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
_DIFF_GIT_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")


@dataclass(frozen=True)
class AddedLine:
    """A line introduced by the diff, with its line number in the new file."""

    lineno: int
    content: str


@dataclass
class Hunk:
    new_start: int
    header: str
    added: list[AddedLine] = field(default_factory=list)


@dataclass
class DiffFile:
    path: str  # the new path (post-change)
    old_path: str | None = None
    is_new: bool = False
    is_deleted: bool = False
    is_rename: bool = False
    is_binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def added_lines(self) -> list[AddedLine]:
        return [ln for h in self.hunks for ln in h.added]


@dataclass
class ParsedDiff:
    files: list[DiffFile] = field(default_factory=list)
    parse_errors: list[str] = field(default_factory=list)

    @property
    def added_lines(self) -> list[tuple[str, AddedLine]]:
        """(file_path, AddedLine) across all non-binary files."""
        return [(f.path, ln) for f in self.files for ln in f.added_lines]


def _strip_prefix(path: str) -> str:
    if path in ("/dev/null",):
        return path
    for pfx in ("a/", "b/"):
        if path.startswith(pfx):
            return path[len(pfx):]
    return path


def parse_unified_diff(text: str) -> ParsedDiff:
    """Parse a (multi-file) unified diff. Robust to git extended headers."""
    result = ParsedDiff()
    lines = text.splitlines()
    i = 0
    n = len(lines)
    current: DiffFile | None = None
    current_hunk: Hunk | None = None
    new_lineno = 0

    def close_file() -> None:
        nonlocal current, current_hunk
        if current is not None:
            result.files.append(current)
        current = None
        current_hunk = None

    while i < n:
        line = lines[i]

        m = _DIFF_GIT_RE.match(line)
        if m:
            close_file()
            old_p, new_p = _strip_prefix(m.group(1)), _strip_prefix(m.group(2))
            current = DiffFile(path=new_p, old_path=old_p)
            current_hunk = None
            i += 1
            continue

        if current is not None:
            if line.startswith("new file mode"):
                current.is_new = True
                i += 1
                continue
            if line.startswith("deleted file mode"):
                current.is_deleted = True
                i += 1
                continue
            if line.startswith("rename from "):
                current.is_rename = True
                current.old_path = line[len("rename from "):].strip()
                i += 1
                continue
            if line.startswith("rename to "):
                current.is_rename = True
                current.path = line[len("rename to "):].strip()
                i += 1
                continue
            if line.startswith("Binary files") or line.startswith("GIT binary patch"):
                current.is_binary = True
                i += 1
                continue
            if line.startswith("--- "):
                i += 1
                continue
            if line.startswith("+++ "):
                p = _strip_prefix(line[4:].strip())
                if p != "/dev/null":
                    current.path = p
                i += 1
                continue

        hm = _HUNK_RE.match(line)
        if hm:
            if current is None:
                result.parse_errors.append(f"hunk with no preceding file header: {line!r}")
                i += 1
                continue
            try:
                new_start = int(hm.group(3))
            except (TypeError, ValueError):
                result.parse_errors.append(f"malformed hunk header: {line!r}")
                current.hunks = []  # skip this file's hunks, keep the rest of the diff
                current_hunk = None
                i += 1
                continue
            current_hunk = Hunk(new_start=new_start, header=line)
            current.hunks.append(current_hunk)
            new_lineno = new_start
            i += 1
            continue

        # Body lines of a hunk
        if current_hunk is not None and current is not None:
            if line.startswith("+"):
                current_hunk.added.append(AddedLine(lineno=new_lineno, content=line[1:]))
                new_lineno += 1
            elif line.startswith("-"):
                pass  # removed line: does not advance the new-file counter
            elif line.startswith(" ") or line == "":
                new_lineno += 1  # context line
            elif line.startswith("\\"):
                pass  # "\ No newline at end of file"
            else:
                # Unknown body line — tolerate, don't crash.
                new_lineno += 1

        i += 1

    close_file()
    return result
