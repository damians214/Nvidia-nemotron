"""Explicit deterministic protocol fixture. This is not a model implementation."""
import json

SAFE = '''"""SQLite example with a parameterized query."""
import sqlite3


def get_user(conn: sqlite3.Connection, username: str):
    query = "SELECT * FROM users WHERE username = ?"
    return conn.execute(query, (username,)).fetchone()
'''
UNSAFE = SAFE.replace('query = "SELECT * FROM users WHERE username = ?"', 'query = f"SELECT * FROM users WHERE username = \'{username}\'"').replace('execute(query, (username,))', 'execute(query)')


class RecordedNemotron:
    mode = "RECORDED_TEST"
    model_id = "recorded-protocol-fixture-v1"

    def __init__(self, candidates=None, verdict="ACCEPT", bad_citations=False):
        self.candidates = candidates or [SAFE]
        self.verdict = verdict
        self.bad_citations = bad_citations
        self.calls = 0
        self.proposals = 0
        self.contexts = []

    def complete(self, messages, tools=None):
        self.calls += 1
        self.contexts.append(messages.copy())
        if tools is None:
            evidence = json.loads(messages[-1]["content"])["available_evidence"]
            refs = [k for k in evidence if k.startswith(("source:", "check:", "scan:"))]
            review = {"verdict": self.verdict, "evidence_refs": ["invented"] if self.bad_citations else refs,
                      "concerns": [], "uncertainty": "Recorded fixture verdict; not a live security assessment."}
            message = {"role": "assistant", "content": json.dumps(review)}
        else:
            reads = [json.loads(m["content"]) for m in messages if m["role"] == "tool" and '"original_hash"' in m["content"]]
            if not reads:
                finding = json.loads(messages[1]["content"])["finding"]
                name, args = "read_file", {"relative_path": finding["file"]}
            else:
                read = reads[-1]
                text = self.candidates[min(self.proposals, len(self.candidates) - 1)]
                self.proposals += 1
                name, args = "propose_patch", {"relative_path": read["relative_path"], "original_hash": read["original_hash"], "patched_text": text}
            message = {"role": "assistant", "content": None, "tool_calls": [
                {"type": "function", "id": f"fixture-{self.calls}", "function": {"name": name, "arguments": json.dumps(args)}}]}
        return {"message": message, "request_id": f"recorded-{self.calls}", "usage": {"prompt_tokens": 100, "completion_tokens": 100}}
