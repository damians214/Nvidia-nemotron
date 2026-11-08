"""Operator-owned settings; never load configuration from a target repository."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from backend.contracts import BackendError

APP_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv() -> dict[str, str]:
    """Read the application's .env as literal values, without shell expansion."""
    path = APP_ROOT / ".env"
    values = {}
    if path.is_file() and not path.is_symlink():
        for line in path.read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key.startswith(("NVIDIA_", "VERIDEX_", "OPENGREP_")):
                values[key] = value.strip().strip("\"'" )
    return values


@dataclass(frozen=True)
class Settings:
    data_root: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "veridex-local")
    repositories: dict[str, Path] = field(default_factory=lambda: {"sample": APP_ROOT / "samples/sql_injection"})
    scanner: Path = APP_ROOT / ".tools/opengrep"
    rules: Path = APP_ROOT / "scanner/rules/python-sql.yml"
    scanner_version: str = "1.33.1"
    scanner_sha256: str = ""
    api_key: str = field(default="", repr=False)
    model: str = ""
    base_url: str = "https://integrate.api.nvidia.com/v1"
    max_files: int = 2000
    max_file_bytes: int = 1024 * 1024
    max_total_bytes: int = 50 * 1024 * 1024
    max_attempts: int = 2
    max_requests: int = 8
    max_tool_calls: int = 12
    max_tokens: int = 64000
    max_input_bytes: int = 32000
    max_output_tokens: int = 2000
    request_timeout: float = 60.0
    scan_timeout: float = 120.0
    run_timeout: float = 600.0
    max_output_bytes: int = 8 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Settings":
        env = {**load_dotenv(), **os.environ}
        toolchain = APP_ROOT / ".tools/toolchain.json"
        pin = json.loads(toolchain.read_text()) if toolchain.is_file() else {}
        repos = {"sample": APP_ROOT / "samples/sql_injection"}
        if env.get("VERIDEX_REPOSITORIES"):
            repos.update({k: Path(v) for k, v in json.loads(env["VERIDEX_REPOSITORIES"]).items()})
        return cls(
            data_root=Path(env.get("VERIDEX_DATA_ROOT", str(Path(tempfile.gettempdir()) / "veridex-local"))),
            repositories=repos,
            scanner=Path(env.get("OPENGREP_PATH", str(APP_ROOT / ".tools/opengrep"))),
            scanner_sha256=env.get("OPENGREP_SHA256", pin.get("sha256", "")),
            api_key=env.get("NVIDIA_API_KEY", ""),
            model=env.get("NVIDIA_MODEL", ""),
            base_url=env.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        )

    def validate_provider(self) -> None:
        if not self.api_key or self.api_key == "replace_me" or not self.model or "your_" in self.model:
            raise BackendError("Configure NVIDIA_API_KEY and NVIDIA_MODEL in the application .env first.")
        url = urlparse(self.base_url)
        if url.username or url.password or url.query or url.fragment:
            raise BackendError("Provider URL must not contain credentials, query or fragment.")
        if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost"}):
            raise BackendError("Provider endpoint requires HTTPS, except for explicit localhost testing.")
