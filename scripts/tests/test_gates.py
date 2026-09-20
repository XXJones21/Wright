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
