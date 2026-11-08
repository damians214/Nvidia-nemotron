"""Measured syntax, import, scope, and structural integrity gates."""
from __future__ import annotations

import ast
import difflib
import re

from backend.contracts import Check, Policies
from workspace.manager import digest


def checked(name: str, passed: bool, details: str, candidate_hash: str) -> Check:
    return Check(name=name, executed=True, passed=passed, status="PASS" if passed else "FAIL",
                 details=details, candidate_hash=candidate_hash)


def import_set(tree: ast.AST) -> set[str]:
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            result.add("." * node.level + (node.module or ""))
    return result


def definitions(tree: ast.AST) -> set[tuple[str, int]]:
    return {(node.name, len(node.args.args) + len(node.args.posonlyargs)) for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def call_target(node: ast.AST) -> str:
    # Strip arguments from chained calls: adding SQL bound parameters must not
    # appear to remove execute(...).fetchone().
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return call_target(node.value) + "." + node.attr
    if isinstance(node, ast.Call):
        return call_target(node.func) + "()"
    return type(node).__name__


def validate_candidate(before: str, after: str, policies: Policies) -> list[Check]:
    candidate_hash = digest(after.encode())
    try:
        original = ast.parse(before)
        patched = ast.parse(after)
    except (SyntaxError, ValueError, RecursionError):
        return [checked("Python syntax", False, "Candidate or baseline is not valid Python; no code executed.", candidate_hash),
                Check(name="Policies", details="Not evaluated after syntax failure", candidate_hash=candidate_hash)]
    checks = [checked("Python syntax", True, "AST parsed; code was not executed.", candidate_hash)]
    if policies.no_new_imports:
        additions = import_set(patched) - import_set(original)
        checks.append(checked("No new imports", not additions,
                              "AST import set comparison, including relative imports.", candidate_hash))
    if policies.minimal_diff:
        changes = sum(line.startswith(("+ ", "- ")) for line in difflib.ndiff(before.splitlines(), after.splitlines()))
        checks.append(checked("Small diff", changes <= policies.max_changed_lines,
                              f"{changes} added/removed lines; limit {policies.max_changed_lines}. Heuristic only.", candidate_hash))
    # Reject suppression even if a scanner would otherwise report zero findings.
    suppression = re.compile(r"nosem(?:grep)?|opengrep[-_ ]?ignore|semgrep[-_ ]?ignore|\bnoqa\b", re.I)
    added = "\n".join(line[2:] for line in difflib.ndiff(before.splitlines(), after.splitlines()) if line.startswith("+ "))
    checks.append(checked("No suppression", not suppression.search(added),
                          "Reject new suppression annotations and ignore directives.", candidate_hash))
    intact = definitions(original) <= definitions(patched)
    # This is a conservative guard, not behavioral equivalence. The reviewer checks semantics.
    old_checks = [ast.dump(n.test) for n in ast.walk(original) if isinstance(n, (ast.If, ast.Assert))]
    new_checks = [ast.dump(n.test) for n in ast.walk(patched) if isinstance(n, (ast.If, ast.Assert))]
    intact = intact and all(test in new_checks for test in old_checks)
    old_calls = {call_target(n.func) for n in ast.walk(original) if isinstance(n, ast.Call)}
    new_calls = {call_target(n.func) for n in ast.walk(patched) if isinstance(n, ast.Call)}
    intact = intact and old_calls <= new_calls
    checks.append(checked("Structural integrity", intact,
                          "Preserve function names/arity, condition checks, and call targets; heuristic, not behavior proof.", candidate_hash))
    return checks
