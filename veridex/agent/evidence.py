"""Deterministic evidence and policy checks for the demonstration.

No model or scanner is invoked here. Review narratives are explicitly scripted.
"""
from __future__ import annotations
import ast
import difflib
import json
from datetime import datetime, timezone
from pathlib import Path


def syntax_result(source: str) -> dict:
    try:
        ast.parse(source)
        return {"passed": True, "detail": "Python AST parse passed; code was not executed."}
    except SyntaxError as exc:
        return {"passed": False, "detail": f"{type(exc).__name__}: {exc.msg} (line {exc.lineno})"}


def imports(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split('.')[0])
    return names


def policy_check(before: str, after: str, minimal_changes: bool, no_new_imports: bool) -> list[dict]:
    checks = []
    try:
        ast.parse(before)
        ast.parse(after)
    except (SyntaxError, ValueError, RecursionError):
        return [{"name": "Syntax prerequisite", "passed": False,
                 "detail": "Policy evaluation requires valid original and candidate Python."}]
    if no_new_imports:
        added = sorted(imports(after) - imports(before))
        checks.append({"name": "No new imports", "passed": not added,
                       "detail": "No imports added" if not added else "Added imports: " + ', '.join(added)})
    if minimal_changes:
        diff = list(difflib.ndiff(before.splitlines(), after.splitlines()))
        changes = sum(line.startswith(('+ ', '- ')) for line in diff)
        # Heuristic, not proof of semantic minimality.
        limit = max(12, int(len(before.splitlines()) * 0.75))
        checks.append({"name": "Small diff (heuristic)", "passed": changes <= limit,
                       "detail": f"{changes} changed lines; demonstration threshold {limit}. This does not prove minimal semantics."})
    return checks


def patch_text(before: str, after: str, relative_path: str) -> str:
    path = Path(relative_path)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError('Invalid patch path')
    return ''.join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                    fromfile=f'a/{path.as_posix()}', tofile=f'b/{path.as_posix()}'))


def evidence_passport(before: str, after: str, policy: list[dict], review: dict, events: list[dict],
                      finding: dict, mode: str = 'SIMULATED') -> dict:
    if mode != 'SIMULATED':
        raise ValueError('Demo passport supports SIMULATED only; live exports require backend.exports.')
    return {
        'product': 'Veridex Glass Box', 'mode': mode,
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'finding': finding,
        'source': {'path': 'tests/vulnerable_sample.py', 'original_unchanged': True},
        'syntax_check': syntax_result(after),
        'opengrep_rescan': {'executed': False, 'status': 'NOT RUN'},
        'policy_checks': policy,
        'adversarial_review': review,
        'activity_events': events,
        'patch': patch_text(before, after, 'tests/vulnerable_sample.py'),
        'limitations': [
            'Nemotron was not called; review narrative and investigation events are scripted.',
            'OpenGrep was not run; no scanner-clearance claim is established.',
            'AST parsing checks syntax only, not behavioral correctness or security.',
            'Review and developer testing are required before applying a patch.'
        ]
    }


def passport_json(*args, **kwargs) -> str:
    return json.dumps(evidence_passport(*args, **kwargs), indent=2, ensure_ascii=False)
