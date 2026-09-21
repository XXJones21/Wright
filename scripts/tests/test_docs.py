import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[2]
REFS = ROOT / "skills/wright/references"
DOCS = list(REFS.glob("*.md")) + list((ROOT / "agents").rglob("*.md")) + list((ROOT / "skills").rglob("SKILL.md")) + [ROOT / "README.md"] + list((ROOT / "knowledge-base").glob("*.md"))

DASH_RE = re.compile("[\u2014\u2013]")
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\u2190-\u27BF\u2B00-\u2BFF]")

def test_no_em_dashes_or_emoji():
    bad = []
    for p in DOCS:
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        if DASH_RE.search(t) or EMOJI_RE.search(t):
            bad.append(p.name)
    assert not bad, bad

def test_plan_template_headings_in_order():
    t = (REFS / "plan-template.md").read_text(encoding="utf-8")
    live_order = ["## Task", "## Engine grounding config", "## PROJECT GPS", "## TOOL API", "## PROJECT SKILLS"]
    idx = [t.index(h) for h in live_order]
    assert idx == sorted(idx)

    appended_names = ["Plan (orchestrator)", "Finding: engine", "Finding: reference",
                       "Synthesis (design)", "Artifact <n>: <title>", "Gate",
                       "PROJECT GPS (post-build)", "Validation", "Close"]

    for line in t.splitlines():
        for name in appended_names:
            assert not line.startswith(f"## {name}"), line

    m = re.search(r"```text\n(.*?)\n```", t, re.DOTALL)
    assert m, "missing the append-order fenced block"
    block = m.group(1)

    positions = [block.index(name) for name in appended_names]
    assert positions == sorted(positions)

def test_core_identity_carries_the_four_lenses():
    t = (REFS / "wright-core.md").read_text(encoding="utf-8")
    for w in ("CORE ACTION", "PROVISIONING", "ECONOMY", "ADVERSARY"):
        assert w in t

def test_playbooks_exist():
    for n in ("blueprint-lane-playbook.md", "comfy-texture-playbook.md", "unreal-notes.md"):
        assert (REFS / n).exists(), n

import yaml  # pip install pyyaml

AGENTS = {
    "engine-investigator": {"name": "wright-engine-investigator", "must_have": ["mcp__unreal-mcp__call_tool", "mcp__unreal-mcp__describe_toolset"], "must_not": ["Edit"]},
    "reference-investigator": {"name": "wright-reference-investigator", "must_have": ["WebSearch", "WebFetch"], "must_not": ["mcp__unreal-mcp__call_tool"]},
    "build-executor": {"name": "wright-build-executor", "must_have": ["mcp__unreal-mcp__call_tool", "mcp__plugin_comfy-local-mcp_comfy-local__generate_image", "Bash", "Write"], "must_not": []},
    "validator": {"name": "wright-validator", "must_have": ["mcp__unreal-mcp__call_tool"], "must_not": ["Edit", "mcp__plugin_comfy-local-mcp_comfy-local__generate_image"]},
}

def _frontmatter(p):
    t = p.read_text(encoding="utf-8")
    assert t.startswith("---\n"), p.name
    return yaml.safe_load(t.split("---\n", 2)[1])

def test_agent_frontmatter():
    for fname, spec in AGENTS.items():
        p = ROOT / "agents" / "subagents" / f"{fname}.md"
        if not p.exists():
            continue  # tasks 7 to 10 add them one at a time
        fm = _frontmatter(p)
        assert fm["name"] == spec["name"]
        tools = [x.strip() for x in fm["tools"].split(",")]
        for t in spec["must_have"]:
            assert t in tools, (fname, t)
        for t in spec["must_not"]:
            assert t not in tools, (fname, t)
        assert fm.get("model") == "inherit"

def test_all_four_agents_present():
    for f in AGENTS:
        assert (ROOT / "agents" / "subagents" / f"{f}.md").exists(), f

def test_skill_structure():
    t = (ROOT / "skills/wright/SKILL.md").read_text(encoding="utf-8")
    assert _frontmatter(ROOT / "skills/wright/SKILL.md")["name"] == "wright"
    # A packaged entry point must actually resolve the instructions it sends a
    # fresh Codex instance to; wording/headings are not a behavior test.
    links = re.findall(r"\]\(([^)]+\.md)\)", t)
    assert links
    for target in links:
        assert (ROOT / "skills/wright" / target).is_file(), target
