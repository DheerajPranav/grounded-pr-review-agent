"""The deterministic baseline reviewer (M1).

The baseline we preserve and must beat. No LLM, no reasoning — pure static checks over the
diff's added lines, plus one whole-diff heuristic (missing tests). Every rule is regex-certain,
so findings are DETERMINISTIC: the same diff always yields the same findings, in the same order.

Each rule already carries the Category (security/quality/tests/docs) that its future LLM
specialist will own, so the M3 fan-out inherits this taxonomy directly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from myers.agents.base import Agent
from myers.diffing.parser import ParsedDiff
from myers.models import AgentType, Category, Evidence, Finding, Severity

_MAX_LINE_LEN = 120


@dataclass(frozen=True)
class LineRule:
    rule_id: str
    pattern: re.Pattern[str]
    category: Category
    severity: Severity
    confidence: float
    summary: str
    suggestion: str


# Ordered, deterministic rule table. Confidence reflects regex certainty, not importance.
_LINE_RULES: tuple[LineRule, ...] = (
    # --- security: CRITICAL -------------------------------------------------
    LineRule("merge-conflict-marker", re.compile(r"^(<<<<<<< |=======$|>>>>>>> )"),
             Category.SECURITY, Severity.CRITICAL, 0.99,
             "Unresolved merge conflict marker committed.",
             "Resolve the conflict and remove the marker before merging."),
    LineRule("hardcoded-aws-key", re.compile(r"AKIA[0-9A-Z]{16}"),
             Category.SECURITY, Severity.CRITICAL, 0.97,
             "Hardcoded AWS access key id.",
             "Move the credential to a secret manager / env var and rotate it."),
    LineRule("hardcoded-openai-key", re.compile(r"sk-[A-Za-z0-9]{20,}"),
             Category.SECURITY, Severity.CRITICAL, 0.95,
             "Hardcoded API key (sk-...).",
             "Load from an environment variable; rotate the exposed key."),
    LineRule("private-key-material", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
             Category.SECURITY, Severity.CRITICAL, 0.98,
             "Private key material committed to the diff.",
             "Never commit private keys; rotate and store in a secret manager."),
    LineRule("hardcoded-secret-assign",
             re.compile(r"""(?i)(password|passwd|secret|api[_-]?key|access[_-]?token)\s*[=:]\s*['"][^'"]{6,}['"]"""),
             Category.SECURITY, Severity.CRITICAL, 0.80,
             "Possible hardcoded secret in an assignment.",
             "Load secrets from configuration/env, not source."),
    # --- security: HIGH -----------------------------------------------------
    LineRule("dynamic-eval", re.compile(r"\b(?:eval|exec)\s*\("),
             Category.SECURITY, Severity.HIGH, 0.75,
             "Use of eval()/exec() on possibly untrusted input.",
             "Avoid dynamic execution; parse/validate explicitly."),
    LineRule("shell-true", re.compile(r"shell\s*=\s*True"),
             Category.SECURITY, Severity.HIGH, 0.80,
             "subprocess with shell=True (command-injection risk).",
             "Pass an argument list and shell=False."),
    LineRule("sql-string-concat",
             re.compile(r"""(?i)(select|insert|update|delete)\b.*(\+\s*\w+|%\s*\w+|\{[^}]+\}|f['"])"""),
             Category.SECURITY, Severity.HIGH, 0.60,
             "SQL built by string concatenation/interpolation (injection risk).",
             "Use parameterized queries / bound parameters."),
    LineRule("react-dangerous-html", re.compile(r"dangerouslySetInnerHTML"),
             Category.SECURITY, Severity.HIGH, 0.85,
             "dangerouslySetInnerHTML can introduce XSS.",
             "Sanitize input or render as text."),
    LineRule("tls-verify-disabled", re.compile(r"verify\s*=\s*False|rejectUnauthorized\s*:\s*false"),
             Category.SECURITY, Severity.HIGH, 0.85,
             "TLS certificate verification disabled.",
             "Enable certificate verification."),
    LineRule("insecure-deserialize", re.compile(r"\b(?:pickle\.loads|yaml\.load)\s*\("),
             Category.SECURITY, Severity.HIGH, 0.70,
             "Insecure deserialization of possibly untrusted data.",
             "Use safe loaders (e.g. yaml.safe_load) / validated schemas."),
    # --- quality: MEDIUM ----------------------------------------------------
    LineRule("bare-except", re.compile(r"except\s*:\s*(#.*)?$"),
             Category.QUALITY, Severity.MEDIUM, 0.90,
             "Bare except swallows all exceptions (including KeyboardInterrupt).",
             "Catch specific exception types."),
    LineRule("except-pass", re.compile(r"except[^:]*:\s*pass\b"),
             Category.QUALITY, Severity.MEDIUM, 0.70,
             "Exception silently swallowed with pass.",
             "Handle or log the exception."),
    # --- quality: LOW -------------------------------------------------------
    LineRule("debug-print",
             re.compile(r"\b(?:console\.log|System\.out\.println|print)\s*\(|(^|\s)debugger\s*;"),
             Category.QUALITY, Severity.LOW, 0.55,
             "Debug/log statement left in the diff.",
             "Remove or route through the logger before merge."),
    LineRule("todo-marker", re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b"),
             Category.QUALITY, Severity.LOW, 0.85,
             "TODO/FIXME marker added.",
             "File a ticket or resolve before merge."),
    # --- docs ---------------------------------------------------------------
    LineRule("new-symbol-undocumented",
             re.compile(r"^\s*(?:def|function|func|public\s+\w+|def\s+)\s*\w+\s*\("),
             Category.DOCS, Severity.LOW, 0.45,
             "New function/method added; confirm it is documented.",
             "Add a docstring/comment describing intent, inputs, and outputs."),
)


