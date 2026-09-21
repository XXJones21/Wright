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

ZERO_CLAIMS = "\n## Plan (orchestrator)\nCLAIMS: NONE\n\n## Finding: engine\nVERDICTS: NONE\n"

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
Lane: editor
# Artifact: blockout

CALL LEDGER
```jsonl
{"toolset": "editor_toolset.toolsets.scene.SceneTools", "tool": "add_to_scene_from_class", "args": ["actor_type", "name", "xform", "parent", "snap_to_ground"]}
```
"""
LEDGER_BAD = """
Lane: editor
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
    (run / "plan.md").write_text("# plan\n" + TOOL_API + ZERO_CLAIMS, encoding="utf-8")
    (run / "artifacts" / "01.md").write_text(LEDGER_OK, encoding="utf-8")
    script = pathlib.Path(gates.__file__)
    r = subprocess.run([_sys.executable, str(script), str(run)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PASS" in r.stdout

def test_run_without_artifacts_reports_inconclusive_result(tmp_path):
    run = tmp_path / "run"; run.mkdir(parents=True)
    (run / "plan.md").write_text("# plan\n" + TOOL_API + ZERO_CLAIMS, encoding="utf-8")
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
    plan.write_text("# plan\n\n## PROJECT GPS\n\nBP_FirstPersonCharacter\n" + TOOL_API + ZERO_CLAIMS, encoding="utf-8")
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
Lane: blueprint
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

import pytest


def make_run(tmp_path, artifact=LEDGER_OK, claims=ZERO_CLAIMS, api=TOOL_API):
    run = tmp_path / "run"
    (run / "artifacts").mkdir(parents=True)
    (run / "plan.md").write_text("# plan\n" + api + claims, encoding="utf-8")
    if artifact is not None:
        (run / "artifacts" / "01.md").write_text(artifact, encoding="utf-8")
    return run


@pytest.mark.parametrize("artifact, problem", [
    ("Lane: editor\nNothing recorded.", "nonempty valid CALL LEDGER"),
    ("Lane: editor\nCALL LEDGER\n```jsonl\n```\n", "nonempty valid CALL LEDGER"),
    (LEDGER_OK.replace('"args": [', '"args": "wrong", "other": ['), "string-list args"),
    (LEDGER_OK.replace('"actor_type", ', '', 1), "missing argument: actor_type"),
    (LEDGER_OK.replace('"actor_type", ', '"actor_type", "actor_type", ', 1), "duplicate argument keys"),
    (LEDGER_OK.replace('\n```\n', '\nnot json\n```\n'), "invalid JSON"),
    (LEDGER_OK + "\nCALL LEDGER\n```jsonl\n```\n", "expected one CALL LEDGER"),
    (LEDGER_OK.replace('Lane: editor\n', ''), "Lane: declaration"),
    (LEDGER_OK.replace('Lane: editor', 'Lane: editor\nLane: needs-you'), "Lane: declaration"),
    ("```text\nLane: needs-you\nNO TOOL CALLS\n```", "Lane: declaration"),
    ("Lane: editor\nNO TOOL CALLS\n", "NO TOOL CALLS requires"),
    ("Lane: needs-you\nNO TOOL CALLS\nCALL LEDGER\n```jsonl\ninvalid\n```", "invalid JSON"),
    (LEDGER_OK.replace('Lane: editor', 'Lane: needs-you\nNO TOOL CALLS'), "NO TOOL CALLS requires"),
])
def test_bad_ledger_or_lane_never_passes(tmp_path, artifact, problem):
    result = gates.run(make_run(tmp_path, artifact=artifact))
    assert "RESULT: FAIL" in result
    assert problem in result


@pytest.mark.parametrize("ledger", ["", "\nCALL LEDGER\n```jsonl\n```\n"])
def test_explicit_needs_you_no_call_exemption(tmp_path, ledger):
    result = gates.run(make_run(tmp_path, artifact="Lane: needs-you\nNO TOOL CALLS\n" + ledger))
    assert "RESULT: PASS" in result


@pytest.mark.parametrize("api", [
    "", TOOL_API + TOOL_API,
    TOOL_API.replace('"tools": [', '"tools": {"bad": [' ).replace(']}', ']}}'),
    TOOL_API.replace('"name": "editor_toolset', '"name": "bad", "name": "editor_toolset', 1),
    TOOL_API.replace('"properties": {"root": {}', '"properties": {"root": "bad"'),
    TOOL_API + '\n```json\ninvalid\n```\n',
    TOOL_API.replace('```\n', ''),
])
def test_invalid_api_never_passes(tmp_path, api):
    assert "RESULT: FAIL" in gates.run(make_run(tmp_path, api=api))


@pytest.mark.parametrize("claim_rows, verdict_rows, problem", [
    ("CLM-1: BP_UnknownThing exists.", "", "missing verdict for CLM-1"),
    ("CLM-1: BP_UnknownThing exists.", "CLM-2: VERIFIED", "unknown verdict ID CLM-2"),
    ("CLM-1: BP_UnknownThing exists.", "CLM-1: VERIFIED\nCLM-1: REJECTED", "duplicate CLM-1"),
    ("CLM-1: BP_UnknownThing exists.\nCLM-01: duplicate", "CLM-1: VERIFIED", "duplicate CLM-1"),
    ("CLM-1: BP_UnknownThing exists.", "CLM-1: VERIFIED or REJECTED", "exactly one leading verdict"),
    ("CLM-1:", "CLM-1: VERIFIED", "empty claim"),
    ("CLM-one: Broken ID", "VERDICTS: NONE", "malformed claim row"),
    ("CLAIMS: NONE\n| CLM-1 | hidden claim |", "VERDICTS: NONE", "malformed claim row"),
    ("CLAIMS: NONE\nCLM-1: BP_UnknownThing exists.", "CLM-1: VERIFIED", "ambiguous CLAIMS: NONE"),
    ("", "", "explicitly for zero claims"),
])
def test_claim_coverage_failures(tmp_path, claim_rows, verdict_rows, problem):
    claims = f"\n## Plan (orchestrator)\n{claim_rows}\n## Finding: engine\n{verdict_rows}\n"
    result = gates.run(make_run(tmp_path, claims=claims))
    assert "RESULT: FAIL" in result
    assert problem in result


@pytest.mark.parametrize("heading", ["Plan (orchestrator)", "Finding: engine", "PROJECT GPS"])
def test_duplicate_authoritative_sections_fail(tmp_path, heading):
    claims = ZERO_CLAIMS
    if heading == "PROJECT GPS":
        claims += "\n## PROJECT GPS\nBP_KnownThing\n"
    claims += f"\n## {heading}\nStale evidence.\n"
    assert "RESULT: FAIL" in gates.run(make_run(tmp_path, claims=claims))


@pytest.mark.parametrize("verdict", ["REJECTED", "UNVERIFIABLE"])
def test_unsupported_claim_usage_fails_without_grounding_from_verdict_prose(tmp_path, verdict):
    claims = f"\n## Plan\nCLM-1: BP_UnknownThing exists.\n## Finding: engine\nCLM-1: {verdict} - BP_UnknownThing not established.\n"
    result = gates.run(make_run(tmp_path, artifact=LEDGER_OK + "\nUse BP_UnknownThing", claims=claims))
    assert "RESULT: FAIL" in result and "forbidden symbol" in result


def test_api_description_does_not_confirm_rejected_symbol(tmp_path):
    api = TOOL_API.replace('"tools": [', '"description": "BP_UnknownThing", "tools": [')
    claims = "\n## Plan\nCLM-1: BP_UnknownThing exists.\n## Finding: engine\nCLM-1: REJECTED\n"
    assert "forbidden symbol" in gates.run(make_run(tmp_path, api=api, claims=claims, artifact=LEDGER_OK + "\nBP_UnknownThing"))


def test_confirmed_symbol_does_not_confirm_other_parts_of_rejected_claim(tmp_path):
    claims = "\n## PROJECT GPS\nBP_KnownThing\n## Plan\nCLM-1: BP_KnownThing has OnUnsupportedEvent.\n## Finding: engine\nCLM-1: REJECTED\n"
    result = gates.run(make_run(tmp_path, claims=claims, artifact=LEDGER_OK + "\nBP_KnownThing OnUnsupportedEvent"))
    assert "forbidden symbol 'OnUnsupportedEvent'" in result
    assert "forbidden symbol 'BP_KnownThing'" not in result


@pytest.mark.parametrize("artifact, claims, expected", [(LEDGER_OK, ZERO_CLAIMS, 0), ("bad", ZERO_CLAIMS, 1), (None, ZERO_CLAIMS, 2)])
def test_cli_status_codes(tmp_path, artifact, claims, expected):
    run = make_run(tmp_path, artifact=artifact, claims=claims)
    result = subprocess.run([sys.executable, str(pathlib.Path(gates.__file__)), str(run)], capture_output=True, text=True)
    assert result.returncode == expected, result.stdout + result.stderr


def test_manifest_uses_current_revision_only_and_rejects_tampering(tmp_path):
    import run_state
    project = tmp_path / "Project"
    project.mkdir()
    (project / "Example.uproject").write_text("{}", encoding="utf-8")
    state = run_state.init_run(project, task="gate-test")
    run = pathlib.Path(state["run_dir"])
    synthesis = "\n## Synthesis\nBUILD TASKS\n- [editor] First: build\n"
    (run / "plan.md").write_text("# plan\n" + TOOL_API + ZERO_CLAIMS + synthesis, encoding="utf-8")
    source = project / "builder.md"
    source.write_text("Lane: editor\ninvalid old revision", encoding="utf-8")
    run_state.register_artifact(project, run, task_id="01", source=source, name="result.md")
    source.write_text(LEDGER_OK, encoding="utf-8")
    run_state.register_artifact(project, run, task_id="01", source=source, name="result.md")
    (run / "artifacts" / "unregistered-draft.md").write_text("bad", encoding="utf-8")
    assert "RESULT: PASS" in gates.run(run)
    current = run_state.load_run(project, run)["artifacts"]["result.md"]
    (run / current["path"]).write_text(LEDGER_OK + "tampered", encoding="utf-8")
    result = gates.run(run)
    assert "RESULT: FAIL" in result and "invalid run manifest" in result


def test_malformed_manifest_does_not_fall_back_to_legacy_artifacts(tmp_path):
    run = make_run(tmp_path)
    (run / "run.json").write_text("not json", encoding="utf-8")
    result = gates.run(run)
    assert "RESULT: FAIL" in result and "invalid run manifest" in result


def test_partial_four_of_eight_build_tasks_fail(tmp_path):
    synthesis = "\n## Synthesis (orchestrator)\nBUILD TASKS\n" + "\n".join(
        f"- [editor] Task {i}: build task {i}" for i in range(1, 9))
    run = make_run(tmp_path, claims=ZERO_CLAIMS + synthesis)
    for number in range(2, 5):
        (run / "artifacts" / f"{number:02d}-task.md").write_text(LEDGER_OK, encoding="utf-8")
    result = gates.run(run)
    assert "RESULT: FAIL" in result
    for number in range(5, 9):
        assert f"missing artifact for build task {number:02d}" in result


def test_build_task_coverage_includes_explicit_needs_you_artifact(tmp_path):
    synthesis = "\n## Synthesis\nBUILD TASKS\n- [editor] First: build\n- [needs-you] Second: user input\n"
    run = make_run(tmp_path, claims=ZERO_CLAIMS + synthesis)
    assert "missing artifact for build task 02" in gates.run(run)
    (run / "artifacts" / "02-user.md").write_text("Lane: needs-you\nNO TOOL CALLS\n", encoding="utf-8")
    assert "RESULT: PASS" in gates.run(run)


@pytest.mark.parametrize("name, body, problem", [
    ("02-wrong.md", LEDGER_OK, "lane does not match build task 02"),
    ("01-duplicate.md", LEDGER_OK, "duplicate artifact coverage for build task 01"),
    ("03-unknown.md", LEDGER_OK, "unknown or missing build task ID"),
])
def test_build_task_artifact_mapping_errors(tmp_path, name, body, problem):
    synthesis = "\n## Synthesis\nBUILD TASKS\n- [editor] First: build\n- [needs-you] Second: user input\n"
    run = make_run(tmp_path, claims=ZERO_CLAIMS + synthesis)
    (run / "artifacts" / name).write_text(body, encoding="utf-8")
    result = gates.run(run)
    assert "RESULT: FAIL" in result and problem in result


def test_manifest_build_task_coverage_uses_task_id_not_artifact_name(tmp_path):
    import run_state
    project = tmp_path / "Project"
    project.mkdir()
    (project / "Example.uproject").write_text("{}", encoding="utf-8")
    (project / "Other.uproject").write_text("{}", encoding="utf-8")
    state = run_state.init_run(project / "Example.uproject", task="gate-test")
    run = pathlib.Path(state["run_dir"])
    synthesis = "\n## Synthesis\nBUILD TASKS\n- [editor] First: build\n"
    (run / "plan.md").write_text("# plan\n" + TOOL_API + ZERO_CLAIMS + synthesis, encoding="utf-8")
    source = project / "draft.md"
    source.write_text(LEDGER_OK, encoding="utf-8")
    run_state.register_artifact(project / "Example.uproject", run, task_id="01", source=source, name="arbitrary-name.md")
    assert "RESULT: PASS" in gates.run(run)


def test_fenced_gate_and_authoritative_heading_examples_are_preserved(tmp_path):
    example = "\n## Notes\n```markdown\n## Gate\nexample\n## TOOL API\nexample\n```\n"
    run = make_run(tmp_path, claims=ZERO_CLAIMS + example)
    assert "RESULT: PASS" in gates.run(run)
    assert example.strip() in (run / "plan.md").read_text(encoding="utf-8")
    assert "RESULT: PASS" in gates.run(run)
    assert example.strip() in (run / "plan.md").read_text(encoding="utf-8")


def test_duplicate_build_task_blocks_are_ambiguous(tmp_path):
    synthesis = "\n## Synthesis\nBUILD TASKS\n- [editor] First: build\n\nBUILD TASKS\n- [editor] Hidden: build\n"
    result = gates.run(make_run(tmp_path, claims=ZERO_CLAIMS + synthesis))
    assert "RESULT: FAIL" in result and "duplicate BUILD TASKS" in result


def test_gate_atomic_write_failure_preserves_original_plan(tmp_path, monkeypatch):
    import plan_sections
    run = make_run(tmp_path)
    plan = run / "plan.md"
    original = plan.read_bytes()

    def interrupted_replace(*args, **kwargs):
        raise OSError("simulated interrupted replacement")

    monkeypatch.setattr(plan_sections.os, "replace", interrupted_replace)
    with pytest.raises(OSError, match="simulated interrupted replacement"):
        gates.run(run)
    assert plan.read_bytes() == original
    assert not list(run.glob(".plan-*"))


def test_pre_and_post_build_gps_are_distinct_sections(tmp_path):
    claims = "\n## PROJECT GPS\nBP_KnownThing\n## PROJECT GPS (post-build)\nBP_KnownThing BP_NewThing\n"
    claims += "\n## Plan\nCLM-1: BP_KnownThing has OnUnsupportedEvent.\n## Finding: engine\nCLM-1: REJECTED\n"
    result = gates.run(make_run(tmp_path, claims=claims, artifact=LEDGER_OK + "\nBP_KnownThing"))
    assert "RESULT: PASS" in result
    assert "duplicate PROJECT GPS" not in result


def test_same_lane_synthesis_change_requires_artifact_reregistration(tmp_path):
    import run_state
    project = tmp_path / "Project"
    project.mkdir()
    (project / "Example.uproject").write_text("{}", encoding="utf-8")
    state = run_state.init_run(project, task="gate-test")
    run = pathlib.Path(state["run_dir"])
    synthesis = "\n## Synthesis (design)\nBUILD TASKS\n- [editor] First: build a wall\n"
    plan = run / "plan.md"
    plan.write_text("# plan\n" + TOOL_API + ZERO_CLAIMS + synthesis, encoding="utf-8")
    source = project / "draft.md"
    source.write_text(LEDGER_OK, encoding="utf-8")
    run_state.register_artifact(project, run, task_id="01", source=source, name="result.md")
    assert "RESULT: PASS" in gates.run(run)
    plan.write_text(plan.read_text(encoding="utf-8").replace("build a wall", "build a bridge"), encoding="utf-8")
    result = gates.run(run)
    assert "RESULT: FAIL" in result and "artifact synthesis is stale or missing" in result
    run_state.register_artifact(project, run, task_id="01", source=source, name="result.md")
    assert "RESULT: PASS" in gates.run(run)
    manifest = run / "run.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    del data["artifacts"]["result.md"]["synthesis_sha256"]
    manifest.write_text(json.dumps(data), encoding="utf-8")
    assert "RESULT: FAIL" in gates.run(run)


@pytest.mark.parametrize("synthesis", ["", "\n## Synthesis\nDesign only.\n", "\n## Synthesis\nBUILD TASKS\n"])
def test_manifest_execution_requires_synthesis_build_tasks(tmp_path, synthesis):
    import run_state
    project = tmp_path / "Project"
    project.mkdir()
    (project / "Example.uproject").write_text("{}", encoding="utf-8")
    state = run_state.init_run(project, task="gate-test")
    run = pathlib.Path(state["run_dir"])
    (run / "plan.md").write_text("# plan\n" + TOOL_API + ZERO_CLAIMS + synthesis, encoding="utf-8")
    source = project / "draft.md"
    source.write_text(LEDGER_OK, encoding="utf-8")
    run_state.register_artifact(project, run, task_id="01", source=source, name="result.md")
    result = gates.run(run)
    assert "RESULT: FAIL" in result
    assert "manifest execution requires nonempty BUILD TASKS" in result
    if not synthesis:
        assert "requires exactly one Synthesis section" in result
