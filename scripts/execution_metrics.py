"""Execution attribution and read-only Codex trace summaries. No transcript export."""
from collections import Counter
import json
import math
from pathlib import Path

COUNTERS = ("tool_calls", "implementation_calls", "verification_calls", "coordination_calls", "retry_calls",
            "active_seconds", "wait_seconds", "input_tokens", "cached_input_tokens", "output_tokens",
            "reasoning_output_tokens")
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def execution_report(value):
    """Reject misleading numbers; unknown stays null, never becomes zero."""
    if value is None:
        return {"coverage": "unknown", "executors": [], "call_unit": "unknown",
                "limitations": ["Executor attribution was not recorded for this packet."]}
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Execution metrics require schema_version 1")
    if value.get("coverage") not in {"complete", "partial"}:
        raise ValueError("Execution coverage must be complete or partial")
    if value.get("call_unit") not in {"underlying_tools", "host_requests", "unknown"}:
        raise ValueError("Unknown execution call unit")
    if not isinstance(value.get("limitations", []), list) or not all(isinstance(v, str) for v in value.get("limitations", [])):
        raise ValueError("Execution limitations must be a list of strings")
    reuse = value.get("reuse_decision")
    if reuse is not None:
        if not isinstance(reuse, dict) or reuse.get("decision") not in {"reuse", "adapt", "new", "mixed", "unknown"}:
            raise ValueError("Invalid reuse decision")
        if not isinstance(reuse.get("candidates", []), list) or not all(isinstance(v, str) for v in reuse.get("candidates", [])):
            raise ValueError("Reuse candidates must be a list of strings")
        if not isinstance(reuse.get("reason", ""), str):
            raise ValueError("Reuse reason must be text")
    executors, seen = value.get("executors"), set()
    if not isinstance(executors, list) or not executors:
        raise ValueError("Execution metrics need at least one identified executor")
    for actor in executors:
        if not isinstance(actor, dict) or actor.get("kind") not in {"orchestrator", "subagent", "human"}:
            raise ValueError("Unknown executor kind")
        if not isinstance(actor.get("id"), str) or not actor["id"].strip() or actor["id"] in seen:
            raise ValueError("Executor IDs must be nonempty and unique")
        seen.add(actor["id"])
        if actor.get("measurement") not in {"measured", "estimated", "unknown"}:
            raise ValueError("Executor needs a measurement method")
        for key in ("role", "model", "reasoning_effort"):
            if actor.get(key) is not None and not isinstance(actor[key], str):
                raise ValueError(f"Executor {key} must be text or null")
        for key in COUNTERS:
            n = actor.get(key)
            if n is not None and (type(n) not in (int, float) or not math.isfinite(n) or n < 0):
                raise ValueError(f"Invalid executor counter: {key}")
        for child, parent in (("cached_input_tokens", "input_tokens"), ("reasoning_output_tokens", "output_tokens"), ("retry_calls", "tool_calls")):
            if actor.get(child) is not None and actor.get(parent) is not None and actor[child] > actor[parent]:
                raise ValueError(f"{child} cannot exceed {parent}")
        parts = [actor.get(k) for k in ("implementation_calls", "verification_calls", "coordination_calls")]
        if actor.get("tool_calls") is not None and all(n is not None for n in parts) and sum(parts) > actor["tool_calls"]:
            raise ValueError("Activity categories double-count tool calls")
    return value


def session_meta(path):
    with path.open(encoding="utf-8") as stream:
        record = json.loads(stream.readline())
    if record.get("type") != "session_meta":
        raise ValueError("Missing session metadata")
    return record["payload"]


def parent_id(meta):
    source = meta.get("source")
    return source.get("subagent", {}).get("thread_spawn", {}).get("parent_thread_id") if isinstance(source, dict) else None


