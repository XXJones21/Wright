"""Read-only dashboard behavior, evidence fidelity, and file boundaries."""
import hashlib
import json
from pathlib import Path
import sys
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dashboard


def write(root, name, data):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return {"document": {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}, "files": []}


def fixture_run(tmp_path):
    spec = write(tmp_path, "packets/definition.json", {"phase": "pre-production", "outcome": "Test a shared system",
                  "role": "gameplay-programmer", "depends_on": []})
    result = write(tmp_path, "packets/result.json", {"runtime": {"status": "not_run"},
                   "persistence": {"status": "verified"}, "note": "Input acceptance pending",
                   "checks": [{"id": "compile", "status": "pass"}]})
    state = {"run_id": "fixture", "project_root": "/games/Example", "created_at": "2026-09-20T20:00:00+00:00",
             "pipeline": {"phase": "pre-production", "status": "working", "history": []},
             "packets": {"shared-system": {"status": "completed", "definition": spec, "result": result,
                        "metrics": {"tool_calls": 6, "elapsed_seconds": 30}}}}
    write(tmp_path, "run.json", state)
    return tmp_path


class DashboardTests(unittest.TestCase):
    def setUp(self):
        base = Path(__file__).resolve().parents[2] / '.test-tmp'
        base.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='dashboard-', dir=base)
        assert Path(self.temp.name).resolve().is_relative_to(base.resolve())
        self.addCleanup(self.temp.cleanup)
        self.run = fixture_run(Path(self.temp.name))

    def test_reject_escape(self):
        for relative in ('../outside.txt', '/etc/passwd', '..\\outside.txt', 'D:/other/file.txt'):
            with self.subTest(path=relative), self.assertRaises(ValueError):
                dashboard.scoped_file(self.run, relative)

    def test_read_only_snapshot_preserves_acceptance_limits(self):
        run = self.run
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in run.rglob("*") if p.is_file()}
        report = dashboard.snapshot(run)
        assert report["packets"][0]["status"] == "completed"
        assert report["packets"][0]["runtime"] == "not_run"
        assert report["packets"][0]["note"] == "Input acceptance pending"
        assert report["review"] == {}
        assert [p["status"] for p in report["phases"]] == ["working", "not_started", "not_started"]
        assert report["metrics"] == {"tool_calls": 6, "elapsed_seconds": 30}
        assert before == {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in run.rglob("*") if p.is_file()}


    def test_missing_or_changed_evidence_is_visible(self):
        run = self.run
        write(run, "packets/result.json", {"note": "Updated externally"})
        report = dashboard.snapshot(run)
        assert any("changed since publication" in w for w in report["warnings"])
        (run / "packets/definition.json").unlink()
        report = dashboard.snapshot(run)
        assert any("Could not read" in w for w in report["warnings"])
        assert report["packets"][0]["phase"] == "unassigned"


    def test_advanced_phase_and_new_work(self):
        run = self.run
        state = json.loads((run / "run.json").read_text())
        state["pipeline"] = {"phase": "production", "status": "working", "history": [{"event": "advance", "phase": "pre-production"}]}
        write(run, "run.json", state)
        assert [p["status"] for p in dashboard.snapshot(run)["phases"]] == ["advanced", "working", "not_started"]


    def test_plan_tables_do_not_become_registered_packets(self):
        run = self.run
        (run / "MISSION1-PRODUCTION-PLAN.md").write_text("# Plan\n\n| Packet | Outcome |\n|---|---|\n| Follow | Two actors move |\n", encoding="utf-8")
        report = dashboard.snapshot(run)
        assert report["documents"][0]["tables"][0]["rows"] == [["Follow", "Two actors move"]]
        assert report["phases"][1]["total"] == 0


    def test_server_refresh_error_and_artifact_boundary(self):
        run = self.run
        server = dashboard.make_server(run)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/state") as response:
                assert json.load(response)["metrics"]["tool_calls"] == 6
            state = json.loads((run / "run.json").read_text())
            state["packets"]["shared-system"]["metrics"]["tool_calls"] = 9
            write(run, "run.json", state)
            with urlopen(base + "/api/state") as response:
                assert json.load(response)["metrics"]["tool_calls"] == 9
            (run / "unsafe.html").write_text("<script>alert(1)</script>")
            for path in ("/artifact/%2e%2e/outside.txt", "/artifact/unsafe.html", "/not-found"):
                with self.assertRaises(HTTPError) as exc:
                    urlopen(base + path)
                assert exc.exception.code == 404
            with urlopen(base + "/artifact/run.json") as response:
                assert response.headers["Content-Type"].startswith("text/plain")
            (run / "run.json").write_text("{")
            with self.assertRaises(HTTPError) as exc:
                urlopen(base + "/api/state")
            assert exc.exception.code == 503
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

if __name__ == '__main__':
    unittest.main()
