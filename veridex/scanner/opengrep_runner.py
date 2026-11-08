"""Pinned real scanner with bounded subprocess IO and no repository configuration."""
from __future__ import annotations

import json
import os
import selectors
import signal
import subprocess
import time
from pathlib import Path
from typing import Callable

from backend.config import Settings
from backend.contracts import BackendError, Canceled, Finding, Scan
from workspace.manager import digest, relative_path


class OpenGrep:
    def __init__(self, settings: Settings):
        self.settings = settings

    def scan(self, root: Path, manifest: dict[str, str], cancel: Callable[[], bool] = lambda: False) -> Scan:
        settings = self.settings
        result = Scan()
        started = time.monotonic()
        binary = settings.scanner.resolve()
        if not binary.is_file() or not os.access(binary, os.X_OK):
            raise BackendError("OpenGrep is unavailable. Run scripts/install_opengrep.py first.")
        actual_hash = digest(binary.read_bytes())
        if not settings.scanner_sha256 or actual_hash != settings.scanner_sha256:
            raise BackendError("OpenGrep checksum mismatch or missing pin; reinstall the trusted binary.")
        rules = settings.rules.resolve()
        result.binary_hash = actual_hash
        result.rules_hash = digest(rules.read_bytes())
        env = {key: os.environ[key] for key in ("PATH", "SYSTEMROOT", "TMPDIR", "LANG") if key in os.environ}
        cache = settings.data_root / "scanner-cache"
        cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        env.update({"XDG_CACHE_HOME": str(cache), "SEMGREP_SEND_METRICS": "off", "SEMGREP_ENABLE_VERSION_CHECK": "0",
                    "SEMGREP_LOG_FILE": str(cache / "scanner.log"), "SEMGREP_SETTINGS_FILE": str(cache / "settings.yml")})
        try:
            version = subprocess.run([str(binary), "--experimental", "--version"], cwd=root, env=env, capture_output=True,
                                     timeout=60, check=True, text=True).stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            raise BackendError("OpenGrep version check failed") from exc
        if version != settings.scanner_version:
            raise BackendError("OpenGrep version does not match the tested release")
        result.tool_version = version
        # Only backend-owned rules. Snapshot contains Python files and no ignore/config files.
        options = ["scan", "--json", "--config", str(rules), "--no-git-ignore", "--no-rewrite-rule-ids",
                   "--experimental", "--project-root", ".", "--x-ignore-semgrepignore-files",
                   "--timeout", "10", "--max-memory", "512", "."]
        result.config_hash = digest(json.dumps(options[0:3] + [result.rules_hash] + options[4:]).encode())
        result.command = [str(binary), *options]
        result.executed = True
        chunks = {"out": bytearray(), "err": bytearray()}
        process = subprocess.Popen([str(binary), *options], cwd=root, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ, "out")
                selector.register(process.stderr, selectors.EVENT_READ, "err")
                while selector.get_map():
                    if cancel():
                        raise Canceled("Investigation canceled")
                    if time.monotonic() - started > settings.scan_timeout:
                        raise BackendError("OpenGrep exceeded its execution deadline")
                    for key, _ in selector.select(0.1):
                        data = os.read(key.fileobj.fileno(), 65536)
                        if not data:
                            selector.unregister(key.fileobj)
                        else:
                            chunks[key.data].extend(data)
                            if sum(map(len, chunks.values())) > settings.max_output_bytes:
                                raise BackendError("OpenGrep output limit exceeded")
                result.exit_code = process.wait(timeout=2)
        except Canceled:
            raise
        except (BackendError, OSError, subprocess.SubprocessError) as exc:
            result.status = "INCONCLUSIVE"
            result.errors = [str(exc) if isinstance(exc, BackendError) else "Scanner process failed"]
            return result
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            process.stdout.close()
            process.stderr.close()
            result.duration_ms = int((time.monotonic() - started) * 1000)
        raw = bytes(chunks["out"])
        result.raw_hash = digest(raw)
        result.raw_json = raw.decode("utf-8", errors="replace")
        try:
            document = json.loads(raw)
            if result.exit_code != 0 or document.get("errors"):
                raise ValueError("Scanner returned errors")
            scanned = [relative_path(p.removeprefix("./")) for p in document["paths"]["scanned"]]
            if set(scanned) != set(manifest):
                raise ValueError("Scanner coverage differs from the accepted Python inventory")
            result.scanned = scanned
            for item in document["results"]:
                rel = relative_path(item["path"].removeprefix("./"))
                if rel not in manifest:
                    raise ValueError("Scanner returned an out-of-scope path")
                extra = item["extra"]
                # Fingerprints are matching aids, not assertions that code is secure.
                native = extra.get("fingerprint") or extra.get("metavars", {})
                fingerprint = digest(json.dumps([item["check_id"], rel, native], sort_keys=True).encode())
                result.findings.append(Finding(
                    rule_id=item["check_id"], severity={"ERROR": "High", "WARNING": "Medium", "INFO": "Low"}.get(extra["severity"], "Unknown"),
                    raw_severity=extra["severity"], file=rel, line=item["start"]["line"],
                    end_line=item["end"]["line"], message=extra["message"], scan_id=result.id,
                    fingerprint=fingerprint))
            result.status = "PASS"
        except (ValueError, TypeError, KeyError):
            result.status = "INCONCLUSIVE"
            result.errors = ["Scanner failed, returned malformed output, or did not cover every accepted Python file."]
        return result
