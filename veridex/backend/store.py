"""Atomic local run snapshots. A snapshot includes its append-only event history."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from backend.contracts import Run


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        self.path = root / "runs.sqlite3"
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT NOT NULL, body TEXT NOT NULL)")
            db.execute("PRAGMA user_version = 1")
        os.chmod(self.path, 0o600)

    def connection(self):
        return sqlite3.connect(self.path, timeout=10)

    def save(self, run: Run) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO runs VALUES (?, ?, ?) ON CONFLICT(id) DO UPDATE SET body=excluded.body",
                       (run.id, run.created_at, run.model_dump_json()))

    def load(self, run_id: str) -> Run:
        with self.connection() as db:
            row = db.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError("Unknown run")
        return Run.model_validate_json(row[0])

    def recent(self, limit: int = 10) -> list[Run]:
        with self.connection() as db:
            rows = db.execute("SELECT body FROM runs ORDER BY created DESC LIMIT ?", (limit,)).fetchall()
        return [Run.model_validate_json(row[0]) for row in rows]

    def write_artifact(self, run_id: str, name: str, data: bytes) -> Path:
        # IDs and artifact names are backend-generated, never model/user paths.
        from uuid import UUID
        UUID(run_id)
        if name not in {"passport.json", "candidate.patch"}:
            raise ValueError("Unsupported artifact")
        directory = self.root / "artifacts" / run_id
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(dir=directory, delete=False) as temp:
            temp.write(data)
            temp.flush()
            os.fsync(temp.fileno())
        target = directory / name
        os.replace(temp.name, target)
        return target
