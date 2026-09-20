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

COMPACT_TOOL_API = """
## TOOL API

### editor_toolset.toolsets.scene.SceneTools
```json
{"tools": [{"name": "editor_toolset.toolsets.scene.SceneTools.add_to_scene_from_class", "description": "Spawn an actor of a class into the current level.", "inputSchema": {"properties": {"actor_type": {}, "name": {}, "xform": {}, "parent": {}, "snap_to_ground": {}}}}, {"name": "editor_toolset.toolsets.scene.SceneTools.find_actors", "description": "Find actors in the current level.", "inputSchema": {"properties": {"root": {}, "name": {}, "actor_type": {}, "tag": {}, "bounds": {}, "collision_channels": {}}}}]}
```

## PROJECT SKILLS
"""

def test_parse_tool_api_reads_the_compact_fence():
    api = gates.parse_tool_api(COMPACT_TOOL_API)
    ts = api["editor_toolset.toolsets.scene.SceneTools"]
    assert set(ts) == {"add_to_scene_from_class", "find_actors"}
    assert ts["add_to_scene_from_class"] == {"actor_type", "name", "xform", "parent", "snap_to_ground"}
    assert gates.tool_call_gate(api, gates.parse_call_ledger(LEDGER_OK), "blockout") == []

def test_run_twice_replaces_the_gate_section(tmp_path):
    run = tmp_path / "run"; (run / "artifacts").mkdir(parents=True)
    plan = run / "plan.md"
    plan.write_text("# plan\n\n## PROJECT GPS\n\nBP_FirstPersonCharacter\n" + TOOL_API, encoding="utf-8")
    art = run / "artifacts" / "01-blockout.md"
    art.write_text(LEDGER_BAD, encoding="utf-8")
    gates.run(run)
    assert "RESULT: FAIL" in plan.read_text(encoding="utf-8")
    art.write_text(LEDGER_OK, encoding="utf-8")
    gates.run(run)
    text = plan.read_text(encoding="utf-8")
    assert text.count("## Gate") == 1
    assert "RESULT: PASS" in text
    assert "RESULT: FAIL" not in text
    assert "## PROJECT GPS" in text and "## TOOL API" in text

FINDING_WITH_SUB_HEADINGS = """# plan

## Finding: engine

### Verdicts

CLM-1: VERIFIED - the TOOL API lists add_to_scene_from_class.
CLM-2: REJECTED - no Blueprint named BP_EvidenceItem exists in the GPS.

### Live read-only calls made
find_actors; get_label; get_class.

## Finding: reference

### Patterns
- Outlast: the camera battery is the economy.
"""

def test_finding_section_survives_demoted_sub_headings():
    v = gates.parse_clm_verdicts(gates._section(FINDING_WITH_SUB_HEADINGS, "Finding: engine"))
    assert [x["id"] for x in v] == ["CLM-1", "CLM-2"]
    assert [x["verdict"] for x in v] == ["VERIFIED", "REJECTED"]

def test_a_level_two_sub_heading_truncates_the_finding_section():
    """The hazard the conductor's demotion prevents: a `## ` line inside an appended
    finding closes the plan's `## Finding: engine` section before any verdict line."""
    hazard = FINDING_WITH_SUB_HEADINGS.replace("### Verdicts", "## Verdicts")
    assert gates.parse_clm_verdicts(gates._section(hazard, "Finding: engine")) == []

TOOL_API_WITH_SAVE = """
## TOOL API

### editor_toolset.toolsets.asset.AssetTools
```json
{"tools": [{"name": "editor_toolset.toolsets.asset.AssetTools.save_assets", "description": "Save the given asset paths.", "inputSchema": {"properties": {"asset_paths": {}}}}]}
```
"""

LEDGER_SAVE = """
# Artifact: evidence blueprint

Saved the Blueprint with save_assets after the compile.

CALL LEDGER
```jsonl
{"toolset": "editor_toolset.toolsets.asset.AssetTools", "tool": "save_assets", "args": ["asset_paths"]}
```
"""

def test_rejected_negative_claim_does_not_forbid_a_tool_api_symbol(tmp_path):
    """A rejected claim names save_assets; save_assets is absent from the GPS but present
    in the TOOL API, so it is grounded and must not be flagged."""
    run = tmp_path / "run"; (run / "artifacts").mkdir(parents=True)
    (run / "plan.md").write_text(
        "# plan\n\n## PROJECT GPS\n\nBP_FirstPersonCharacter\n" + TOOL_API_WITH_SAVE +
        "\n## Plan (orchestrator)\n\n"
        "- `CLM-1` no tool saves the level; AssetTools.save_assets does not exist.\n"
        "\n## Finding: engine\n\n"
        "CLM-1: REJECTED - save_assets exists and saves any asset path.\n", encoding="utf-8")
    (run / "artifacts" / "01-evidence.md").write_text(LEDGER_SAVE, encoding="utf-8")
    section = gates.run(run)
    assert "forbidden symbol" not in section
    assert "save_assets" not in section
    assert "RESULT: PASS" in section