class TraceReader:
    """Incremental JSONL reader; count only own events and unique response usage."""
    def __init__(self, path):
        self.path = path
        self.reset()

    def reset(self):
        self.meta = session_meta(self.path)
        self.offset = 0
        self.calls = Counter()
        self.call_ids, self.response_ids = set(), set()
        self.tokens = Counter()
        self.missing_tokens = set()
        self.settings = []
        self.current_turn = None
        self.latest_at = None
        self.malformed_lines = 0

    def read(self):
        if self.path.stat().st_size < self.offset:
            self.reset()
        with self.path.open("rb") as stream:
            stream.seek(self.offset)
            while True:
                start = stream.tell()
                line = stream.readline()
                if not line:
                    break
                if not line.endswith(b"\n"):
                    stream.seek(start)  # A concurrently written record is retried next refresh.
                    break
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeError):
                    self.malformed_lines += 1
                    continue
                data, kind = record.get("payload", {}), record.get("type")
                self.latest_at = record.get("timestamp", self.latest_at)
                if kind == "turn_context":
                    self.current_turn = data.get("turn_id")
                    settings = {"model": data.get("model"), "reasoning_effort": data.get("effort", data.get("reasoning_effort"))}
                    if settings not in self.settings:
                        self.settings.append(settings)
                if kind == "response_item" and self.current_turn and data.get("type") in {"function_call", "custom_tool_call"}:
                    key = data.get("call_id")
                    if key and key not in self.call_ids:
                        self.call_ids.add(key)
                        self.calls[data.get("name", "unknown")] += 1
                if kind == "token_usage_record" and data.get("thread_id") == self.meta["id"]:
                    key = data.get("response_id")
                    if key and key not in self.response_ids:
                        self.response_ids.add(key)
                        for field in TOKEN_KEYS:
                            n = data.get("usage", {}).get(field)
                            if type(n) is int and n >= 0:
                                self.tokens[field] += n
                            else:
                                self.missing_tokens.add(field)
            self.offset = stream.tell()
        return {"id": self.meta["id"], "parent_id": parent_id(self.meta),
                "name": self.meta.get("agent_path") or "Main orchestrator",
                "kind": "subagent" if parent_id(self.meta) else "orchestrator",
                "settings": self.settings, "host_tool_requests": sum(self.calls.values()),
                "tool_breakdown": dict(self.calls), "explicit_spawns": self.calls.get("spawn_agent", 0),
                "response_count": len(self.response_ids),
                "tokens": {k: self.tokens.get(k) if k in self.tokens and k not in self.missing_tokens else None for k in TOKEN_KEYS},
                "started_at": self.meta.get("timestamp"), "latest_event_at": self.latest_at,
                "malformed_lines": self.malformed_lines}


class TraceCollection:
    def __init__(self, roots):
        self.roots = [Path(p).resolve() for p in roots]
        self.readers = {}

    def read(self):
        if not self.roots:
            return {"sessions": [], "scope": "No session logs configured", "warnings": []}
        warnings, metas = [], {}
        candidates = set(self.roots)
        for folder in {p.parent for p in self.roots}:
            candidates.update(folder.glob("*.jsonl"))
        for path in candidates:
            try:
                metas[path] = session_meta(path)
            except (ValueError, OSError, KeyError) as exc:
                if path in self.roots:
                    warnings.append(f"Configured session unavailable: {exc}")
        selected = {p for p in self.roots if p in metas}
        while True:
            ids = {metas[p]["id"] for p in selected}
            found = {p for p, m in metas.items() if parent_id(m) in ids}
            if found <= selected:
                break
            selected.update(found)
        summaries, seen = [], set()
        for path in sorted(selected):
            try:
                if metas[path]["id"] in seen:
                    continue
                seen.add(metas[path]["id"])
                if path not in self.readers:
                    self.readers[path] = TraceReader(path)
                summaries.append(self.readers[path].read())
            except (OSError, ValueError, KeyError, TypeError) as exc:
                warnings.append(f"Session summary unavailable: {exc}")
        return {"sessions": summaries, "scope": "Configured sessions and explicitly spawned descendants found in the same log folders; earlier run sessions and system reviewers are excluded unless configured.",
                "warnings": warnings,
                "limitations": "Host requests include exec/wait wrappers and differ from underlying tool calls. Input includes repeatedly processed cached context; reasoning is a subset of output. These are raw response counters, not billed cost, account-limit usage, or per-packet attribution."}
