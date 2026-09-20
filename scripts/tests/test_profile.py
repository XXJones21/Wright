import json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]

def test_profile_shape():
    p = json.loads((ROOT / "profiles" / "ue5.config.json").read_text(encoding="utf-8"))
    for k in ("engine", "status", "reference_corpus", "execution_lane", "constraints", "footguns", "pattern_table", "ownership"):
        assert k in p, k
    assert p["engine"] == "UE5" and p["reference_corpus"]["kind"] == "unreal_mcp_tool_api"
    assert any("every parameter key" in f.lower() for f in p["footguns"])
    assert any("object path" in f.lower() for f in p["footguns"])
    assert {t["lane"] for t in p["pattern_table"]} >= {"editor", "blueprint", "texture"}
    assert p["execution_lane"]["needs_you"]

def test_unreal_notes_cover_live_footguns():
    txt = (ROOT / "skills/wright/references/unreal-notes.md").read_text(encoding="utf-8").lower()
    for phrase in ("every parameter key", "object path", "refpath", "selectactors", "json string", "mp_", "read back", "sprites"):
        assert phrase in txt, phrase
