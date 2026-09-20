import pathlib, re
ROOT = pathlib.Path(__file__).resolve().parents[2]
REFS = ROOT / "skills/wright/references"
DOCS = list(REFS.glob("*.md")) + list((ROOT / "agents").rglob("*.md")) + list((ROOT / "skills").rglob("SKILL.md")) + [ROOT / "README.md"]

def test_no_em_dashes_or_emoji():
    bad = []
    for p in DOCS:
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        if re.search("[—–]", t) or re.search(r"[\U0001F300-\U0001FAFF]", t):
            bad.append(p.name)
    assert not bad, bad

def test_plan_template_headings_in_order():
    t = (REFS / "plan-template.md").read_text(encoding="utf-8")
    order = ["## Task", "## Engine grounding config", "## PROJECT GPS", "## TOOL API", "## PROJECT SKILLS",
             "## Plan (orchestrator)", "## Finding: engine", "## Finding: reference", "## Synthesis (design)"]
    idx = [t.index(h) for h in order]
    assert idx == sorted(idx)

def test_core_identity_carries_the_four_lenses():
    t = (REFS / "wright-core.md").read_text(encoding="utf-8")
    for w in ("CORE ACTION", "PROVISIONING", "ECONOMY", "ADVERSARY"):
        assert w in t

def test_playbooks_exist():
    for n in ("blueprint-lane-playbook.md", "comfy-texture-playbook.md", "unreal-notes.md"):
        assert (REFS / n).exists(), n
