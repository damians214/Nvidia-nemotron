"""Isolated, bounded source snapshots for Veridex investigations."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
from pathlib import Path, PurePosixPath

from backend.contracts import BackendError


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        raise BackendError("Invalid relative path")
    if ("\\" in value or "\x00" in value or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or value.startswith("/") or value.endswith("/") or "//" in value):
        raise BackendError("Noncanonical relative path")
    parts = value.split("/")
    if any(p in ("", ".", "..") for p in parts) or ":" in parts[0]:
        raise BackendError("Unsafe relative path")
    if PurePosixPath(value).as_posix() != value:
        raise BackendError("Noncanonical relative path")
    return value


class Workspace:
    def __init__(self, settings, run_id: str, repository_id: str):
        if repository_id not in settings.repositories:
            raise BackendError("Unknown repository")
        if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", run_id):
            raise BackendError("Invalid run ID")
        self.settings = settings
        self.source = Path(settings.repositories[repository_id]).resolve(strict=True)
        if not self.source.is_dir():
            raise BackendError("Repository is not a directory")
        data_root = Path(settings.data_root).resolve()
        if data_root == self.source or data_root.is_relative_to(self.source):
            raise BackendError("Workspace storage cannot be inside source repository")
        self.root = data_root / "workspaces" / run_id
        self.baseline = self.root / "baseline"

    def _source_files(self):
        """Inventory Python files; reject symlinks/special files, including in subfolders."""
        selected = []
        exclusions = []
        for directory, dirs, files in os.walk(self.source, followlinks=False):
            base = Path(directory)
            for name in list(dirs):
                path = base / name
                rel = path.relative_to(self.source).as_posix()
                if path.is_symlink():
                    raise BackendError("Symlinked directory rejected")
                if name.startswith(".") or name in {"__pycache__", "node_modules", "venv", "dist", "build"}:
                    dirs.remove(name)
                    exclusions.append(rel)
            for name in files:
                path = base / name
                rel = relative_path(path.relative_to(self.source).as_posix())
                info = path.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
                    raise BackendError("Symlink or special file rejected")
                if name.startswith(".") or not name.endswith(".py"):
                    exclusions.append(rel)
                    continue
                selected.append((rel, path))
        return sorted(selected), sorted(exclusions)

    def snapshot(self):
        selected, exclusions = self._source_files()
        if len(selected) > self.settings.max_files:
            raise BackendError("File count limit exceeded")
        manifest = {}
        contents = {}
        total = 0
        for rel, path in selected:
            if path.stat().st_size > self.settings.max_file_bytes:
                raise BackendError("File size limit exceeded")
            data = path.read_bytes()
            if len(data) > self.settings.max_file_bytes:
                raise BackendError("File size limit exceeded")
            total += len(data)
            if total > self.settings.max_total_bytes:
                raise BackendError("Total snapshot size exceeded")
            manifest[rel] = digest(data)
            contents[rel] = data
        if self.root.exists():
            raise BackendError("Workspace already exists")
        self.baseline.mkdir(parents=True, mode=0o700)
        for rel, data in contents.items():
            target = self.baseline / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        return manifest, exclusions

    def read(self, path: str, manifest: dict[str, str]) -> bytes:
        rel = relative_path(path)
        if rel not in manifest:
            raise BackendError("File is outside approved manifest")
        target = self.baseline / rel
        if target.is_symlink() or not target.is_file():
            raise BackendError("Baseline file missing or unsafe")
        data = target.read_bytes()
        if len(data) > self.settings.max_file_bytes or digest(data) != manifest[rel]:
            raise BackendError("Baseline file integrity check failed")
        return data

    def candidate_copy(self, candidate_id: str, path: str, patched_text: str, manifest: dict[str, str]) -> Path:
        rel = relative_path(path)
        self.read(rel, manifest)
        if not isinstance(candidate_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", candidate_id):
            raise BackendError("Invalid candidate ID")
        if not isinstance(patched_text, str) or len(patched_text.encode()) > self.settings.max_file_bytes:
            raise BackendError("Candidate exceeds file limit")
        dest = self.root / "attempts" / candidate_id
        if dest.exists():
            raise BackendError("Candidate already exists")
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(self.baseline, dest, symlinks=False)
        target = dest / rel
        target.write_bytes(patched_text.encode())
        return dest

    def unchanged(self, manifest: dict[str, str]) -> bool:
        try:
            selected, _ = self._source_files()
            if {rel for rel, _ in selected} != set(manifest):
                return False
            return all(digest(path.read_bytes()) == manifest[rel] for rel, path in selected)
        except (BackendError, OSError):
            return False