class BaselineAgent(Agent):
    name = "baseline"

    def review(self, diff: ParsedDiff) -> list[Finding]:
        findings: list[Finding] = []
        for path, added in diff.added_lines:
            text = added.content
            for rule in _LINE_RULES:
                if rule.pattern.search(text):
                    findings.append(self._make(rule, path, added.lineno, text))
            if len(text.rstrip("\n")) > _MAX_LINE_LEN:
                findings.append(self._long_line(path, added.lineno, text))

        findings.extend(self._missing_tests(diff))
        findings.sort(key=lambda f: f.sort_key)
        return findings

    # -- rule constructors ---------------------------------------------------
    def _make(self, rule: LineRule, path: str, lineno: int, text: str) -> Finding:
        return Finding(
            rule_id=rule.rule_id,
            agent_type=AgentType.BASELINE,
            category=rule.category,
            severity=rule.severity,
            summary=rule.summary,
            file_path=path,
            line_start=lineno,
            line_end=lineno,
            suggestion=rule.suggestion,
            rationale=f"Deterministic static check '{rule.rule_id}' matched the added line.",
            confidence=rule.confidence,
            evidence=[Evidence(file_path=path, line=lineno, snippet=text, source="diff")],
        )

    def _long_line(self, path: str, lineno: int, text: str) -> Finding:
        return Finding(
            rule_id="line-too-long",
            agent_type=AgentType.BASELINE,
            category=Category.QUALITY,
            severity=Severity.INFO,
            summary=f"Line exceeds {_MAX_LINE_LEN} characters.",
            file_path=path,
            line_start=lineno,
            line_end=lineno,
            suggestion="Wrap or refactor the long line.",
            rationale="Style: long lines hurt reviewability.",
            confidence=0.99,
            evidence=[Evidence(file_path=path, line=lineno, snippet=text[:120], source="diff")],
        )

    def _missing_tests(self, diff: ParsedDiff) -> list[Finding]:
        """Whole-diff heuristic: source changed but no test file touched.

        Lower confidence (0.5) because it is a heuristic, not a certainty — exactly the kind
        of signal that in later milestones is a candidate for human review, not an auto-block.
        """
        def is_test(p: str) -> bool:
            pl = p.lower()
            return any(t in pl for t in ("test", "spec", "__tests__")) or pl.endswith(
                (".test.js", ".test.ts", ".spec.js", ".spec.ts", "_test.go", "_test.py")
            )

        code_files = [f for f in diff.files if not f.is_binary and not f.is_deleted and not is_test(f.path)]
        test_files = [f for f in diff.files if is_test(f.path)]
        if code_files and not test_files:
            first = min(code_files, key=lambda f: f.path)
            return [Finding(
                rule_id="no-tests-for-change",
                agent_type=AgentType.BASELINE,
                category=Category.TESTS,
                severity=Severity.MEDIUM,
                summary="Source files changed but no test file was added or updated.",
                file_path=first.path,
                line_start=1,
                line_end=1,
                suggestion="Add or update tests covering the changed behavior.",
                rationale=f"{len(code_files)} non-test file(s) changed; 0 test files touched.",
                confidence=0.5,
                evidence=[Evidence(file_path=first.path, line=1,
                                   snippet="(no corresponding test change)", source="diff")],
            )]
        return []
