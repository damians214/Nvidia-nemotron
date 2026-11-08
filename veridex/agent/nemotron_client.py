"""Small NVIDIA Chat Completions adapter. No textual tool-call emulation."""
from __future__ import annotations

import json

import httpx

from backend.config import Settings
from backend.contracts import BackendError, ProviderTransientError
from backend.redaction import safe_outbound


class Nemotron:
    mode = "LIVE"

    def __init__(self, settings: Settings, transport=None):
        settings.validate_provider()
        self.settings = settings
        self.model_id = settings.model
        self.transport = transport

    def complete(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        settings = self.settings
        serialized = json.dumps(messages, ensure_ascii=False)
        safe_outbound(serialized, settings.api_key)
        if len(serialized.encode()) > settings.max_input_bytes:
            raise BackendError("Model context limit exceeded; start a smaller scoped investigation.")
        body = {"model": settings.model, "messages": messages, "temperature": 0.1,
                "max_tokens": settings.max_output_tokens, "stream": False}
        if tools:
            body.update(tools=tools, tool_choice="auto")
        else:
            body["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=settings.request_timeout, follow_redirects=False,
                              trust_env=False, transport=self.transport) as client:
                with client.stream("POST", settings.base_url.rstrip("/") + "/chat/completions",
                                   headers={"Authorization": "Bearer " + settings.api_key}, json=body) as response:
                    if response.status_code != 200:
                        if response.status_code in {429, 500, 502, 503, 504}:
                            raise ProviderTransientError(f"Transient NVIDIA HTTP {response.status_code}; retry within run budget.")
                        raise BackendError(f"NVIDIA request failed with HTTP {response.status_code}; check endpoint, model, quota and credentials.")
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        data.extend(chunk)
                        if len(data) > settings.max_output_bytes:
                            raise BackendError("NVIDIA response size limit exceeded")
            document = json.loads(data)
            choice = document["choices"][0]
            if choice.get("finish_reason") not in {"stop", "tool_calls"}:
                raise BackendError("Model response was incomplete or truncated")
            message = choice["message"]
            if message.get("role") != "assistant":
                raise ValueError("Invalid response role")
            safe_outbound(json.dumps(message), settings.api_key)
            request_id = document.get("id", "unknown")
            if type(request_id) is not str or len(request_id) > 200:
                raise ValueError("Invalid provider request ID")
            safe_outbound(request_id, settings.api_key)
            calls = message.get("tool_calls", [])
            if tools and not calls:
                raise BackendError("Model did not return native tool calls; verify tool support for the configured endpoint/model.")
            if not isinstance(calls, list):
                raise ValueError("Invalid tool call list")
            return {"message": {k: v for k, v in message.items() if k in {"role", "content", "tool_calls"}},
                    "request_id": request_id, "usage": document.get("usage", {})}
        except BackendError:
            raise
        except httpx.TransportError as exc:
            raise ProviderTransientError("NVIDIA transport failed; retry within run budget.") from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError) as exc:
            raise BackendError("NVIDIA request failed or returned an invalid response; no model result was accepted.") from exc
