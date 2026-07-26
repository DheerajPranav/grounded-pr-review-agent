"""diffing — parse unified diffs into files/hunks/changed-lines. Depends only on models/core."""

from myers.diffing.parser import (
    AddedLine,
    DiffFile,
    Hunk,
    ParsedDiff,
    parse_unified_diff,
)

__all__ = ["AddedLine", "DiffFile", "Hunk", "ParsedDiff", "parse_unified_diff"]
