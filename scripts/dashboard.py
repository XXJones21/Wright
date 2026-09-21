"""Read-only, loopback dashboard for an existing Wright packet run (stdlib only)."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlsplit

from execution_metrics import TraceCollection, execution_report

PHASES = ("pre-production", "production", "post-production")
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
TEXT = {".md", ".txt", ".json", ".dsl", ".rle"}
PAGE = Path(__file__).with_name("dashboard.html")


def scoped_file(root: Path, relative: str) -> Path:
    """Allow only regular files inside this run, including after symlink resolution."""
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("Invalid run-relative path")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("File is outside this run or is missing")
    return path


def iso_time(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def artifact(root: Path, relative: str) -> dict | None:
    try:
        path = scoped_file(root, relative)
        if path.suffix.lower() not in IMAGES | TEXT:
            return None
        return {"path": relative, "name": path.stem.replace("-", " "),
                "url": "/artifact/" + quote(relative, safe="/"),
                "modified": iso_time(path)}
    except (ValueError, OSError):
        return None


def read_record(root: Path, reference: dict | None, warnings: list) -> dict:
    if not reference:
        return {}
    try:
        doc = reference["document"]
        path = scoped_file(root, doc["path"])
        raw = path.read_bytes()
        if doc.get("sha256") and hashlib.sha256(raw).hexdigest() != doc["sha256"]:
            warnings.append(f"Record changed since publication: {doc['path']}")
        value = json.loads(raw.decode("utf-8-sig"))
        if not isinstance(value, dict):
            raise ValueError("Record is not an object")
        return value
    except (KeyError, TypeError, ValueError, OSError) as exc:
        warnings.append(f"Could not read a referenced record: {exc}")
        return {}


def markdown_tables(text: str) -> list[dict]:
    """Extract planning tables without interpreting prose as task completion."""
    tables, rows, heading = [], [], ""
    for line in text.splitlines() + [""]:
        if line.startswith("#"):
            heading = line.lstrip("# ")
        if line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells):
                rows.append(cells)
        elif rows:
            if len(rows) > 1:
                tables.append({"heading": heading, "headers": rows[0], "rows": rows[1:]})
            rows = []
    return tables


def snapshot(root: Path) -> dict:
    state_path = root / "run.json"
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    if not isinstance(state, dict) or not isinstance(state.get("packets"), dict):
        raise ValueError("This dashboard requires a Wright packet run")
    warnings, packets = [], []
    for packet_id, record in state["packets"].items():
        spec = read_record(root, record.get("definition"), warnings)
        result = read_record(root, record.get("result"), warnings)
        progress = read_record(root, record.get("progress"), warnings)
        attribution = progress.get("execution", result.get("execution"))
        try:
            metric_file = artifact(root, f"metrics/{packet_id}.json")
            if metric_file:
                attribution = json.loads(scoped_file(root, metric_file["path"]).read_text(encoding="utf-8-sig"))
            execution = execution_report(attribution)
        except (ValueError, TypeError, OSError) as exc:
            warnings.append(f"Invalid executor metrics for {packet_id}: {exc}")
            execution = execution_report(None)
        refs = [record.get(key, {}) for key in ("result", "progress", "definition")]
        files = []
        for ref in refs:
            files.extend(ref.get("files", []))
            if ref.get("document"):
                files.append(ref["document"])
        evidence = []
        for relative in dict.fromkeys(f.get("path") for f in files if f.get("path")):
            item = artifact(root, relative)
            if item:
                evidence.append(item)
        modified = max((f["modified"] for f in evidence), default=state.get("created_at", ""))
        packets.append({"id": packet_id, "title": packet_id.replace("-", " "),
                        "status": record.get("status", "unknown"),
                        "phase": spec.get("phase", "unassigned"), "role": spec.get("role", "unspecified"),
                        "outcome": spec.get("outcome", "Definition unavailable"),
                        "depends_on": spec.get("depends_on", []), "budget": spec.get("budget", {}),
                        "metrics": record.get("metrics", {}), "budget_exceeded": record.get("budget_exceeded", False),
                        "runtime": result.get("runtime", {}).get("status", "not_recorded"),
                        "persistence": result.get("persistence", {}).get("status", "not_recorded"),
                        "checks": result.get("checks", []), "note": result.get("note", ""),
                        "next_action": progress.get("next_action", ""), "modified": modified,
                        "started_at": record.get("started_at"), "evidence": evidence})
        packets[-1]["execution"] = execution
    packets.sort(key=lambda p: p["modified"], reverse=True)
    pipeline = state.get("pipeline", {})
    phases = []
    for phase in PHASES:
        items = [p for p in packets if p["phase"] == phase]
        advanced = any(h.get("event") == "advance" and h.get("phase") == phase
                       for h in pipeline.get("history", []))
        status = pipeline.get("status", "unknown") if pipeline.get("phase") == phase else (
            "advanced" if advanced else "not_started")
        phases.append({"id": phase, "status": status, "counts": dict(Counter(p["status"] for p in items)),
                       "total": len(items)})
    documents = []
    for path in sorted(root.glob("*.md")):
        if not artifact(root, path.name):
            continue
        body = path.read_text(encoding="utf-8-sig")
        documents.append({**artifact(root, path.name), "text": body, "tables": markdown_tables(body)})
    gallery = []
    for folder in ("concepts", "captures"):
        base = root / folder
        if base.is_dir():
            for path in sorted(base.rglob("*")):
                if path.suffix.lower() in IMAGES:
                    item = artifact(root, path.relative_to(root).as_posix())
                    if item:
                        brief = artifact(root, (path.parent / "concept-brief.md").relative_to(root).as_posix())
                        gallery.append({**item, "kind": folder, "brief": brief})
    metrics = {key: sum(p["metrics"].get(key, 0) or 0 for p in packets)
               for key in ("tool_calls", "elapsed_seconds")}
    latest_result = max((p["modified"] for p in packets if p["status"] == "completed"), default="")
    older_plans = [d["path"] for d in documents if d["path"] in {"GAMEWIDE-PLAN.md", "MISSION1-PRODUCTION-PLAN.md"}
                   and d["modified"] < latest_result]
    return {"run_id": state.get("run_id", root.name), "task": state.get("task", "Wright run"),
            "project": Path(state.get("project_root", "Project")).name,
            "level": state.get("environment", {}).get("contract", {}).get("target_level", "Not recorded"),
            "created_at": state.get("created_at"), "state_updated": iso_time(state_path),
            "sampled_at": datetime.now(timezone.utc).isoformat(), "pipeline": pipeline,
            "review": read_record(root, pipeline.get("review"), warnings),
            "phases": phases, "packets": packets, "metrics": metrics, "documents": documents,
            "gallery": gallery, "older_plans": older_plans, "warnings": warnings}


def make_server(root: Path, port: int = 0, sessions=()) -> ThreadingHTTPServer:
    root = root.resolve()
    traces = TraceCollection(sessions)
    # Threaded HTTP requests must not update incremental trace offsets concurrently.
    from threading import Lock
    trace_lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def respond(self, data: bytes, content_type: str, status: int = 200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            # No mutation routes, directory listings, cross-origin API access or remote binding.
            path = unquote(urlsplit(self.path).path)
            if path == "/":
                self.respond(PAGE.read_bytes(), "text/html; charset=utf-8")
            elif path == "/api/state":
                try:
                    payload = snapshot(root)
                    with trace_lock:
                        payload["session_metrics"] = traces.read()
                    self.respond(json.dumps(payload).encode(), "application/json; charset=utf-8")
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    self.respond(json.dumps({"error": f"State temporarily unavailable: {exc}"}).encode(),
                                 "application/json; charset=utf-8", 503)
            elif path.startswith("/artifact/"):
                try:
                    target = scoped_file(root, path[len("/artifact/"):])
                    suffix = target.suffix.lower()
                    if suffix not in IMAGES | TEXT:
                        raise ValueError("Unsupported artifact")
                    kind = mimetypes.guess_type(target.name)[0] if suffix in IMAGES else "text/plain; charset=utf-8"
                    self.respond(target.read_bytes(), kind or "application/octet-stream")
                except (ValueError, OSError):
                    self.respond(b"Artifact unavailable", "text/plain", 404)
            else:
                self.respond(b"Not found", "text/plain", 404)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Existing run directory containing run.json")
    parser.add_argument("--port", type=int, default=0, help="Loopback port; 0 selects an available port")
    parser.add_argument("--session", type=Path, action="append", default=[],
                        help="Optional Codex rollout JSONL; repeat for additional root sessions. Descendants are discovered locally.")
    args = parser.parse_args()
    snapshot(args.run.resolve())  # Fail clearly before starting for unsupported/missing runs.
    server = make_server(args.run, args.port, args.session)
    print(f"Wright dashboard: http://127.0.0.1:{server.server_port}", flush=True)
    print("Read-only. Refreshes saved evidence; does not inspect Unreal or spend model tokens.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
