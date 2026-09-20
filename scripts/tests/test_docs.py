import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[2]
REFS = ROOT / "skills/wright/references"
DOCS = list(REFS.glob("*.md")) + list((ROOT / "agents").rglob("*.md")) + list((ROOT / "skills").rglob("SKILL.md")) + [ROOT / "README.md"]

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

    appended_headings = ["## Plan (orchestrator)", "## Finding: engine", "## Finding: reference",
                          "## Synthesis (design)", "## Artifact <n>: <title>", "## Gate",
                          "## PROJECT GPS (post-build)", "## Validation", "## Close"]

    m = re.search(r"```text\n(.*?)\n```", t, re.DOTALL)
    assert m, "missing the append-order fenced block"
    block = m.group(1)
    outside = t[:m.start()] + t[m.end():]

    for h in appended_headings:
        assert h not in outside.splitlines(), h

    positions = [block.index(h) for h in appended_headings]
    assert positions == sorted(positions)

def test_core_identity_carries_the_four_lenses():
    t = (REFS / "wright-core.md").read_text(encoding="utf-8")
    for w in ("CORE ACTION", "PROVISIONING", "ECONOMY", "ADVERSARY"):
        assert w in t

def test_playbooks_exist():
    for n in ("blueprint-lane-playbook.md", "comfy-texture-playbook.md", "unreal-notes.md"):
        assert (REFS / n).exists(), n
