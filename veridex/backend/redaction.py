"""Best-effort secret detection; source itself never enters telemetry."""
import re

from backend.contracts import BackendError

PATTERN = re.compile(
    r"nvapi-[A-Za-z0-9_-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(?i:(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]\s*['\"][^'\"]{6,}['\"])"
)


def sanitize(text: str) -> str:
    return PATTERN.sub("[REDACTED]", text)[:2000]


def safe_outbound(text: str, key: str = "") -> str:
    if PATTERN.search(text) or (key and key in text):
        raise BackendError("Potential secret found in outbound context; request blocked. Use an approved secret-free sample.")
    return text
