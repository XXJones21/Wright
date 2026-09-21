"""Legacy paths cannot accidentally declare a packet workflow complete."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gates
import run_state


def test_legacy_gate_does_not_write_packet_report(tmp_path):
    manifest = tmp_path / "run.json"
    manifest.write_text(json.dumps({"workflow": "packets-v1"}), encoding="utf-8")
    assert "RESULT: INCONCLUSIVE" in gates.run(tmp_path)
    assert not (tmp_path / "plan.md").exists()


def test_legacy_state_updates_cannot_bypass_packet_transitions(tmp_path):
    (tmp_path / "Example.uproject").write_text("{}", encoding="utf-8")
    state = run_state.init_run(tmp_path, task="packet-test")
    run = Path(state["run_dir"])
    state["workflow"] = "packets-v1"
    run_state._atomic_json(run / "run.json", state)
    original = (run / "run.json").read_bytes()
    draft = run / "findings" / "draft.md"
    draft.write_text("unverified draft", encoding="utf-8")
    with pytest.raises(run_state.StateError, match="work_packets"):
        run_state.checkpoint(tmp_path, run, name="complete")
    with pytest.raises(run_state.StateError, match="work_packets"):
        run_state.register_artifact(tmp_path, run, task_id="01", source=draft)
    assert (run / "run.json").read_bytes() == original
    assert not list((run / "artifacts").rglob("*.md"))
