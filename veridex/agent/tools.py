"""Strict tool schemas. Application code alone grants authority."""
from typing import Literal

from pydantic import Field

from backend.contracts import Record


class ListFiles(Record):
    prefix: str = ""


class ReadFile(Record):
    relative_path: str
    start_line: int = Field(default=1, ge=1)
    end_line: int = Field(default=200, ge=1, le=400)


class GetFinding(Record):
    finding_id: str


class ProposePatch(Record):
    relative_path: str
    original_hash: str
    patched_text: str = Field(min_length=1)


class RunVerification(Record):
    candidate_id: str


TOOL_TYPES = {"list_scoped_files": ListFiles, "read_file": ReadFile, "get_finding": GetFinding,
              "propose_patch": ProposePatch, "run_verification": RunVerification}
DESCRIPTIONS = {
    "list_scoped_files": "List approved Python snapshot files (bounded).",
    "read_file": "Read bounded original source lines and obtain the original_hash needed to propose a fix.",
    "get_finding": "Read the selected scanner finding in this run.",
    "propose_patch": "Propose the entire replacement text for the selected file after reading it. Never alters original files.",
    "run_verification": "Run independent syntax, policies, and OpenGrep rescan on the latest candidate.",
}


def tool_definitions():
    return [{"type": "function", "function": {"name": name, "description": DESCRIPTIONS[name],
                                               "parameters": schema.model_json_schema()}}
            for name, schema in TOOL_TYPES.items()]
