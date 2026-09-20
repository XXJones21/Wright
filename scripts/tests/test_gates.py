import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import gates

PLAN = """
3. DEVICE / API CLAIMS
- `CLM-1` `SceneTools.add_to_scene_from_class` spawns a StaticMeshActor at an xform.
- `CLM-2` BP_EvidenceItem exposes an 'OnScanned' event dispatcher.
- CLM-3: the level has a PlayerStart actor.
"""
VERDICTS = """
CLM-1: VERIFIED - TOOL API lists add_to_scene_from_class(actor_type, name, xform, parent, snap_to_ground).
CLM-2: REJECTED - no Blueprint named BP_EvidenceItem exists in the GPS; create it first.
CLM-3: UNVERIFIABLE - GPS was truncated before the PlayerStart entries.
"""

def test_parse_clm_claims():
    c = gates.parse_clm_claims(PLAN)
    assert set(c) == {"CLM-1", "CLM-2", "CLM-3"}
    assert "BP_EvidenceItem" in c["CLM-2"]

def test_parse_clm_verdicts():
    v = gates.parse_clm_verdicts(VERDICTS)
    assert [x["id"] for x in v] == ["CLM-1", "CLM-2", "CLM-3"]
    assert [x["verdict"] for x in v] == ["VERIFIED", "REJECTED", "UNVERIFIABLE"]

def test_extract_symbols():
    s = gates.extract_symbols("bind 'Capture Point' via ItemCaptured on capture_item_spawner_device")
    assert {"Capture Point", "ItemCaptured", "capture_item_spawner_device"} <= s

def test_grounding_gate_flags_rejected_symbol_absent_from_gps():
    flags = gates.grounding_gate(
        ["BP_EvidenceItem exposes an 'OnScanned' event dispatcher."],
        [("evidence-blueprint", "(event OnScanned ...) on BP_EvidenceItem")],
        gps_text="/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter",
    )
    assert {"BP_EvidenceItem", "OnScanned"} <= {f["symbol"] for f in flags}

def test_grounding_gate_ignores_symbols_present_in_gps():
    flags = gates.grounding_gate(
        ["BP_FirstPersonCharacter has a Scan function."],
        [("x", "call Scan on BP_FirstPersonCharacter")],
        gps_text="BP_FirstPersonCharacter",
    )
    assert all(f["symbol"] != "BP_FirstPersonCharacter" for f in flags)

def test_parse_build_tasks_with_lanes():
    syn = """
BUILD TASKS
- [blueprint] BP_EvidenceItem: actor with a scan interaction and OnScanned dispatcher
- [editor] Crash site blockout: three debris primitives around the PlayerStart
- [texture] Scorched ground material: seamless burnt-soil tile on the site floor
- [needs-you] Scanner input action: bind IA_Scan in the C++ character
Other text
"""
    t = gates.parse_build_tasks(syn)
    assert [x["lane"] for x in t] == ["blueprint", "editor", "texture", "needs-you"]
    assert t[0]["title"] == "BP_EvidenceItem"
    assert t[1]["brief"].startswith("three debris")

def test_parse_build_tasks_defaults_lane_to_editor():
    t = gates.parse_build_tasks("BUILD TASKS\n- Site fence: a low wall")
    assert t[0]["lane"] == "editor"

import json, pathlib, subprocess, sys as _sys

TOOL_API = """
## TOOL API

### editor_toolset.toolsets.scene.SceneTools
```json
{"tools": [
 {"name": "editor_toolset.toolsets.scene.SceneTools.find_actors",
  "inputSchema": {"type": "object", "properties": {"root": {}, "name": {}, "actor_type": {}, "tag": {}, "bounds": {}, "collision_channels": {}}}},
 {"name": "editor_toolset.toolsets.scene.SceneTools.add_to_scene_from_class",
  "inputSchema": {"type": "object", "properties": {"actor_type": {}, "name": {}, "xform": {}, "parent": {}, "snap_to_ground": {}}}}
]}
```
"""

LEDGER_OK = """
# Artifact: blockout

CALL LEDGER
```jsonl
{"toolset": "editor_toolset.toolsets.scene.SceneTools", "tool": "add_to_scene_from_class", "args": ["actor_type", "name", "xform", "parent", "snap_to_ground"]}
```
"""
LEDGER_BAD = """
CALL LEDGER
```jsonl
{"toolset": "editor_toolset.toolsets.scene.SceneTools", "tool": "spawn_actor", "args": ["name"]}
{"toolset": "editor_toolset.toolsets.scene.SceneTools", "tool": "find_actors", "args": ["name", "label"]}
{"toolset": "editor_toolset.toolsets.level.LevelTools", "tool": "create_level", "args": []}
```
"""

def test_parse_tool_api():
    api = gates.parse_tool_api(TOOL_API)
    assert api["editor_toolset.toolsets.scene.SceneTools"]["find_actors"] == {"root", "name", "actor_type", "tag", "bounds", "collision_channels"}

def test_parse_call_ledger():
    e = gates.parse_call_ledger(LEDGER_OK)
    assert e == [{"toolset": "editor_toolset.toolsets.scene.SceneTools", "tool": "add_to_scene_from_class",
                  "args": ["actor_type", "name", "xform", "parent", "snap_to_ground"]}]

def test_tool_call_gate_passes_known_calls():
    api = gates.parse_tool_api(TOOL_API)
    assert gates.tool_call_gate(api, gates.parse_call_ledger(LEDGER_OK), "blockout") == []

def test_tool_call_gate_flags_unknown_tool_arg_and_toolset():
    api = gates.parse_tool_api(TOOL_API)
    flags = gates.tool_call_gate(api, gates.parse_call_ledger(LEDGER_BAD), "bad")
    problems = {(f["tool"], f["problem"]) for f in flags}
    assert ("spawn_actor", "unknown tool") in problems
    assert ("find_actors", "unknown argument: label") in problems
    assert ("create_level", "unknown toolset") in problems

def test_run_appends_gate_section(tmp_path):
    run = tmp_path / "run"; (run / "artifacts").mkdir(parents=True)
    (run / "plan.md").write_text(
        "# plan\n\n## PROJECT GPS\n\nBP_FirstPersonCharacter\n" + TOOL_API +
        "\n## Plan (orchestrator)\n\n- `CLM-1` BP_EvidenceItem exposes an 'OnScanned' dispatcher.\n"
        "\n## Finding: engine\n\nCLM-1: REJECTED - not in GPS.\n", encoding="utf-8")
    (run / "artifacts" / "01-blockout.md").write_text(LEDGER_OK + "\nuses BP_EvidenceItem\n", encoding="utf-8")
    section = gates.run(run)
    text = (run / "plan.md").read_text(encoding="utf-8")
    assert "## Gate" in text and "FAIL" in section and "BP_EvidenceItem" in section

def test_cli_exit_code(tmp_path):
    run = tmp_path / "run"; (run / "artifacts").mkdir(parents=True)
    (run / "plan.md").write_text("# plan\n" + TOOL_API, encoding="utf-8")
    (run / "artifacts" / "01.md").write_text(LEDGER_OK, encoding="utf-8")
    script = pathlib.Path(gates.__file__)
    r = subprocess.run([_sys.executable, str(script), str(run)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout

def test_run_without_artifacts_reports_inconclusive_result(tmp_path):
    run = tmp_path / "run"; run.mkdir(parents=True)
    (run / "plan.md").write_text("# plan\n" + TOOL_API, encoding="utf-8")
    section = gates.run(run)
    assert "RESULT: INCONCLUSIVE" in section
    assert "RESULT: FAIL" not in section
