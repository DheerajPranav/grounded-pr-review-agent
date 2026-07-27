"""Enforce the ADR-002 dependency rule: core depends on nothing; every module imports inward only.

Layers (rank): a module may import grounded.X only when rank(X) <= rank(importer). ``core`` (rank 0)
may not import any grounded.* module at all. Delete any outer module and the inner ones still import.
"""

import ast
from pathlib import Path

_MYERS = Path(__file__).resolve().parent.parent / "grounded"

_RANK = {
    "core": 0,
    "models": 1,
    "diffing": 2,
    "observability": 2,
    "tools": 2,
    "memory": 2,
    "security": 2,
    "agents": 3,
    "aggregation": 3,
    "economics": 3,
    "hitl": 3,
    "integrations": 3,
    "webhook_receiver": 3,
    "orchestrator": 4,
    "evaluation": 4,
    "cli": 5,
    "__main__": 5,
    "job_queue": 5,
    "api": 6,
}


def _top_pkg(path: Path) -> str:
    rel = path.relative_to(_MYERS)
    return rel.parts[0] if len(rel.parts) > 1 else rel.stem


def _imported_grounded_pkgs(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    pkgs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("grounded"):
            parts = node.module.split(".")
            if len(parts) >= 2:
                pkgs.add(parts[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("grounded."):
                    pkgs.add(alias.name.split(".")[1])
    return pkgs


def test_dependency_rule_holds():
    violations = []
    for py in _MYERS.rglob("*.py"):
        importer = _top_pkg(py)
        importer_rank = _RANK.get(importer)
        if importer_rank is None:
            continue
        for dep in _imported_grounded_pkgs(py):
            dep_rank = _RANK.get(dep)
            if dep_rank is None or dep == importer:
                continue
            if dep_rank > importer_rank:
                violations.append(f"{py.relative_to(_MYERS)}: {importer}(r{importer_rank}) -> {dep}(r{dep_rank})")
    assert not violations, "inward-only dependency rule broken:\n" + "\n".join(violations)


def test_core_imports_no_grounded_module():
    for py in (_MYERS / "core").rglob("*.py"):
        assert _imported_grounded_pkgs(py) == set(), f"core must depend on nothing: {py.name}"
