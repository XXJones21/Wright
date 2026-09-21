import json, pathlib, re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

def test_plugin_manifest():
    d = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert d["name"] == "wright"
    assert d["version"]
    assert "description" in d

def test_command_loads_skill():
    txt = (ROOT / "commands" / "run.md").read_text(encoding="utf-8")
    assert "$ARGUMENTS" in txt and "wright" in txt

def test_machine_config_example_fields():
    txt = (ROOT / "skills/wright/references/machine-config.example.md").read_text(encoding="utf-8")
    for f in ("UE_PROJECT_ROOT", "RUNS_DIR", "TEXTURE_STAGING_DIR", "COMFY_TEXTURE_WORKFLOW",
              "COMFY_PLATE_WORKFLOW", "GPS_MAX_CHARS", "DESIGN_DOCS"):
        assert f"`{f}`" in txt

def test_marketplace_lists_wright():
    path = ROOT.parent / ".claude-plugin" / "marketplace.json"
    if not path.exists():
        pytest.skip("marketplace manifest not present")
    m = json.loads(path.read_text(encoding="utf-8"))
    names = [p["name"] for p in m["plugins"]]
    assert "wright" in names
