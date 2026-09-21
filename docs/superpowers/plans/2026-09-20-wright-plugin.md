# Wright Standalone Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `wright` Claude Code plugin: a five-beat game-development orchestrator (Plan, Investigate, Synthesize, Execute, Validate) that grounds against a live Unreal Engine 5.8 editor through Epic's Unreal MCP, builds in the editor, and uses ComfyUI for textures and concept plates.

**Architecture:** A conductor skill (`skills/wright/SKILL.md`) runs in the main context, owns a plan file on disk, and dispatches four leaf subagents (engine-investigator, reference-investigator, build-executor, validator) through the Agent tool. Grounding is three allow-lists written into the plan once (engine profile, PROJECT GPS, TOOL API) plus Epic's project Agent Skills; two deterministic Python gates check artifacts before validation. Epic's `unreal-engine-skills-for-claude-code` plugin supplies Unreal onboarding; Wright supplies the game-design method.

**Tech Stack:** Claude Code plugin (markdown skill, agents, command), Python 3.11+ (`scripts/`, pytest, numpy, Pillow), Unreal Engine 5.8 `ModelContextProtocol` + `AllToolsets` via project `.mcp.json`, comfy-local-mcp plugin.

**Spec:** `D:\tools\claude-marketplace\wright\docs\superpowers\specs\2026-09-19-wright-plugin-design.md`. Survey facts: `D:\tools\claude-marketplace\wright\knowledge-base\03-tool-survey.md`.

## Global Constraints

- Plugin repo: `D:\tools\claude-marketplace\wright`, plugin name `wright`, registered in the local marketplace `josh-plugins` (`D:\tools\claude-marketplace\.claude-plugin\marketplace.json`).
- No dependency on Valinor, Hearth, Valar, or Engram. Runtime dependencies: Claude Code, Epic's `unreal-engine-skills-for-claude-code` plugin, the project's `unreal-mcp` server, `comfy-local-mcp`.
- Unreal tool names, verbatim: `mcp__unreal-mcp__list_toolsets`, `mcp__unreal-mcp__describe_toolset`, `mcp__unreal-mcp__call_tool`. They are deferred; the conductor loads them with one ToolSearch call at Gate 0. Subagents grant them in `tools:` frontmatter.
- comfy-local tool names, verbatim: `mcp__plugin_comfy-local-mcp_comfy-local__health`, `..._recommend_workflow`, `..._list_workflows`, `..._generate_image`, `..._get_result`.
- The MCP is single-threaded: build executors run one at a time; investigators may run in parallel; the conductor never calls the MCP while a subagent that holds MCP tools is running.
- Every Unreal call passes every parameter key from the describe schema, optional ones as `null` or `""`. Object references are `{"refPath": "..."}`. Blueprint and asset tools take object paths (`/Game/X/BP_Y.BP_Y`). Tool errors come back as plain strings starting with `Function "` or `Parameter error:`.
- Wright is add-only in the editor: everything it creates lives under `/Game/Wright/<slug>/` and outliner folder `Wright/<slug>`; it never deletes or renames content it did not create in the run. `execute_tool_script` is read-only in Wright.
- Writing rules for every file: no emojis, no em-dashes, no `--` used as an em-dash. Machine-specific paths live only in `machine-config.md` (operator copy of `machine-config.example.md`).
- Commit after every task with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Use `git -c user.name="Joshua Jones" -c user.email="joshuatjones92@gmail.com"` if git identity is unset.
- Tests: `cd D:\tools\claude-marketplace\wright && python -m pytest scripts/tests -q`. Python deps: `pip install pytest numpy pillow`.

## File Structure

| Path | Responsibility |
| --- | --- |
| `.claude-plugin/plugin.json` | plugin manifest |
| `README.md` | install and editor setup, port change, first run |
| `commands/run.md` | `/wright:run` entry that loads the skill |
| `skills/wright/SKILL.md` | the conductor: gates, beats, dispatch, close |
| `skills/wright/references/wright-core.md` | durable identity |
| `skills/wright/references/plan-template.md` | run plan file schema |
| `skills/wright/references/*-prompt.md` | one dispatch template per leaf agent |
| `skills/wright/references/unreal-notes.md` | footguns beyond Epic's skill |
| `skills/wright/references/blueprint-lane-playbook.md` | DSL discipline |
| `skills/wright/references/comfy-texture-playbook.md` | texture recipe |
| `skills/wright/references/blueprint-dsl-docs.txt`, `programmatic-exec-env.txt` | already present from the survey |
| `skills/wright/references/machine-config.example.md` | per-machine fields |
| `profiles/ue5.config.json` | engine grounding profile |
| `agents/subagents/{engine-investigator,reference-investigator,build-executor,validator}.md` | leaf agents |
| `scripts/gates.py` | grounding gate, tool-call gate, build-task parser, CLI |
| `scripts/textures.py` | seamless tile + normal map (ported), CLI |
| `scripts/tests/` | pytest suites |
| `knowledge-base/` | overview, pipeline, survey (present), gotchas, run log |

---

### Task 1: Plugin skeleton and marketplace registration

**Files:**
- Create: `.claude-plugin/plugin.json`, `README.md`, `.gitignore`, `commands/run.md`, `skills/wright/references/machine-config.example.md`
- Modify: `D:\tools\claude-marketplace\.claude-plugin\marketplace.json` (add a `wright` entry)
- Test: `scripts/tests/test_manifest.py`

**Interfaces:**
- Produces: the plugin identity `wright`; the command `/wright:run`; machine-config field names `UE_PROJECT_ROOT`, `RUNS_DIR`, `TEXTURE_STAGING_DIR`, `COMFY_TEXTURE_WORKFLOW`, `COMFY_PLATE_WORKFLOW`, `GPS_MAX_CHARS`, `DESIGN_DOCS` used by every later task.

- [ ] **Step 1: Write the failing manifest test**

`scripts/tests/test_manifest.py`:
```python
import json, pathlib, re
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
    m = json.loads((ROOT.parent / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    names = [p["name"] for p in m["plugins"]]
    assert "wright" in names
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd D:\tools\claude-marketplace\wright && python -m pytest scripts/tests/test_manifest.py -q`
Expected: FAIL (FileNotFoundError on plugin.json).

- [ ] **Step 3: Create the manifest, gitignore, and command**

`.claude-plugin/plugin.json`:
```json
{
  "name": "wright",
  "description": "Game-development reasoning core for Unreal Engine 5.8. A five-beat orchestrator (Plan, Investigate, Synthesize, Execute, Validate) that grounds every claim against the live editor through Epic's Unreal MCP, builds level content, materials, and Blueprints in the editor, generates textures and concept plates with ComfyUI, and hands what it cannot build to the designer as a Needs You list. Layers on Epic's unreal-engine-skills-for-claude-code plugin.",
  "version": "0.1.0",
  "author": { "name": "Joshua Jones" },
  "license": "MIT",
  "keywords": ["claude-code", "unreal-engine", "game-design", "mcp", "comfyui"]
}
```

`.gitignore`:
```
__pycache__/
*.pyc
.pytest_cache/
skills/wright/references/machine-config.md
```

`commands/run.md`:
```markdown
---
description: Run the Wright game-development pipeline (Plan -> Investigate -> Synthesize -> Execute -> Validate) against the live Unreal Engine 5.8 editor.
argument-hint: <task> [--stop-after plan|investigate|synthesize|execute|validate] [--project <ue_project_root>]
---

Load and follow the `wright` skill. Parse the arguments below: everything before the first `--` flag is the task text; `--stop-after <beat>` ends the run after that beat; `--project <path>` overrides `UE_PROJECT_ROOT` from the machine config. Run Gate 0 and Gate 1, then the beats in order, coordinating the leaf subagents through the run's plan file, and finish with the Close summary and the NEEDS YOU list.

Task / arguments:

$ARGUMENTS
```

- [ ] **Step 4: Write the machine-config example**

`skills/wright/references/machine-config.example.md`:
```markdown
# Machine config

The conductor (`skills/wright/SKILL.md`, Step 0.5) reads this file before dispatching any subagent and substitutes the values into every dispatch prompt. This is the ONLY file where machine-specific literals belong. Copy it to `machine-config.md` beside it and edit the values; `machine-config.md` is gitignored.

| Field | Meaning | Default / this machine |
| --- | --- | --- |
| `UE_PROJECT_ROOT` | The Unreal project the run targets. Must contain the `.uproject` and the editor-generated `.mcp.json`. `--project` on the command overrides it. | `D:\UnrealProjects\Retrieval` |
| `RUNS_DIR` | Root for run folders (`<RUNS_DIR>/<slug>/plan.md`). | `<UE_PROJECT_ROOT>\wright\runs` |
| `TEXTURE_STAGING_DIR` | Where ComfyUI textures and their seamless/normal derivatives land before `TextureTools.import_file`. | `<UE_PROJECT_ROOT>\wright\textures` |
| `COMFY_TEXTURE_WORKFLOW` | comfy-local workflow name for seamless texture tiles. Confirm with `list_workflows`. | `scene_image_flux` |
| `COMFY_PLATE_WORKFLOW` | comfy-local workflow name for concept plates. | `scene_image_flux` |
| `GPS_MAX_CHARS` | Character cap for the PROJECT GPS section; truncation is announced, never silent. | `12000` |
| `DESIGN_DOCS` | Comma-separated paths handed to the reference investigator (game design document, slice brief). | `<UE_PROJECT_ROOT>\Documentation\GDD_Retrieval.md` |

## How this gets used
At Step 0.5 the skill reads `machine-config.md` (or this example if the copy is absent) and resolves every `<ue_project_root>`, `<runs_dir>`, `<texture_staging_dir>`, `<comfy_texture_workflow>`, `<comfy_plate_workflow>`, `<gps_max_chars>`, and `<design_docs>` placeholder in the dispatch templates. Subagents never hardcode these paths; they receive them resolved. If `UE_PROJECT_ROOT` cannot be resolved from either file or `--project`, the run stops at Step 0.5.
```

- [ ] **Step 5: Write the README**

`README.md`:
```markdown
# Wright

A game-development reasoning core for Unreal Engine 5.8, packaged as a Claude Code plugin. Wright runs a five-beat pipeline (Plan, Investigate, Synthesize, Execute, Validate): it frames a design as gaps and claims, verifies every claim against the live editor, synthesizes a concrete loop, builds what the editor's MCP can build (level content, materials, Blueprints, data tables), generates textures and concept plates with ComfyUI, and hands the rest to you as a Needs You list.

Wright is the method. Unreal onboarding comes from Epic's `unreal-engine-skills-for-claude-code` plugin, which Wright requires.

## Requirements

1. Unreal Engine 5.8 with a project that has the `ModelContextProtocol` and `AllToolsets` plugins enabled (Edit > Plugins). With only `ModelContextProtocol` enabled the server exposes no editor tools.
2. Editor Preferences > General > Model Context Protocol: Auto Start Server on, port 8000, URL path `/mcp`, Enable Tool Search on.
3. In the editor console: `ModelContextProtocol.GenerateClientConfig ClaudeCode`. This writes `.mcp.json` next to the `.uproject`.
4. Claude Code plugins: `unreal-engine-skills-for-claude-code@claude-plugins-official` and `comfy-local-mcp@josh-plugins`, plus this plugin (`wright@josh-plugins`).
5. ComfyUI running with comfy-local configured (`/comfy-setup` if not).
6. Python 3.11+ with `numpy` and `pillow` for the texture scripts, `pytest` for the tests.

## First run

1. Copy `skills/wright/references/machine-config.example.md` to `machine-config.md` in the same folder and set `UE_PROJECT_ROOT` and `DESIGN_DOCS`.
2. Open the project in the editor and wait for the Output Log line that the MCP server started.
3. Launch Claude Code from the project root (or from the editor's Terminal panel).
4. `/wright:run Design and build the Mission 1 evidence-collection slice --stop-after synthesize` for a design-only pass, or omit the flag for a full build.

Runs land in `<UE_PROJECT_ROOT>/wright/runs/<slug>/`: `plan.md` is the shared state, `artifacts/` holds what was built and the Needs You specs, `plates/` the concept plates, `captures/` the viewport captures.

## Changing the port

If 8000 is taken: set Server Port Number in Editor Preferences, restart the editor, re-run `ModelContextProtocol.GenerateClientConfig ClaudeCode` (it merges into the existing `.mcp.json`), and restart Claude Code. The server name stays `unreal-mcp`, so Wright's tool grants do not change. Epic's optional `unreal-mcp-proxy` registers under a different server name and is not supported by Wright v1.

## Safety

Save and commit the project before a run. Wright creates only under `/Game/Wright/<slug>/` and outliner folder `Wright/<slug>` and never deletes or renames content it did not create in the run. Wright uses `ProgrammaticToolset.execute_tool_script` for read-only batch queries only. After a run, save the level yourself; Wright saves the assets it creates.
```

- [ ] **Step 6: Register in the marketplace**

In `D:\tools\claude-marketplace\.claude-plugin\marketplace.json`, append to the `plugins` array (keep the existing entries):
```json
{
  "name": "wright",
  "source": "./wright",
  "description": "Game-development reasoning core for Unreal Engine 5.8: a five-beat orchestrator that grounds against the live editor via Epic's Unreal MCP, builds in-editor, and uses ComfyUI for textures and concept plates.",
  "author": { "name": "Joshua Jones" },
  "license": "MIT",
  "keywords": ["unreal-engine", "game-design", "mcp", "comfyui", "orchestrator"],
  "category": "development"
}
```
Validate: `python -c "import json; json.load(open(r'D:\tools\claude-marketplace\.claude-plugin\marketplace.json'))"`.

- [ ] **Step 7: Run the tests**

Run: `cd D:\tools\claude-marketplace\wright && python -m pytest scripts/tests/test_manifest.py -q`
Expected: 4 passed.

- [ ] **Step 8: Commit**

```bash
cd D:\tools\claude-marketplace\wright && git add -A && git commit -m "feat: plugin skeleton, README, run command, machine config"
cd D:\tools\claude-marketplace && git status --short   # marketplace.json is outside the wright repo; note the change for the user, do not commit it here unless the marketplace dir is itself a repo
```

---

### Task 2: Grounding gate and parsers (`scripts/gates.py`, part 1)

**Files:**
- Create: `scripts/gates.py`, `scripts/tests/test_gates.py`

**Interfaces:**
- Produces (module `gates`): `parse_clm_claims(plan_beat_text: str) -> dict[str, str]`; `parse_clm_verdicts(text: str) -> list[dict]` with keys `id`, `verdict`, `line`; `extract_symbols(text: str) -> set[str]`; `grounding_gate(rejected_claim_texts: list[str], artifacts: list[tuple[str, str]], gps_text: str = "") -> list[dict]` with keys `artifact`, `symbol`; `parse_build_tasks(synthesis: str, cap: int = 8) -> list[dict]` with keys `title`, `brief`, `lane` (one of `editor`, `blueprint`, `texture`, `needs-you`).

- [ ] **Step 1: Write the failing tests**

`scripts/tests/test_gates.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest scripts/tests/test_gates.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'gates'`.

- [ ] **Step 3: Write the module (ported from Valar `wright_plan.py`, plus lanes)**

`scripts/gates.py`:
```python
"""Deterministic gates for a Wright run. Pure Python, no model, no network.

Ported from Valar's wright_plan.py (grounding gate, claim/verdict parsers) and
extended with lane tags on build tasks and a tool-call gate (see part 2).
"""
from __future__ import annotations

import re

LANES = ("editor", "blueprint", "texture", "needs-you")

_CLM_LINE = re.compile(
    r"^[\s>*_`-]*`?(CLM[\s_-]?\d+)`?[\s:.)\]\-]*(.*?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_VERDICT = re.compile(r"\b(VERIFIED|REJECTED|UNVERIFIABLE)\b", re.IGNORECASE)
_CAMEL = re.compile(r"\b([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+)\b")
_SNAKE = re.compile(r"\b([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\b")
_SPAN = re.compile(r"[`\"'\u201c]([^`\"'\u201d\n]{2,48})[`\"'\u201d]")
_LANE = re.compile(r"^\[(editor|blueprint|texture|needs-you)\]\s*", re.IGNORECASE)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _clm_id(raw: str) -> str | None:
    m = re.search(r"\d+", raw or "")
    return f"CLM-{m.group(0)}" if m else None


def parse_clm_claims(plan_beat_text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in _CLM_LINE.finditer(plan_beat_text or ""):
        cid = _clm_id(m.group(1))
        body = (m.group(2) or "").strip()
        if cid and body and cid not in out:
            out[cid] = body
    return out


def parse_clm_verdicts(investigator_text: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for m in _CLM_LINE.finditer(investigator_text or ""):
        cid = _clm_id(m.group(1))
        if not cid or cid in seen:
            continue
        v = _VERDICT.search(m.group(2) or "")
        if not v:
            continue
        seen.add(cid)
        out.append({"id": cid, "verdict": v.group(1).upper(), "line": m.group(0).strip()})
    return out


def extract_symbols(text: str) -> set[str]:
    syms: set[str] = set()
    for rx in (_CAMEL, _SNAKE):
        syms.update(m.group(1) for m in rx.finditer(text or ""))
    for m in _SPAN.finditer(text or ""):
        s = m.group(1).strip()
        if 2 <= len(s) <= 48:
            syms.add(s)
    return syms


def grounding_gate(rejected_claim_texts: list[str], artifacts: list[tuple[str, str]],
                   gps_text: str = "") -> list[dict]:
    """A symbol named in a REJECTED claim and absent from the GPS is forbidden;
    return every (artifact, symbol) where a forbidden symbol appears."""
    gps_n = _norm(gps_text)
    forbidden: dict[str, str] = {}
    for claim in rejected_claim_texts:
        for s in extract_symbols(claim):
            ns = _norm(s)
            if len(ns) < 6:
                continue
            if ns not in gps_n:
                forbidden.setdefault(ns, s)
    flags: list[dict] = []
    for title, content in artifacts:
        cn = _norm(content)
        for ns, orig in forbidden.items():
            if ns in cn:
                flags.append({"artifact": title, "symbol": orig})
    return flags


def parse_build_tasks(synthesis: str, cap: int = 8) -> list[dict]:
    """Lines under a BUILD TASKS heading: `- [lane] <title>: <brief>`.
    Lane defaults to editor. Stops at the first non-list line."""
    tasks: list[dict] = []
    in_block = False
    for ln in (synthesis or "").splitlines():
        s = ln.strip()
        if not in_block:
            if re.match(r"^#*\s*BUILD\s+TASKS\b", s, re.IGNORECASE):
                in_block = True
            continue
        if not s:
            continue
        m = re.match(r"^[-*\d.)\s]+(.+)$", s)
        if not m:
            break
        item = m.group(1).strip()
        lane = "editor"
        lm = _LANE.match(item)
        if lm:
            lane = lm.group(1).lower()
            item = item[lm.end():]
        title, _, brief = item.partition(":")
        tasks.append({"title": title.strip(), "brief": brief.strip() or title.strip(), "lane": lane})
        if len(tasks) >= cap:
            break
    return tasks
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest scripts/tests/test_gates.py -q`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/gates.py scripts/tests/test_gates.py
git commit -m "feat(gates): port grounding gate, claim parsers, lane-tagged build tasks"
```

---

### Task 3: Tool-call gate and the gates CLI (`scripts/gates.py`, part 2)

**Files:**
- Modify: `scripts/gates.py` (append)
- Modify: `scripts/tests/test_gates.py` (append)

**Interfaces:**
- Consumes: the plan file layout from Task 6 (`## TOOL API` section containing one fenced ```json block per toolset, each the raw `describe_toolset` result with a `tools` list of `{name, inputSchema.properties}`); executor artifacts in `<run_dir>/artifacts/*.md` each ending with a fenced ```jsonl block headed `CALL LEDGER` whose lines are `{"toolset": "<fq name>", "tool": "<name>", "args": ["key", ...]}`.
- Produces: `parse_tool_api(plan_text) -> dict[str, dict[str, set[str]]]` (toolset -> tool -> allowed arg keys); `parse_call_ledger(artifact_text) -> list[dict]`; `tool_call_gate(api, ledger_entries, artifact_title) -> list[dict]` with keys `artifact`, `toolset`, `tool`, `problem`; `run(run_dir: Path) -> str` that appends a `## Gate` section to `<run_dir>/plan.md` and returns it; CLI `python scripts/gates.py <run_dir>` exiting 0 on PASS or INCONCLUSIVE, 1 on FAIL.

- [ ] **Step 1: Append the failing tests**

Append to `scripts/tests/test_gates.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest scripts/tests/test_gates.py -q`
Expected: 6 new failures (`AttributeError: module 'gates' has no attribute 'parse_tool_api'`).

- [ ] **Step 3: Append the implementation**

Append to `scripts/gates.py`:
```python
import json
import sys
from pathlib import Path

_FENCE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)


def parse_tool_api(plan_text: str) -> dict[str, dict[str, set[str]]]:
    """Read every fenced json block under `## TOOL API` (up to the next `## `
    heading) and index toolset -> tool -> allowed argument keys."""
    api: dict[str, dict[str, set[str]]] = {}
    m = re.search(r"^## TOOL API\s*$(.*?)(?=^## |\Z)", plan_text or "", re.MULTILINE | re.DOTALL)
    if not m:
        return api
    for lang, body in _FENCE.findall(m.group(1)):
        if (lang or "").lower() != "json":
            continue
        try:
            d = json.loads(body)
        except json.JSONDecodeError:
            continue
        tools = d.get("tools") if isinstance(d, dict) else d
        for t in tools or []:
            full = t.get("name", "")
            toolset, _, tool = full.rpartition(".")
            props = ((t.get("inputSchema") or t.get("input_schema") or {}).get("properties") or {})
            api.setdefault(toolset, {})[tool] = set(props.keys())
    return api


def parse_call_ledger(artifact_text: str) -> list[dict]:
    """The `CALL LEDGER` jsonl fence in an artifact: one call per line."""
    entries: list[dict] = []
    m = re.search(r"CALL LEDGER\s*```jsonl\n(.*?)```", artifact_text or "", re.DOTALL)
    if not m:
        return entries
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            e = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict) and "toolset" in e and "tool" in e:
            e.setdefault("args", [])
            entries.append(e)
    return entries


def tool_call_gate(api: dict, entries: list[dict], artifact_title: str) -> list[dict]:
    flags: list[dict] = []
    for e in entries:
        ts, tool = e["toolset"], e["tool"]
        base = {"artifact": artifact_title, "toolset": ts, "tool": tool}
        if ts not in api:
            flags.append({**base, "problem": "unknown toolset"})
            continue
        if tool not in api[ts]:
            flags.append({**base, "problem": "unknown tool"})
            continue
        for a in e.get("args", []):
            if a not in api[ts][tool]:
                flags.append({**base, "problem": f"unknown argument: {a}"})
    return flags


def _section(plan_text: str, heading_prefix: str) -> str:
    m = re.search(rf"^## {re.escape(heading_prefix)}.*?$(.*?)(?=^## |\Z)", plan_text, re.MULTILINE | re.DOTALL)
    return m.group(1) if m else ""


def run(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    plan_path = run_dir / "plan.md"
    plan = plan_path.read_text(encoding="utf-8") if plan_path.exists() else ""
    artifacts: list[tuple[str, str]] = []
    for p in sorted((run_dir / "artifacts").glob("*.md")) if (run_dir / "artifacts").exists() else []:
        artifacts.append((p.stem, p.read_text(encoding="utf-8")))

    gps = _section(plan, "PROJECT GPS")
    claims = parse_clm_claims(_section(plan, "Plan"))
    verdicts = parse_clm_verdicts(_section(plan, "Finding: engine"))
    rejected = [claims[v["id"]] for v in verdicts if v["verdict"] == "REJECTED" and v["id"] in claims]
    g_flags = grounding_gate(rejected, artifacts, gps)

    api = parse_tool_api(plan)
    t_flags: list[dict] = []
    for title, text in artifacts:
        t_flags += tool_call_gate(api, parse_call_ledger(text), title)

    lines = ["## Gate", ""]
    if not artifacts:
        lines.append("INCONCLUSIVE: no artifacts found under artifacts/.")
        status = "INCONCLUSIVE"
    else:
        status = "PASS" if not g_flags and not t_flags else "FAIL"
        lines.append(f"Grounding gate: {'PASS' if not g_flags else 'FAIL'} "
                     f"({len(rejected)} rejected claim(s), {len(artifacts)} artifact(s) scanned).")
        for f in g_flags:
            lines.append(f"- forbidden symbol {f['symbol']!r} in artifact '{f['artifact']}'")
        if not api:
            lines.append("Tool-call gate: INCONCLUSIVE (no TOOL API section in the plan).")
            if status == "PASS":
                status = "INCONCLUSIVE"
        else:
            lines.append(f"Tool-call gate: {'PASS' if not t_flags else 'FAIL'} "
                         f"({sum(len(parse_call_ledger(t)) for _, t in artifacts)} call(s) checked).")
            for f in t_flags:
                lines.append(f"- {f['toolset']}.{f['tool']} in '{f['artifact']}': {f['problem']}")
        lines.append("")
        lines.append(f"RESULT: {status}. " + ("The Validator may not sign off; the builder must re-emit." if status == "FAIL"
                     else "The Validator still performs the prose-level scan."))
    section = "\n".join(lines) + "\n"
    with plan_path.open("a", encoding="utf-8") as fh:
        fh.write("\n" + section)
    return section


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python gates.py <run_dir>", file=sys.stderr)
        sys.exit(2)
    out = run(Path(sys.argv[1]))
    print(out)
    sys.exit(1 if "RESULT: FAIL" in out else 0)
```

- [ ] **Step 4: Run all gate tests**

Run: `python -m pytest scripts/tests/test_gates.py -q`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/gates.py scripts/tests/test_gates.py
git commit -m "feat(gates): tool-call gate against the TOOL API block and a run-dir CLI"
```

---

### Task 4: Texture scripts (`scripts/textures.py`)

**Files:**
- Create: `scripts/textures.py`, `scripts/tests/test_textures.py`

**Interfaces:**
- Produces: `make_seamless(rgb: np.ndarray, band: float = 0.18) -> np.ndarray` (float32 HxWx3 in 0..1); `normal_from_luminance(rgb: np.ndarray, strength: float = 6.0, blur: float = 2.5) -> np.ndarray` (uint8 HxWx3); CLI `python scripts/textures.py <in.png> <out_albedo.png> <out_normal.png> [--strength 6] [--blur 2.5]`. This is the only texture entry point the executor uses (spec 5.1 step 2); it replaces `make_seamless_normal.py` and `height2normal.py`.

- [ ] **Step 1: Write the failing tests**

`scripts/tests/test_textures.py`:
```python
import sys, pathlib, subprocess
import numpy as np
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import textures

def _noise(h=64, w=64, seed=1):
    rng = np.random.default_rng(seed)
    return rng.random((h, w, 3), dtype=np.float32)

def test_make_seamless_matches_opposite_edges():
    a = _noise()
    s = textures.make_seamless(a)
    assert s.shape == a.shape and s.dtype == np.float32
    assert np.abs(s[0, :, :] - s[-1, :, :]).mean() < np.abs(a[0, :, :] - a[-1, :, :]).mean()
    assert np.abs(s[:, 0, :] - s[:, -1, :]).mean() < np.abs(a[:, 0, :] - a[:, -1, :]).mean()

def test_normal_is_blue_dominant_and_uint8():
    n = textures.normal_from_luminance(_noise(), strength=6.0, blur=2.5)
    assert n.dtype == np.uint8 and n.shape == (64, 64, 3)
    assert n[..., 2].mean() > 150

def test_flat_image_gives_neutral_normal():
    flat = np.full((16, 16, 3), 0.5, dtype=np.float32)
    n = textures.normal_from_luminance(flat)
    assert np.allclose(n[..., :2], 127, atol=2) and (n[..., 2] >= 253).all()

def test_cli_writes_both_files(tmp_path):
    src = tmp_path / "in.png"
    Image.fromarray((_noise() * 255).astype(np.uint8), "RGB").save(src)
    alb, nrm = tmp_path / "alb.png", tmp_path / "nrm.png"
    r = subprocess.run([sys.executable, str(pathlib.Path(textures.__file__)), str(src), str(alb), str(nrm), "--strength", "6"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert Image.open(alb).size == (64, 64) and Image.open(nrm).size == (64, 64)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest scripts/tests/test_textures.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'textures'`.

- [ ] **Step 3: Write the module (port of TheArchive's `make_seamless_normal.py`)**

`scripts/textures.py`:
```python
"""Seamless tile plus wrap-aware normal map, the-archive's verified recipe.

(a) seamless: roll the image by half in both axes, then smoothstep cross-fade
    the original against the rolled copy weighted by distance to the border
    (border trusts the rolled, continuous copy; center trusts the original).
(b) normal: wrap-aware Sobel on a Gaussian-blurred luminance of the SEAMLESS
    image at the given strength. Strength ~6 makes a flat print read as form.

CLI: python textures.py <in.png> <out_albedo.png> <out_normal.png> [--strength 6] [--blur 2.5]
"""
from __future__ import annotations

import argparse
import numpy as np
from PIL import Image, ImageFilter


def make_seamless(rgb: np.ndarray, band: float = 0.18) -> np.ndarray:
    a = rgb.astype(np.float32)
    H, W, _ = a.shape
    rolled = np.roll(np.roll(a, H // 2, axis=0), W // 2, axis=1)
    yy = np.linspace(0, 1, H, endpoint=False)
    xx = np.linspace(0, 1, W, endpoint=False)
    dy = np.minimum(yy, 1 - yy)
    dx = np.minimum(xx, 1 - xx)
    DX, DY = np.meshgrid(dx, dy)
    d = np.minimum(DX, DY)
    t = np.clip(d / band, 0, 1)
    w = (t * t * (3 - 2 * t))[..., None]
    return (a * w + rolled * (1 - w)).astype(np.float32)


def _sobel_wrap(h: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    kx = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
    ky = kx.T
    gx = np.zeros_like(h)
    gy = np.zeros_like(h)
    for i in range(3):
        for j in range(3):
            sh = np.roll(np.roll(h, i - 1, axis=0), j - 1, axis=1)
            gx += kx[i, j] * sh
            gy += ky[i, j] * sh
    return gx, gy


def normal_from_luminance(rgb: np.ndarray, strength: float = 6.0, blur: float = 2.5) -> np.ndarray:
    a = rgb.astype(np.float32)
    lum = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    lum_img = Image.fromarray(np.clip(lum * 255, 0, 255).astype(np.uint8), "L")
    if blur > 0:
        lum_img = lum_img.filter(ImageFilter.GaussianBlur(radius=blur))
    h = np.asarray(lum_img, dtype=np.float32) / 255.0
    gx, gy = _sobel_wrap(h)
    nx, ny, nz = -gx * strength, -gy * strength, np.ones_like(h)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / ln * 0.5 + 0.5, ny / ln * 0.5 + 0.5, nz / ln * 0.5 + 0.5], axis=-1) * 255.0
    return np.clip(nrm, 0, 255).astype(np.uint8)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inp")
    p.add_argument("out_albedo")
    p.add_argument("out_normal")
    p.add_argument("--strength", type=float, default=6.0)
    p.add_argument("--blur", type=float, default=2.5)
    p.add_argument("--band", type=float, default=0.18)
    args = p.parse_args()
    rgb = np.asarray(Image.open(args.inp).convert("RGB"), dtype=np.float32) / 255.0
    seam = make_seamless(rgb, band=args.band)
    Image.fromarray(np.clip(seam * 255, 0, 255).astype(np.uint8), "RGB").save(args.out_albedo)
    Image.fromarray(normal_from_luminance(seam, args.strength, args.blur), "RGB").save(args.out_normal)
    print("wrote", args.out_albedo, args.out_normal, "strength", args.strength, "blur", args.blur)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests**

Run: `python -m pytest scripts/tests/test_textures.py -q`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/textures.py scripts/tests/test_textures.py
git commit -m "feat(textures): seamless tile and wrap-aware normal map with CLI"
```

---

### Task 5: Engine profile and Unreal notes

**Files:**
- Create: `profiles/ue5.config.json`, `skills/wright/references/unreal-notes.md`, `scripts/tests/test_profile.py`

**Interfaces:**
- Produces: the profile JSON the conductor pastes into the plan under `## Engine grounding config` (keys `engine`, `status`, `reference_corpus`, `execution_lane`, `constraints`, `footguns`, `pattern_table`, `ownership`); `unreal-notes.md`, which every leaf agent is told to read.

- [ ] **Step 1: Write the failing test**

`scripts/tests/test_profile.py`:
```python
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest scripts/tests/test_profile.py -q`
Expected: FAIL, FileNotFoundError.

- [ ] **Step 3: Write the profile**

`profiles/ue5.config.json`:
```json
{
  "engine": "UE5",
  "version": "5.8",
  "status": "active, profile #1 (Retrieval validation vertical, Mission 1 First Light)",
  "reference_corpus": {
    "kind": "unreal_mcp_tool_api",
    "rule": "The TOOL API block in the plan (describe_toolset output) is the allow-list for calls: a toolset, tool, argument key, or enum value not present there does not exist. BlueprintTools.find_node_types and get_node_type_pins are the allow-list for Blueprint node type ids and pin names. ObjectTools.list_properties is the allow-list for UClass properties. The PROJECT GPS is the allow-list for content: an actor, asset, Blueprint, variable, or function not listed there does not exist in the project.",
    "discovery": "list_toolsets, then describe_toolset before any call into a toolset; never assume a signature."
  },
  "execution_lane": {
    "editor": "SceneTools, PrimitiveTools, ActorTools, StaticMeshTools, ObjectTools, AssetTools, EditorAppToolset: Wright places, transforms, tags, foldering, assigns materials, captures, saves.",
    "blueprint": "BlueprintTools plus DataTableTools and GameplayTagsToolset: Wright creates Blueprints, variables, components, events, dispatchers, writes graphs through write_graph_dsl, compiles, reads back.",
    "texture": "comfy-local generate_image, scripts/textures.py, TextureTools.import_file, MaterialTools or MaterialInstanceTools, assign, read back.",
    "needs_you": "C++ edits and new UFUNCTIONs (LiveCodingToolset.CompileLiveCoding exists but new declarations need an editor restart), level creation (no tool), Fab or Bridge downloads, external asset packs, anything no toolset exposes.",
    "rule": "Wright acts through the MCP and never claims a result its call ledger and read-backs do not show. Anything it cannot perform is handed to the designer as a Needs You spec."
  },
  "constraints": [
    "Tool calls execute serially on the editor game thread: one build executor at a time; never overlap MCP calls.",
    "Primitives are limited to add_cube, add_cylinder, add_sphere, add_cone (components on a host actor). Richer geometry comes only from existing Content or StaticMeshTools.import_file of a staged file.",
    "There is no level-creation tool; SceneTools.load_level opens existing levels only. Wright builds in the level named by the task.",
    "Per-call latency grows with actor count (~0.09 s empty to ~1 s at ~260 actors). Keep hero actors in the tens; represent mass as a mesh plus texture or a PCG scatter, never hundreds of actors.",
    "ProgrammaticToolset.execute_tool_script is privileged; Wright uses it only for read-only batch queries (the GPS snapshot), never for mutation.",
    "Blueprint structural changes (components, variables, function signatures) do not exist on the CDO or spawned instances until compile_blueprint runs.",
    "Editor-only tools misbehave during Play In Editor; check IsPIERunning before asset work and do not start PIE in v1."
  ],
  "footguns": [
    "Every parameter key in the describe schema must be present in the call, optional ones as explicit null or an empty string; a missing key is rejected with 'input param ... is required'. Build argument objects from the schema, never from memory.",
    "Object references are {\"refPath\": \"...\"} in and out. Actor refPaths look like /Game/<Level>.<Level>:PersistentLevel.<ActorName>; graph refPaths like /Game/.../BP_X.BP_X:EventGraph.",
    "AssetTools.find_assets returns package paths (/Game/X/BP_Y); Blueprint and asset tools need the object path (/Game/X/BP_Y.BP_Y). Append '.' plus the asset name before passing it on.",
    "A parameter or schema error is returned as a plain string starting with 'Function \"' or 'Parameter error:', not as an MCP error. String-check every result; anything that is not an explicit success is a stop.",
    "ObjectTools.set_properties takes values as a JSON STRING, not an object. A material refPath inside it needs the full Package.Object form.",
    "overrideMaterials set through set_properties can return true and silently not persist; read back with get_properties and rebuild the actor if it did not take. add_* primitives attach as SECONDARY components, so iterate every StaticMeshComponent from get_components when assigning materials.",
    "MaterialTools.connect_to_output material_property values need the MP_ prefix (MP_BaseColor, MP_Normal, MP_EmissiveColor); a bare BaseColor errors. TextureSample outputs are RGB, R, G, B, A, RGBA.",
    "An xform with a rotation must give pitch, yaw, and roll together; omit a field for identity. Units are centimeters, Z up.",
    "EditorAppToolset.CaptureViewport requires captureTransform, annotations, and bShowUI keys; captureTransform null captures the current viewport. Call SelectActors with an empty list first or the selection outline and gizmo bake into the capture. Editor sprites (lights, player start, cameras) and the axis widget still appear with bShowUI false; reviewers ignore them.",
    "SceneTools.find_actors returns refPaths only; the label comes from ActorTools.get_label and the class from ObjectTools.get_class. Batch-spawned actors share a _UAID_ segment.",
    "The template level already has a DirectionalLight and sky; adding another directional light triggers a competing-lights warning. Reuse the existing sun.",
    "Pure Blueprint node outputs are recomputed per connected wire; store a reused result in a variable. Casting to a Blueprint class creates a hard load dependency; prefer interfaces.",
    "BlueprintTools.write_graph_dsl compiles the Blueprint; a compile warning or error comes back in the result text, not as an exception. Class paths, enum values, and asset refs inside DSL must be quoted strings."
  ],
  "pattern_table": [
    {"lane": "editor", "task": "spawn a placed form", "pattern": "SceneTools.add_to_scene_from_class {actor_type:{refPath:'/Script/Engine.StaticMeshActor'}, name, xform, parent:null, snap_to_ground:false} -> returnValue.refPath; PrimitiveTools.add_cube {actor:{refPath}, name, dimensions:{x,y,z}, local_transform:null}; ActorTools.get_components {actor, component_type:{refPath:'/Script/Engine.StaticMeshComponent'}}; ObjectTools.set_properties {instance:<component>, values:'{\"overrideMaterials\":[{\"refPath\":\"/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial\"}]}'}; get_properties read-back; SceneTools.set_actor_folder {actor, folder_path:'Wright/<slug>'}"},
    {"lane": "editor", "task": "look at the result", "pattern": "EditorAppToolset.SelectActors {actors:[]}; SetCameraTransform {transform:{location, rotation, scale}}; CaptureViewport {captureTransform:null, annotations:{gridSpacing:0, gridExtent:0, gridHeight:0, maxLabelDistance:0}, bShowUI:false} -> returnValue.image.data (base64 PNG); decode to <run_dir>/captures/<n>.png and Read it"},
    {"lane": "editor", "task": "read what exists", "pattern": "SceneTools.get_current_level {}; find_actors {root:null, name:'', actor_type:null, tag:'', bounds:null, collision_channels:null}; per actor ActorTools.get_label, ObjectTools.get_class, ActorTools.get_actor_transform; AssetTools.find_assets {folder_path:'/Game', name:'', asset_type:{refPath:'/Script/Engine.Blueprint'}, recursive:true, tags:null}"},
    {"lane": "blueprint", "task": "author a Blueprint actor with logic", "pattern": "AssetTools.create_folder {path:'/Game/Wright/<slug>'}; BlueprintTools.create {folder_path, asset_name, asset_type:{refPath:'/Script/Engine.Actor'}} -> blueprint ref (object path); add_variable {blueprint, name, type_name, graph:null, container_type:null}; ActorTools.add_component {owner:<blueprint>, component_type:{refPath:'/Script/Engine.StaticMeshComponent'}, name}; get_graph {blueprint, graph_name:'EventGraph'}; find_node_types {graph, type_id_filter:'<word>', context_pins:null} and get_node_type_pins before any DSL; write_graph_dsl {graph, code}; compile_blueprint {blueprint, warnings_as_errors:true}; read_graph_dsl {graph} and diff; AssetTools.save_assets {asset_paths:[...]}"},
    {"lane": "blueprint", "task": "tuning values the economy lens produced", "pattern": "DataTableTools.search_row_structs {struct_name:'<hint>'}; create {folder_path, asset_name, schema}; add_rows {data_table, row_names}; set_rows {data_table, values}; get_rows read-back"},
    {"lane": "texture", "task": "a seamless PBR tile on a surface", "pattern": "comfy recommend_workflow {goal:'image seamless tileable texture'}; generate_image {prompt, workflow, width:1024, height:1024}; python scripts/textures.py <in> <albedo> <normal> --strength 6; TextureTools.import_file {folder_path:'/Game/Wright/<slug>', asset_name:'T_<name>_A', source_file}; same for _N; MaterialTools.create_material; add_expression TextureSample x2 plus TextureCoordinate; ObjectTools.set_properties on the normal sample values:'{\"texture\":{\"refPath\":\"/Game/Wright/<slug>/T_<name>_N.T_<name>_N\"},\"samplerType\":\"SAMPLERTYPE_Normal\"}'; connect_to_output RGB -> MP_BaseColor and RGB -> MP_Normal; recompile; assign via overrideMaterials on every StaticMeshComponent; read back; save_assets"}
  ],
  "ownership": {
    "content_root": "/Game/Wright/<slug>/",
    "outliner_folder": "Wright/<slug>",
    "rule": "add-only: never remove_from_scene, delete, move, or rename anything not created in this run; save_assets on what you create; tell the operator to save the level."
  }
}
```

- [ ] **Step 4: Write the Unreal notes**

`skills/wright/references/unreal-notes.md`:
```markdown
# Unreal notes for Wright agents

Epic's `unreal-mcp` skill (plugin `unreal-engine-skills-for-claude-code`) owns discovery (`list_toolsets`, `describe_toolset`, `call_tool`), the safety rules (save first, wait for compiles, check every result, mind PIE), and project Agent Skills. Read it first. This file holds only what that skill does not say, all confirmed live on UE 5.8.

## Calls
- Every parameter key must be present. Build each argument object from the describe schema; pass optional keys as `null` or `""`. `find_actors` needs all six keys; `CaptureViewport` all three.
- Object references are `{"refPath": "..."}` both ways. `find_assets` returns package paths; append `.` plus the asset name to get the object path Blueprint and asset tools need.
- Errors arrive as plain strings (`Function "...`, `Parameter error: ...`). String-check every result.
- `ObjectTools.set_properties` `values` is a JSON string. Material refPaths inside it use `Package.Object` form. Read back with `get_properties`; if `overrideMaterials` came back empty, rebuild the actor.
- Primitives attach as secondary components: iterate every StaticMeshComponent from `get_components`.
- `connect_to_output` needs `MP_`-prefixed properties. Rotation needs pitch, yaw, and roll together. Units cm, Z up.

## Captures
- `SelectActors([])` before every capture. `captureTransform: null` captures the current viewport; pass the `GetCameraTransform` result to be explicit. Editor sprites and the axis widget remain; ignore them when reviewing. Decode `returnValue.image.data` (base64 PNG) to `<run_dir>/captures/` and Read it.
- Assign a lit material to blockout geometry before capturing; null-material primitives render black.

## Blueprints
- `get_graph_dsl_docs` and `find_node_types` before writing DSL; node type ids are `Category|Title`; quote class paths, enums, and asset refs.
- `write_graph_dsl` compiles; read the result text for warnings. Compile with `warnings_as_errors: true` once per logical unit, then `read_graph_dsl` and compare to intent.
- Structural changes need a compile before they exist on the CDO.

## Ledger
Every mutating and read call an executor makes goes into its artifact's `CALL LEDGER` fence as `{"toolset": "<fully qualified>", "tool": "<name>", "args": ["<key>", ...]}` so the tool-call gate can check it.
```

- [ ] **Step 5: Run the tests and commit**

Run: `python -m pytest scripts/tests/test_profile.py -q`
Expected: 2 passed.

```bash
git add profiles/ue5.config.json skills/wright/references/unreal-notes.md scripts/tests/test_profile.py
git commit -m "feat(profile): UE 5.8 grounding profile and Unreal notes from the survey"
```

---

### Task 6: Core identity, plan template, lane playbooks, docs lint

**Files:**
- Create: `skills/wright/references/wright-core.md`, `skills/wright/references/plan-template.md`, `skills/wright/references/blueprint-lane-playbook.md`, `skills/wright/references/comfy-texture-playbook.md`, `scripts/tests/test_docs.py`

**Interfaces:**
- Produces: the plan file section headings every agent and gate depends on, in this order: `## Task`, `## Engine grounding config`, `## PROJECT GPS`, `## TOOL API`, `## PROJECT SKILLS`, `## Plan (orchestrator)`, `## Finding: engine`, `## Finding: reference`, `## Synthesis (design)`, `## Artifact <n>: <title>`, `## Gate` (appended by gates.py), `## PROJECT GPS (post-build)`, `## Validation`, `## Close`. `gates.run` reads `Plan`, `Finding: engine`, `PROJECT GPS`, `TOOL API` by these exact prefixes.

- [ ] **Step 1: Write the failing docs lint test**

`scripts/tests/test_docs.py`:
```python
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
        if re.search("[\u2014\u2013]", t) or re.search(r"[\U0001F300-\U0001FAFF]", t):
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
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest scripts/tests/test_docs.py -q`
Expected: FAIL on the missing files.

- [ ] **Step 3: Port the core identity**

Copy `D:\Tools\Valinor\Persona\Wright\wright-core.md` to `skills/wright/references/wright-core.md`, then edit:
- Replace the `## Architecture` section body with: "Wright is a game-design orchestrator run by the `wright` Claude Code skill. The conductor holds the Plan and Synthesize beats; the Engine Investigator, Reference Investigator, Build Executor, and Validator are leaf subagents. The plan file under `<RUNS_DIR>/<slug>/plan.md` is the only shared state. The design is in `docs/superpowers/specs/2026-09-19-wright-plugin-design.md`."
- Delete the `## Three-layer memory model` and `## Standing artifacts` sections.
- In the shared core, replace the stance bullet "You propose; the human decides and runs. You never claim to have placed, wired, compiled, or shipped anything yourself..." with: "You act in the editor through the Unreal MCP and never claim to have done what your call ledger and read-backs do not show. What you cannot perform (C++, level creation, external assets) you hand to the designer as a Needs You spec. The designer still decides; you widen the solution space and recommend."
- In "Grounding discipline", replace "The engine's reference corpus is the allow-list" paragraph with the profile's `reference_corpus.rule` text, and "PROJECT GPS" wording stays as is (it now lists actors, assets, Blueprints, variables, functions).
- Replace every em-dash with a comma or a period. Keep the four-lens paragraph verbatim (CORE ACTION, PROVISIONING, ECONOMY, ADVERSARY AND EXITS).
- Replace the final paragraph ("You run as one focused subagent...") with: "The conductor runs Plan and Synthesize in the main context; each leaf agent receives only its dispatch prompt and the plan file, does its one beat, and hands the result forward."

- [ ] **Step 4: Write the plan template**

`skills/wright/references/plan-template.md`:
```markdown
# Wright run plan: <slug>

Shared state for the Wright pipeline. The conductor appends each section; every agent reads the whole file. Sections appear in this order and are never reordered.

- Run slug: <slug>
- Created: <YYYY-MM-DD>
- Project: <ue_project_root>
- Level: <level asset path from get_current_level>
- Stop after: <beat or "validate">
- Design docs: <design_docs>

## Task

<the task text verbatim>

## Engine grounding config

<contents of profiles/ue5.config.json, verbatim, as a ```json fence>

## PROJECT GPS

Snapshot of what exists in the live project at Gate 1. Read-only ground truth.

### Level
- Path: <level path>
- Outliner folders: <get_folders>

### Actors (<count>)
| refPath tail | label | class | location |
| --- | --- | --- | --- |

### Assets under /Game
- Folders: <list_folders /Game>
- Blueprints (<count>): <object paths>
- Materials (<count>): <object paths>
- Textures (<count>): <object paths>
- Data tables (<count>): <object paths>

### Blueprints named by the task
For each: parent class, variables (list_variables), functions (list_functions), custom events (list_events), and the EventGraph as DSL (read_graph_dsl).

<truncation notice if GPS_MAX_CHARS was hit: "GPS TRUNCATED at <n> chars: <what was cut>">

## TOOL API

One ```json fence per toolset the run will touch, the raw describe_toolset result. The tool-call gate reads these.

### <fully qualified toolset name>
```json
{}
```

## PROJECT SKILLS

Output of AgentSkillToolset.GetSkills for every skill ListSkills returned whose description matches the task (always: BlueprintBasicsSkill, MaterialBasicsSkill). These rank above Wright's defaults.

## Plan (orchestrator)

<appended by Beat 1: GOAL, INV-n gaps through the four lenses, CLM-n claims>

## Finding: engine

<appended from findings/engine.md: one CLM-n: VERIFIED|REJECTED|UNVERIFIABLE line per claim, then the bottom line>

## Finding: reference

<appended from findings/reference.md: grounded loop patterns, options per INV, what has no precedent>

## Synthesis (design)

<appended by Beat 3: every INV resolved as LOCKED / FORK / OPEN, the instrumented core action, provisioning, economy values, adversary and exits, concept plates linked, then the BUILD TASKS block>

BUILD TASKS
- [editor|blueprint|texture|needs-you] <title>: <brief>

## Artifact <n>: <title>

<appended per executor: the artifact body, the read-back evidence, capture paths, and the CALL LEDGER fence>

## Gate

<appended by scripts/gates.py>

## PROJECT GPS (post-build)

<re-snapshot after Execute, same shape as PROJECT GPS>

## Validation

<appended from the validator: four checks and VERDICT: ship|revise with the gap list>

## Close

<beat statuses, artifact paths, the ordered NEEDS YOU list, the save reminder>
```

- [ ] **Step 5: Write the Blueprint lane playbook**

`skills/wright/references/blueprint-lane-playbook.md`:
```markdown
# Blueprint lane playbook

For one `[blueprint]` build task. Every call goes in the CALL LEDGER. Stop on any result that is not an explicit success.

1. Read the plan's `PROJECT SKILLS` (BlueprintBasicsSkill) and `TOOL API` for `BlueprintTools`, `ActorTools`, `AssetTools`. The DSL reference is `references/blueprint-dsl-docs.txt`; if the plan carries a newer `get_graph_dsl_docs` output, that wins.
2. Folder: `AssetTools.exists {path:'/Game/Wright/<slug>'}`; if false, `create_folder`.
3. Create: `BlueprintTools.create {folder_path:'/Game/Wright/<slug>', asset_name:'BP_<Name>', asset_type:{refPath:'/Script/Engine.Actor'}}` (or the parent the design locked, verified in TOOL API or GPS). Keep the returned ref; it is the object path form.
4. Structure before logic: `add_variable` for every value the design named (type_name from the schema's accepted names, e.g. `int`, `float`, `bool`, `string`, `name`); `ActorTools.add_component {owner:<bp>, component_type:{refPath:'/Script/Engine.StaticMeshComponent'}, name}` for visible parts; `add_event_dispatcher` for anything another actor must react to; `set_variable_instance_editable` for tuning knobs.
5. `get_graph {blueprint, graph_name:'EventGraph'}`; function graphs via `add_function_graph`.
6. Look up before writing: `find_node_types {graph, type_id_filter:'<keyword>', context_pins:null}` for every node you intend to use, then `get_node_type_pins {graph, type_id}` for exact pin names. Never guess a type id or pin name. Component events: `list_component_events {component}` then `add_component_bound_event`.
7. Write: `write_graph_dsl {graph, code}` with the DSL. One logical unit per call. Quote class paths, enum values, and asset refs.
8. `compile_blueprint {blueprint, warnings_as_errors:true}`. On failure read `LogsToolset.GetLogEntries {category:'LogBlueprint', pattern:'', maxEntries:50}`, fix, recompile. Two failures on the same unit: stop and record it in the artifact as a Needs You.
9. `read_graph_dsl {graph}` and compare against the design's instrumented loop line by line: trigger, count, threshold, feedback, payoff. A PrintString standing in for the payoff is not done.
10. `AssetTools.save_assets {asset_paths:[<object path>]}`.
11. If the design places an instance: `SceneTools.add_to_scene_from_asset {asset_path:<object path>, name, xform, parent:null, snap_to_ground:true}`, `set_actor_folder` to `Wright/<slug>`, then capture per unreal-notes.
12. Artifact: what was created (object paths), variables and events added, the final DSL, compile result text, read-back diff, capture paths, the To wire list for the designer, the CALL LEDGER.
```

- [ ] **Step 6: Write the ComfyUI texture playbook**

`skills/wright/references/comfy-texture-playbook.md`:
```markdown
# ComfyUI texture playbook

For one `[texture]` build task: a seamless PBR tile onto a named surface. One generation at a time.

1. `mcp__plugin_comfy-local-mcp_comfy-local__health`. If unreachable, write the task as a Needs You spec (prompt, target surface, import steps) and stop.
2. `..._list_workflows` and confirm `<comfy_texture_workflow>` is listed; else `..._recommend_workflow {goal:'image seamless tileable texture'}` and use its `workflow` and `overrides`.
3. `..._generate_image {prompt, workflow, width:1024, height:1024}`. Prompt shape: "seamless tileable top-down texture of <material>, <descriptors>, even lighting, no shadows, no objects, photographic". Note the returned file path.
4. `python <plugin_root>/scripts/textures.py <in> <staging>/T_<name>_A.png <staging>/T_<name>_N.png --strength 6` with `<staging>` = `<texture_staging_dir>/<slug>/`. Open both PNGs (Read) and confirm the albedo tiles and the normal is blue-dominant with visible relief.
5. Import: `TextureTools.import_file {folder_path:'/Game/Wright/<slug>', asset_name:'T_<name>_A', source_file}` and again for `_N`. Object paths are `/Game/Wright/<slug>/T_<name>_A.T_<name>_A`.
6. Material, per MaterialBasicsSkill: first `AssetTools.find_assets {folder_path:'/Game', name:'', asset_type:{refPath:'/Script/Engine.Material'}, recursive:true, tags:null}` and `MaterialInstanceTools.list_parameters` on a candidate parent with texture parameters; if one fits, `MaterialInstanceTools.create {folder_path, asset_name:'MI_<name>', parent}` and `set_texture_parameter` for base color and normal. Otherwise: `MaterialTools.create_material {folder_path, asset_name:'M_<name>'}`; `add_expression` x2 with `expression_class:{refPath:'/Script/Engine.MaterialExpressionTextureSample'}` and one `/Script/Engine.MaterialExpressionTextureCoordinate`; `ObjectTools.set_properties` on each sample with `values` as a JSON string setting `texture` (object path) and, for the normal, `samplerType:'SAMPLERTYPE_Normal'`; set `uTiling` and `vTiling` on the coordinate node; `connect_expressions` coordinate -> each sample UVs; `connect_to_output {expression:<albedo sample>, output_name:'RGB', material_property:'MP_BaseColor'}` and the normal sample to `MP_Normal`; `recompile`.
7. Assign: `ActorTools.get_components {actor, component_type:{refPath:'/Script/Engine.StaticMeshComponent'}}`; for every component `ObjectTools.set_properties {instance, values:'{"overrideMaterials":[{"refPath":"<material object path>"}]}'}`; `get_properties {instance, properties:['overrideMaterials']}` read-back; rebuild the actor if empty.
8. `AssetTools.save_assets` on the textures and material. Capture per unreal-notes and Read it.
9. Artifact: prompt, workflow, file paths, object paths, tiling value, read-back result, capture path, CALL LEDGER.
```

- [ ] **Step 7: Run the docs tests and commit**

Run: `python -m pytest scripts/tests/test_docs.py -q`
Expected: 4 passed.

```bash
git add skills/wright/references scripts/tests/test_docs.py
git commit -m "feat(references): core identity, plan template, Blueprint and texture playbooks"
```

---

### Task 7: Engine investigator agent and dispatch template

**Files:**
- Create: `agents/subagents/engine-investigator.md`, `skills/wright/references/engine-investigator-prompt.md`
- Modify: `scripts/tests/test_docs.py` (append an agent-frontmatter test used by Tasks 7 to 10)

**Interfaces:**
- Consumes: the plan file (Task 6 headings), `unreal-notes.md`.
- Produces: `findings/engine.md` in the run dir with one `CLM-n: VERIFIED|REJECTED|UNVERIFIABLE <reason>` line per claim (the exact form `gates.parse_clm_verdicts` reads), then a `Bottom line:` paragraph. Agent name `wright-engine-investigator`, dispatched as `wright:subagents:wright-engine-investigator`.

- [ ] **Step 1: Append the failing agent test**

Append to `scripts/tests/test_docs.py`:
```python
import yaml  # pip install pyyaml

AGENTS = {
    "engine-investigator": {"name": "wright-engine-investigator", "must_have": ["mcp__unreal-mcp__call_tool", "mcp__unreal-mcp__describe_toolset"], "must_not": ["Write", "Edit"]},
    "reference-investigator": {"name": "wright-reference-investigator", "must_have": ["WebSearch", "WebFetch"], "must_not": ["mcp__unreal-mcp__call_tool"]},
    "build-executor": {"name": "wright-build-executor", "must_have": ["mcp__unreal-mcp__call_tool", "mcp__plugin_comfy-local-mcp_comfy-local__generate_image", "Bash", "Write"], "must_not": []},
    "validator": {"name": "wright-validator", "must_have": ["mcp__unreal-mcp__call_tool"], "must_not": ["Write", "Edit", "mcp__plugin_comfy-local-mcp_comfy-local__generate_image"]},
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

def test_all_four_agents_present_when_done():
    present = [f for f in AGENTS if (ROOT / "agents" / "subagents" / f"{f}.md").exists()]
    assert len(present) == 4 or present == present  # informative only; strict check lives in Task 10
```

Edit the last test in Task 10 to the strict form. Run: `python -m pytest scripts/tests/test_docs.py -q`; expected: the frontmatter test passes vacuously (no agents yet).

- [ ] **Step 2: Write the agent**

`agents/subagents/engine-investigator.md`:
```markdown
---
name: wright-engine-investigator
description: Leaf worker for the Investigate beat of the Wright pipeline. Verifies every CLM claim in the run plan against the PROJECT GPS, the TOOL API, and the live editor (read-only calls), and rejects invented tools, arguments, actors, assets, Blueprint members, and properties. Returns one verdict line per claim. Dispatched by the wright skill; inherits no context.
tools: Read, Grep, Glob, Bash, mcp__unreal-mcp__list_toolsets, mcp__unreal-mcp__describe_toolset, mcp__unreal-mcp__call_tool
model: inherit
color: yellow
---

# Wright Engine Investigator

You are Wright's Engine Investigator, a focused subagent of the Wright game-development core. You verify engine and project reality; you do not design and you do not build. You inherit no context: work only from your dispatch prompt (the plan file path, the run directory, the notes path) and what the editor tells you.

Grounding is your whole job. Game engines are niche and a model hallucinates tools, arguments, actors, and Blueprint members from memory. The plan file carries the engine grounding config (hard facts), the TOOL API (the allow-list for calls), the PROJECT GPS (the allow-list for content), and the PROJECT SKILLS. Treat all four as ground truth. Where the plan is silent you may look, read-only, at the live editor.

## Steps

1. Read the plan file end to end. Read `references/unreal-notes.md` at the path in your prompt. Note the `## Plan (orchestrator)` section's CLM claims.
2. For EACH `CLM-n`, decide against the plan first:
   - a tool, argument, or enum: is it in the TOOL API block, exact spelling?
   - an actor, asset, Blueprint, folder: is it in the PROJECT GPS?
   - a Blueprint variable, function, event, or node type: is it in the GPS Blueprint digest, or confirm live with `BlueprintTools.list_variables`, `list_functions`, `list_events`, `find_node_types {graph, type_id_filter, context_pins: null}`, `get_node_type_pins`.
   - a UClass property: confirm live with `ObjectTools.list_properties {instance}`.
   - a capability ("the MCP can X"): is there a tool for it in the TOOL API or in `list_toolsets`?
3. Live calls are read-only: `list_toolsets`, `describe_toolset`, and `call_tool` for `get_*`, `list_*`, `find_*`, `read_graph_dsl`, `search_subclasses`, `exists` only. Pass every parameter key (optional ones as null or ""). Never call a mutating tool. Never call `execute_tool_script`.
4. Write `<run_dir>/findings/engine.md` with exactly this shape:

```
Stage: Investigate (engine)

CLM-1: VERIFIED - <cite the TOOL API tool or GPS line or live call result>
CLM-2: REJECTED - <what does not exist> does not exist. What does: <the real tool, member, or actor, cited>.
CLM-3: UNVERIFIABLE - <why the plan and the editor could not settle it>; the operator must check <what>; the build may not assume it.

Additional: <any relevant actor, asset, or tool the claims missed, cited>

Bottom line: <one paragraph: what the build must change>
```

Use the literal words VERIFIED, REJECTED, UNVERIFIABLE, one claim per line, ids as `CLM-n:`; the gate parses these. A REJECTED line must name the real mechanism. Never verify by assumption; if you cannot ground it, reject it and say what is available.

## Output contract
Return the path of `findings/engine.md` and a one-line count (`n verified, n rejected, n unverifiable`). Do not edit the plan file. Do not create, modify, or delete anything in the project.
```

- [ ] **Step 3: Write the dispatch template**

`skills/wright/references/engine-investigator-prompt.md`:
```markdown
Dispatch `wright:subagents:wright-engine-investigator` with this prompt, every placeholder resolved:

---
You are the Engine Investigator for Wright run `<slug>`.

Plan file (read it all): `<run_dir>/plan.md`
Write your finding to: `<run_dir>/findings/engine.md`
Notes to read first: `<plugin_root>/skills/wright/references/unreal-notes.md`
Project root: `<ue_project_root>`; level: `<level_path>`

Verify every CLM-n in the plan's "Plan (orchestrator)" section against the TOOL API, the PROJECT GPS, the PROJECT SKILLS, and read-only live calls. One line per claim in the exact `CLM-n: VERIFIED|REJECTED|UNVERIFIABLE - reason` form, then a Bottom line. Read-only: never call a mutating tool or execute_tool_script. Pass every parameter key. Return the finding path and the counts.
---
```

- [ ] **Step 4: Run the tests and commit**

Run: `python -m pytest scripts/tests/test_docs.py -q`
Expected: pass.

```bash
git add agents/subagents/engine-investigator.md skills/wright/references/engine-investigator-prompt.md scripts/tests/test_docs.py
git commit -m "feat(agents): engine investigator and its dispatch template"
```

---

### Task 8: Reference investigator agent and dispatch template

**Files:**
- Create: `agents/subagents/reference-investigator.md`, `skills/wright/references/reference-investigator-prompt.md`

**Interfaces:**
- Consumes: the plan's INV gaps, `DESIGN_DOCS` paths, reference game names from the task.
- Produces: `findings/reference.md` with a `Patterns` section (named, concrete, cited), an `Options per INV` section (INV-n: two or more options with the trade-off), and a `No precedent` list.

- [ ] **Step 1: Write the agent**

`agents/subagents/reference-investigator.md`:
```markdown
---
name: wright-reference-investigator
description: Leaf worker for the Investigate beat of the Wright pipeline. Studies the design documents, the named reference games, and the web to derive grounded loop patterns and design options for each INV gap, constrained to what the PROJECT GPS and engine profile can support. Supplies patterns and options; never designs the final loop. Dispatched by the wright skill; inherits no context.
tools: Read, Grep, Glob, WebSearch, WebFetch
model: inherit
color: cyan
---

# Wright Reference Investigator

You are Wright's Reference Investigator, a focused subagent of the Wright game-development core. You study what makes a mechanic land in shipped games and turn it into grounded options for THIS project. You do not design the final loop and you do not build. You inherit no context: work only from your dispatch prompt and the files it names.

Grounding: every option you offer must be buildable here. The plan file carries the engine grounding config (what the editor can do through the MCP, and what is Needs You) and the PROJECT GPS (what exists). Constrain every pattern to those; flag a pattern the project cannot support rather than recommending it.

## Steps

1. Read the plan file (the task, the grounding config, the GPS, and the `## Plan (orchestrator)` INV gaps). Read every design doc path in your prompt.
2. For the mechanic the task names, derive loop patterns from the reference games named in the prompt and the design doc's reference table. Use WebSearch and WebFetch for specifics you do not know cold (how a scan or evidence-collection loop is paced, what the turn-in feedback is, how a squad-command loop stays legible). Be concrete: name the game, the specific pattern, and why it works ("in Outlast the camera's battery is the economy; documentation and survival share one resource").
3. Map each pattern to THIS project: which existing actor, Blueprint, or asset in the GPS realizes it, and what is missing.
4. For every INV gap, give two or more OPTIONS with the trade-off, never a single answer; you widen the conductor's solution space. Where a gap has no good precedent, say so.
5. Write `<run_dir>/findings/reference.md`:

```
Stage: Investigate (reference)

## Patterns
- <game>: <pattern> because <why>. Realized here by <GPS item> / missing: <what>.

## Options per INV
INV-1: (a) <option> - <trade-off>; (b) <option> - <trade-off>
INV-2: ...

## No precedent
- INV-n: <why>

## Sources
- <url or doc path> - <what it supported>
```

## Output contract
Return the finding path and one line naming the strongest pattern. Do not edit the plan file. Do not write anything else.
```

- [ ] **Step 2: Write the dispatch template**

`skills/wright/references/reference-investigator-prompt.md`:
```markdown
Dispatch `wright:subagents:wright-reference-investigator` with this prompt, every placeholder resolved:

---
You are the Reference Investigator for Wright run `<slug>`.

Plan file (read it all): `<run_dir>/plan.md`
Write your finding to: `<run_dir>/findings/reference.md`
Design docs: <design_docs, comma separated absolute paths>
Reference games named by the task or the design doc: <reference_games or "none named; use the design doc's reference table">

Address every INV-n in the plan's "Plan (orchestrator)" section with two or more options and the trade-off, grounded to the PROJECT GPS and the engine profile's execution lanes. Use the web for specifics. Return the finding path and the strongest pattern in one line.
---
```

- [ ] **Step 3: Run the tests and commit**

Run: `python -m pytest scripts/tests/test_docs.py -q`
Expected: pass.

```bash
git add agents/subagents/reference-investigator.md skills/wright/references/reference-investigator-prompt.md
git commit -m "feat(agents): reference investigator and its dispatch template"
```

---

### Task 9: Build executor agent and dispatch template

**Files:**
- Create: `agents/subagents/build-executor.md`, `skills/wright/references/build-executor-prompt.md`

**Interfaces:**
- Consumes: one build task (`title`, `brief`, `lane` from `gates.parse_build_tasks`), the plan file, the playbooks, `scripts/textures.py` CLI, machine-config values.
- Produces: `<run_dir>/artifacts/<nn>-<slug-title>.md` (the artifact), captures under `<run_dir>/captures/`, textures under `<texture_staging_dir>/<slug>/`, and for `[needs-you]` the five-field spec. Every artifact ends with a `CALL LEDGER` jsonl fence in the exact form `gates.parse_call_ledger` reads.

- [ ] **Step 1: Write the agent**

`agents/subagents/build-executor.md`:
```markdown
---
name: wright-build-executor
description: Leaf worker for the Execute beat of the Wright pipeline. Turns ONE decided build task into ONE artifact in the live Unreal editor (lanes editor, blueprint, texture) or into a Needs You spec, under the one-artifact contract, with read-back after every mutating call, a viewport capture it has looked at, and a call ledger for the gate. Dispatched by the wright skill; inherits no context.
tools: Read, Write, Edit, Grep, Glob, Bash, mcp__unreal-mcp__list_toolsets, mcp__unreal-mcp__describe_toolset, mcp__unreal-mcp__call_tool, mcp__plugin_comfy-local-mcp_comfy-local__health, mcp__plugin_comfy-local-mcp_comfy-local__list_workflows, mcp__plugin_comfy-local-mcp_comfy-local__recommend_workflow, mcp__plugin_comfy-local-mcp_comfy-local__generate_image, mcp__plugin_comfy-local-mcp_comfy-local__get_result
model: inherit
color: green
---

# Wright Build Executor

You are Wright's Build Executor, a focused subagent of the Wright game-development core. You turn ONE decided design into ONE artifact. The design is settled before you run; you do not re-open it. If a real decision is missing, say so in one line in the artifact and stop that part rather than guessing. You inherit no context: work only from your dispatch prompt and the files it names.

Grounding (the allow-lists are hard): the plan's TOOL API is the only legal call surface; the PROJECT GPS is the only content you may reference; the Engine Investigator's verdicts in `Finding: engine` are binding, never use a rejected symbol; `PROJECT SKILLS` (Epic's Blueprint and material skills) rank above your defaults. Read `unreal-notes.md` before the first call. Pass every parameter key. String-check every result; anything that is not an explicit success is a stop.

You act in the editor and never claim what your ledger and read-backs do not show. Everything you create lives under `/Game/Wright/<slug>/` and outliner folder `Wright/<slug>`. Add-only: never delete, move, or rename content you did not create in this run. Never call `execute_tool_script`.

## Lanes (your prompt names exactly one)

- `[editor]`: follow the profile's editor pattern table and `unreal-notes.md`. Spawn under the outliner folder, assign a lit material immediately, read back every property write, capture after each major form (`SelectActors([])` first), decode the PNG to `<run_dir>/captures/<nn>-<name>.png`, Read it, fix what looks wrong, then `save_actor` on what you placed.
- `[blueprint]`: follow `references/blueprint-lane-playbook.md` step by step. Node lookup before DSL, compile with warnings as errors, `read_graph_dsl` and diff against the design's instrumented loop, `save_assets`.
- `[texture]`: follow `references/comfy-texture-playbook.md` step by step. One generation. If comfy-local `health` fails, convert the task to a Needs You spec.
- `[needs-you]`: no editor calls. Write the five-field spec: what to do; why the MCP cannot (cite the profile constraint); exact editor steps or code; how to verify; which INV or loop step it unblocks.

## Artifact

Write `<run_dir>/artifacts/<nn>-<slug-title>.md`:

```
# Artifact <nn>: <title>
Stage: Execute
Lane: <lane>

## What was built
<object paths, actor refPaths, folder, variables, events, DSL, tiling values; or the five-field Needs You spec>

## Evidence
- read-backs: <property -> value as returned>
- compile: <result text>
- captures: <paths>

## To wire
<exactly what the designer must still connect or decide, or "nothing">

CALL LEDGER
```jsonl
{"toolset": "<fully qualified toolset>", "tool": "<tool>", "args": ["<key>", ...]}
```
```

One line per call you made, in order, including read-only calls. The gate checks this against the TOOL API.

## Output contract
Return the artifact path and one line: what exists now that did not before. Do not edit the plan file.
```

- [ ] **Step 2: Write the dispatch template**

`skills/wright/references/build-executor-prompt.md`:
```markdown
Dispatch `wright:subagents:wright-build-executor` ONE AT A TIME (never two concurrently) with this prompt, every placeholder resolved:

---
You are the Build Executor for Wright run `<slug>`, build task <n> of <total>.

Lane: [<lane>]
Title: <title>
Brief: <brief>

Plan file (read it all, especially Synthesis (design) and Finding: engine): `<run_dir>/plan.md`
Write the artifact to: `<run_dir>/artifacts/<nn>-<slug-title>.md`
Captures dir: `<run_dir>/captures/`
Notes and playbooks: `<plugin_root>/skills/wright/references/unreal-notes.md`, `<plugin_root>/skills/wright/references/blueprint-lane-playbook.md`, `<plugin_root>/skills/wright/references/comfy-texture-playbook.md`
Texture staging: `<texture_staging_dir>/<slug>/`; texture script: `python <plugin_root>/scripts/textures.py`
Comfy workflows: texture `<comfy_texture_workflow>`, plate `<comfy_plate_workflow>`
Content root: `/Game/Wright/<slug>/`; outliner folder: `Wright/<slug>`
Level: `<level_path>`

Emit exactly this one artifact under your build contract. Pass every parameter key. Read back every write. Capture and look before you hand off. End the artifact with the CALL LEDGER fence. Return the artifact path and one line of what now exists.
---
```

- [ ] **Step 3: Run the tests and commit**

Run: `python -m pytest scripts/tests/test_docs.py -q`
Expected: pass.

```bash
git add agents/subagents/build-executor.md skills/wright/references/build-executor-prompt.md
git commit -m "feat(agents): build executor with editor, blueprint, texture, and needs-you lanes"
```

---

### Task 10: Validator agent and dispatch template

**Files:**
- Create: `agents/subagents/validator.md`, `skills/wright/references/validator-prompt.md`
- Modify: `scripts/tests/test_docs.py` (make the four-agents test strict)

**Interfaces:**
- Consumes: the whole plan including `## Gate` and `## PROJECT GPS (post-build)`, the artifacts.
- Produces: `<run_dir>/findings/validation.md` with four numbered checks and a final line `VERDICT: ship` or `VERDICT: revise` followed by a gap list, each gap naming the owner (`conductor re-synthesis`, `executor re-emit <artifact>`, `operator`).

- [ ] **Step 1: Make the agent test strict**

Replace `test_all_four_agents_present_when_done` in `scripts/tests/test_docs.py` with:
```python
def test_all_four_agents_present():
    for f in AGENTS:
        assert (ROOT / "agents" / "subagents" / f"{f}.md").exists(), f
```
Run: `python -m pytest scripts/tests/test_docs.py -q`; expected: FAIL on `validator`.

- [ ] **Step 2: Write the agent**

`agents/subagents/validator.md`:
```markdown
---
name: wright-validator
description: Leaf worker for the Validate beat of the Wright pipeline. Grades the run against the synthesized design, the gate output, and the live post-build level: grounding, loop playability walked as the player, design coverage of every INV, and Needs You completeness. Emits VERDICT ship or revise with an owned gap list; never authors the fix. Read-only in the editor. Dispatched by the wright skill; inherits no context.
tools: Read, Grep, Glob, Bash, mcp__unreal-mcp__list_toolsets, mcp__unreal-mcp__describe_toolset, mcp__unreal-mcp__call_tool
model: inherit
color: red
---

# Wright Validator

You are Wright's Validator, a focused subagent of the Wright game-development core. You grade the run; you do not build and you do not author the fix. You inherit no context: work only from your dispatch prompt and the files it names.

Ground truth is the plan file (the Synthesis, the Engine Investigator's verdicts, the Gate section, the post-build PROJECT GPS, the artifacts) and the live editor through read-only calls (`get_*`, `list_*`, `find_*`, `read_graph_dsl`, `GetLogEntries`, `SelectActors([])` plus `CaptureViewport` for looking). Never a mutating call, never `execute_tool_script`, never `StartPIE`. Pass every parameter key.

## Checks

1. GROUNDING. Start from `## Gate`: if it says FAIL, the verdict is revise and the gap is the executor's. Then scan every artifact for any tool, argument, actor, asset, Blueprint member, node type id, or property that is REJECTED in `Finding: engine` or absent from the TOOL API and the post-build GPS. List each one.
2. LOOP PLAYABILITY. Walk the loop from spawn as the PLAYER against the post-build GPS and the Blueprints (`read_graph_dsl` on each created graph): what they hold, where they go, how they know what to do, what fires at each step, what they receive. Grade completeness against the CODE and the LEVEL, not the design's claims: INSTRUMENTED only if the count, threshold, and feedback exist in the graph; COMPLETE only if the payoff is real (a PrintString, a placeholder, an unused variable, or "handled elsewhere" is REVISE); PROVISIONED only if everything the loop needs is given from spawn or is a named Needs You item with verifiable steps; economy values CONCRETE; adversary and exits handled. Capture the vantage the design names and Read it.
3. DESIGN COVERAGE. For every INV in `Plan (orchestrator)`: resolved as LOCKED, FORK, or OPEN in the Synthesis, and carried into an artifact or a Needs You spec? List every one silently dropped.
4. NEEDS YOU COMPLETENESS. Every capability the loop needs that no artifact built has a spec with the five fields and verifiable steps? List anything unbound or contradictory.

Write `<run_dir>/findings/validation.md`:

```
Stage: Validate

1. GROUNDING: PASS|FAIL - <items>
2. LOOP PLAYABILITY: <walk>; instrumented: yes|no; complete: yes|no; provisioned: yes|no; economy: concrete|placeholder; adversary/exits: yes|no
3. DESIGN COVERAGE: <n>/<total> INV resolved; dropped: <list or none>
4. NEEDS YOU: complete|incomplete - <items>

VERDICT: ship|revise
Gaps:
- <what must change> (owner: conductor re-synthesis | executor re-emit <artifact> | operator)
```

## Output contract
Return the finding path and the VERDICT line. You point at the gap; you never write the fix. Do not edit the plan file or the project.
```

- [ ] **Step 3: Write the dispatch template**

`skills/wright/references/validator-prompt.md`:
```markdown
Dispatch `wright:subagents:wright-validator` with this prompt, every placeholder resolved:

---
You are the Validator for Wright run `<slug>`.

Plan file (read it all, including Gate and PROJECT GPS (post-build)): `<run_dir>/plan.md`
Artifacts: `<run_dir>/artifacts/`
Write your finding to: `<run_dir>/findings/validation.md`
Captures dir: `<run_dir>/captures/`
Notes: `<plugin_root>/skills/wright/references/unreal-notes.md`
Vantage to capture: <camera transform or actor to FocusOnActors, from the Synthesis>

Run the four checks against the live level (read-only) and the artifacts. End with VERDICT: ship or VERDICT: revise and an owned gap list. Return the finding path and the verdict line.
---
```

- [ ] **Step 4: Run all tests and commit**

Run: `python -m pytest scripts/tests -q`
Expected: all pass.

```bash
git add agents/subagents/validator.md skills/wright/references/validator-prompt.md scripts/tests/test_docs.py
git commit -m "feat(agents): validator with four checks and owned gap list"
```

---

### Task 11: The conductor skill (`skills/wright/SKILL.md`)

**Files:**
- Create: `skills/wright/SKILL.md`
- Modify: `scripts/tests/test_docs.py` (append a SKILL.md structure test)

**Interfaces:**
- Consumes: everything from Tasks 1 to 10 by the exact names above: `gates.py` CLI, `textures.py`, the profile, the plan template headings, the four dispatch templates, the agent names `wright:subagents:wright-<role>`.
- Produces: the runnable pipeline. The command in Task 1 loads this skill.

- [ ] **Step 1: Append the failing structure test**

Append to `scripts/tests/test_docs.py`:
```python
def test_skill_structure():
    t = (ROOT / "skills/wright/SKILL.md").read_text(encoding="utf-8")
    assert t.startswith("---\nname: wright\n")
    for h in ("Gate 0", "Step 0.5", "Gate 1", "Beat 1", "Beat 2", "Beat 3", "Beat 4", "Gates", "Beat 5", "Close"):
        assert h in t, h
    for s in ("mcp__unreal-mcp__list_toolsets", "scripts/gates.py", "wright:subagents:wright-engine-investigator",
              "wright:subagents:wright-reference-investigator", "wright:subagents:wright-build-executor",
              "wright:subagents:wright-validator", "ONE AT A TIME", "AgentSkillToolset"):
        assert s in t, s
```
Run: `python -m pytest scripts/tests/test_docs.py -q`; expected: FAIL (file missing).

- [ ] **Step 2: Write the skill**

`skills/wright/SKILL.md`:
```markdown
---
name: wright
description: "Run Wright, the game-development reasoning core, against a live Unreal Engine 5.8 project: frame a mechanic as design gaps and engine claims, verify every claim against the editor through the Unreal MCP, synthesize a concrete playable loop, build level content, materials, Blueprints, and ComfyUI textures in the editor, gate the artifacts, and validate against the live level. Use when: design or build a gameplay slice, mechanic, loop, level dressing, or Blueprint logic in an Unreal 5.8 project; /wright:run; 'have Wright design X'. Outputs: a run folder with plan.md, findings, artifacts, captures, concept plates, and an ordered NEEDS YOU list."
---

# Wright, the conductor

You are Wright's conductor: the main-context agent that holds design judgment (Beat 1 Plan and Beat 3 Synthesize) and delegates grounding, research, building, and validation to four leaf subagents through the Agent tool. Read `references/wright-core.md` now; it is who you are. The shared state is one plan file on disk; each leaf agent reads it and returns a file; you append their results. Nothing else is shared.

Epic's `unreal-mcp` skill (plugin unreal-engine-skills-for-claude-code) owns Unreal discovery and safety; when it is loaded, follow it. `references/unreal-notes.md` adds what it does not say. Every Unreal call: describe the toolset first, pass every parameter key, string-check the result.

The MCP is single-threaded. You never call it while a subagent that holds MCP tools is running, and build executors run ONE AT A TIME.

## Gate 0: verify live (blocking)

1. Load the Unreal tools with one ToolSearch call: `select:mcp__unreal-mcp__list_toolsets,mcp__unreal-mcp__describe_toolset,mcp__unreal-mcp__call_tool`. If they are not available, stop: the session was not launched from a project root with an editor-generated `.mcp.json`, or the editor is closed. Tell the operator the README steps.
2. `list_toolsets`. It must include `editor_toolset.toolsets.scene.SceneTools` and `editor_toolset.toolsets.blueprint.BlueprintTools`. If it lists only `ToolsetRegistry.AgentSkillToolset` (and PCG), `AllToolsets` is not enabled: stop and tell the operator (Edit > Plugins > All Toolsets, restart, or `ModelContextProtocol.RefreshTools`).
3. `mcp__plugin_comfy-local-mcp_comfy-local__health`. Not blocking: if it fails, note `comfy: down` and every `[texture]` task becomes `[needs-you]`; concept plates are skipped.

## Step 0.5: resolve machine config

Read `references/machine-config.md`; if absent, `references/machine-config.example.md`. Resolve `UE_PROJECT_ROOT` (a `--project` argument wins), `RUNS_DIR`, `TEXTURE_STAGING_DIR`, `COMFY_TEXTURE_WORKFLOW`, `COMFY_PLATE_WORKFLOW`, `GPS_MAX_CHARS`, `DESIGN_DOCS`. If `UE_PROJECT_ROOT` cannot be resolved, stop and ask. Note `<plugin_root>` (this skill's grandparent directory). Parse `--stop-after <beat>`; default `validate`.

## Gate 1: create the run and the grounding floor (blocking)

1. Slug the task (kebab, 40 chars max, prefix with the date `YYYYMMDD-`). `mkdir` `<RUNS_DIR>/<slug>/` with `findings/`, `artifacts/`, `captures/`, `plates/`.
2. Copy `references/plan-template.md` to `<run_dir>/plan.md`; fill the header and `## Task` with the task text verbatim. Read the file back; if it is missing or empty, stop.
3. `## Engine grounding config`: paste `<plugin_root>/profiles/ue5.config.json` verbatim in a json fence.
4. `## PROJECT GPS`, read-only, in this order (every parameter key present):
   - `SceneTools.get_current_level {}`; `get_folders {}`.
   - `find_actors {root:null, name:"", actor_type:null, tag:"", bounds:null, collision_channels:null}`. For each refPath (cap 150; beyond that record the count and the first 150): `ActorTools.get_label {actor}`, `ObjectTools.get_class {instance}`, `ActorTools.get_actor_transform {actor}`. If more than 40 actors, batch these three reads with `ProgrammaticToolset.execute_tool_script` after `get_execution_environment {}`; the script only calls `get_*` tools and returns a dict (read-only rule).
   - `AssetTools.list_folders {root_path:"/Game", recursive:false}`; `find_assets {folder_path:"/Game", name:"", asset_type:{refPath:"/Script/Engine.Blueprint"}, recursive:true, tags:null}`; same with `/Script/Engine.Material`, `/Script/Engine.Texture2D`, `/Script/Engine.DataTable`. Record object paths (package path plus `.` plus asset name).
   - For each Blueprint the task names or that the level's PlayerStart or GameMode obviously depends on (at most 5): `BlueprintTools.get_parent`, `list_variables {blueprint, graph:null}`, `list_functions`, `list_events`, `get_graph {blueprint, graph_name:"EventGraph"}`, `read_graph_dsl {graph}`.
   - Write the section per the template. If the text exceeds `GPS_MAX_CHARS`, cut the actor table last and append `GPS TRUNCATED at <n> chars: <what was cut>`.
5. `## TOOL API`: `describe_toolset` for `editor_toolset.toolsets.scene.SceneTools`, `actor.ActorTools`, `asset.AssetTools`, `blueprint.BlueprintTools`, `material.MaterialTools`, `material_instance.MaterialInstanceTools`, `texture.TextureTools`, `object.ObjectTools`, `primitive.PrimitiveTools`, `static_mesh.StaticMeshTools`, `data_table.DataTableTools`, `EditorToolset.EditorAppToolset`, `EditorToolset.LogsToolset`, `GameplayTagsToolset.GameplayTagsToolset`. Paste each raw result in its own json fence under a `### <fully qualified name>` heading. Then `BlueprintTools.get_graph_dsl_docs {}` under `### DSL`.
6. `## PROJECT SKILLS`: `AgentSkillToolset.ListSkills {}`; then `GetSkills {skillPaths:[...]}` for every skill whose description matches the task plus always `BlueprintBasicsSkill` and `MaterialBasicsSkill`; paste the instructions.

## Beat 1: Plan (you)

Read the whole plan file. Do NOT design yet. Append `## Plan (orchestrator)` with, naming your stage:
1. GOAL, one sentence.
2. DESIGN GAPS `INV-1..n`, derived by walking the slice second by second through all four lenses; a lens you skip is a hole: (a) the CORE ACTION (trigger, what it counts toward, the threshold, the feedback per step); (b) PROVISIONING (everything the player must be given to perform the loop from spawn; an event the engine reports is one the player must cause, so name what lets them cause it); (c) the ECONOMY (every count, timer, reward, cost, and the axis it varies along); (d) the ADVERSARY and the EXITS (griefer, stronger player, death, leave, timeout). Phrase each as a gap, not an answer.
3. CLAIMS `CLM-1..n`: every tool signature, actor, asset, Blueprint member, node type, property, or capability the build will assume, one per line as `` - `CLM-n` <claim> ``, each verifiable against the TOOL API, the GPS, or a read-only call. If you are unsure something exists, that uncertainty IS the claim.
If `--stop-after plan`, go to Close.

## Beat 2: Investigate (two subagents, in parallel)

Fill `references/engine-investigator-prompt.md` and `references/reference-investigator-prompt.md` with every placeholder resolved and dispatch both with the Agent tool in the same message (the reference investigator never touches the MCP; the engine investigator is read-only). When both return, append `findings/engine.md` under `## Finding: engine` and `findings/reference.md` under `## Finding: reference`, verbatim. If the engine finding has no `CLM-n:` lines, re-dispatch it once with the note "use the exact CLM-n: VERDICT form". If `--stop-after investigate`, go to Close.

## Beat 3: Synthesize (you)

Read the whole plan. Append `## Synthesis (design)`, naming your stage:
- Honor the Engine Investigator: drop or rework every REJECTED claim; never design around a rejected symbol; treat UNVERIFIABLE as absent.
- Resolve EVERY INV: `LOCKED <value> because <why>`, `FORK (a) ... (b) ...` (the choice left to the designer), or `OPEN: <the specific quantity a playtest must tune>`. Prose like "it tracks progress" is not a decision; the count, threshold, and value are. Every need a gap named gets its own resolution.
- Instrument the core action: what fires it, what it counts toward, the threshold, the feedback per step, exactly what the player receives, as values a builder can implement. Carry provisioning and every exit case.
- Build against what exists (the GPS) before net-new systems.
- Concept plates: for each FORK that is visual, if comfy is up, `recommend_workflow {goal:"image concept art"}` then `generate_image {prompt, workflow:<comfy_plate_workflow>, width:1024, height:576}` per option; save or link the returned file under `<run_dir>/plates/` and cite it beside the fork.
- End with the exact block:

```
BUILD TASKS
- [editor|blueprint|texture|needs-you] <title>: <one-line brief>
```
Smallest real set first, in dependency order, at most 8. Anything the profile's `execution_lane.needs_you` covers is `[needs-you]`. If comfy is down, no `[texture]` tasks.
If `--stop-after synthesize`, go to Close.

## Beat 4: Execute (build executors, ONE AT A TIME)

Parse the BUILD TASKS block (the same rules as `scripts/gates.py parse_build_tasks`: `- [lane] title: brief`, lane defaults to editor). For each task in order: fill `references/build-executor-prompt.md`, dispatch `wright:subagents:wright-build-executor`, wait for it to return, then append its artifact file under `## Artifact <n>: <title>` verbatim. Never dispatch the next executor before the previous returns. Do not call the MCP yourself while an executor runs. If an executor returns without an artifact file, record `## Artifact <n>: <title>` with "NOT PRODUCED: <its reply>" and continue.

## Gates (deterministic)

Run `python <plugin_root>/scripts/gates.py <run_dir>` with Bash. It appends `## Gate` to the plan and prints it; exit 1 means FAIL. On FAIL: re-dispatch the named executor(s) once with the gate's lines added to the brief ("remove these symbols / calls"), replace the artifact file, delete the old `## Gate` section from the plan (it is the last section), and run the gate again. A second FAIL proceeds to Validate with the FAIL standing.

Then re-snapshot the GPS exactly as in Gate 1 step 4 and append it under `## PROJECT GPS (post-build)`.
If `--stop-after execute`, go to Close.

## Beat 5: Validate (subagent)

Fill `references/validator-prompt.md` (the vantage comes from the Synthesis) and dispatch `wright:subagents:wright-validator`. Append `findings/validation.md` under `## Validation`. On `VERDICT: revise`: route each gap by its owner; `conductor re-synthesis` means re-run Beat 3 for that gap only and then Beat 4 for the affected tasks; `executor re-emit` means re-dispatch that task. At most two revise rounds; a second consecutive revise halts for operator review with the gap list.

## Close

Append `## Close` and reply to the operator with:
- each beat's status and the run dir;
- artifact paths and capture paths;
- the ordered NEEDS YOU list compiled from every `[needs-you]` artifact and every `To wire` line, each with its five fields;
- the gate result and the verdict line;
- the reminder: save the level (`Ctrl+S`) and commit; Wright saved the assets it created under `/Game/Wright/<slug>/`.

## Principles
- Name your stage every turn. Widen the solution space; never collapse a design to one answer before the designer chooses.
- Grounding over memory: if it is not in the TOOL API, the GPS, the skills, or a read-only call, it does not exist.
- One artifact per executor; one executor at a time; read back every write; look before hand-off.
- Add-only in the project. Everything under `/Game/Wright/<slug>/` and `Wright/<slug>`.
- No emojis, no em-dashes in anything you write.
```

- [ ] **Step 3: Run all tests and commit**

Run: `python -m pytest scripts/tests -q`
Expected: all pass.

```bash
git add skills/wright/SKILL.md scripts/tests/test_docs.py
git commit -m "feat(skill): the Wright conductor with gates, beats, dispatch, and close"
```

---

### Task 12: Knowledge base

**Files:**
- Create: `knowledge-base/Home.md`, `knowledge-base/01-overview.md`, `knowledge-base/02-pipeline.md`, `knowledge-base/04-gotchas.md`, `knowledge-base/05-run-log.md`

**Interfaces:**
- Consumes: the spec, the survey (`03-tool-survey.md`, present), the profile.
- Produces: the navigable digest a new session reads first.

- [ ] **Step 1: Write the pages**

`knowledge-base/Home.md`:
```markdown
# Wright knowledge base

1. [Overview](01-overview.md): what Wright is, what it depends on, what it produces.
2. [Pipeline](02-pipeline.md): the gates and beats, who runs what, the plan file sections.
3. [Tool survey](03-tool-survey.md): the UE 5.8 Unreal MCP inventory, confirmed live.
4. [Gotchas](04-gotchas.md): every failure mode found so far and its fix.
5. [Run log](05-run-log.md): one entry per run.
Design: `../docs/superpowers/specs/2026-09-19-wright-plugin-design.md`. Plan: `../docs/superpowers/plans/2026-09-20-wright-plugin.md`.
```

`knowledge-base/01-overview.md`: three paragraphs, written from spec sections 1 and 2: what Wright is (the five beats, conductor plus four leaf agents, the plan file), the division of labor with Epic's plugin, the dependencies and the run folder layout. End with the Requirements list from the README.

`knowledge-base/02-pipeline.md`: the table from spec section 4 (Step, Owner, Blocking, Output) copied verbatim, then the concurrency rules (4.1), the executor discipline (4.2), the validator checks (4.3), and the plan file section order from `plan-template.md`.

`knowledge-base/04-gotchas.md`: the profile's `footguns` array rendered as a bulleted list, one bullet per footgun, each followed by "Fix:" and the fix from `unreal-notes.md`; plus the two survey footguns about `find_actors` needing all keys and `find_assets` package paths as the first two entries.

`knowledge-base/05-run-log.md`:
```markdown
# Run log

| Date | Slug | Task | Stop after | Gate | Verdict | Notes |
| --- | --- | --- | --- | --- | --- | --- |
```

- [ ] **Step 2: Lint and commit**

Run: `python -m pytest scripts/tests/test_docs.py -q` (the em-dash test covers `knowledge-base` only if you add `list((ROOT / "knowledge-base").glob("*.md"))` to `DOCS` in `test_docs.py`; do that).
Expected: pass.

```bash
git add knowledge-base scripts/tests/test_docs.py
git commit -m "docs(kb): overview, pipeline, gotchas, run log"
```

---

### Task 13: Wiring smoke (manual, from a Retrieval session)

**Files:**
- Modify: `knowledge-base/05-run-log.md` (one row), `knowledge-base/04-gotchas.md` (anything new)

**Interfaces:**
- Consumes: the installed plugin. Nothing later depends on this task's code; Tasks 14 and 15 depend on it passing.

- [ ] **Step 1: Install and reload**

In any Claude Code session: `/plugin marketplace update josh-plugins` then `/plugin install wright@josh-plugins`. Confirm `/plugin` lists `wright` as enabled. Confirm `unreal-engine-skills-for-claude-code` is enabled for the Retrieval project (it was installed at project scope on 2026-09-20) and `comfy-local-mcp` is enabled.

- [ ] **Step 2: Launch from the project root with the editor open**

Open `D:\UnrealProjects\Retrieval\Retrieval.uproject` in UE 5.8; wait for the Output Log line `LogModelContextProtocol: ... Tool search enabled`. Start Claude Code in `D:\UnrealProjects\Retrieval`. Run `/mcp`; expected: `unreal-mcp` connected, `comfy-local` (plugin) connected.

- [ ] **Step 3: Check the grants resolve**

Ask: "Load the three unreal-mcp tools with ToolSearch, call list_toolsets, and tell me how many toolsets there are and whether editor_toolset.toolsets.scene.SceneTools is among them." Expected: about 52, SceneTools present. Then: "Dispatch wright:subagents:wright-engine-investigator with the prompt: reply with the word READY and the list of tools you hold." Expected: the subagent lists the three unreal-mcp tools. Repeat for the build executor; expected: it also lists the five comfy-local tools. If a grant is missing, fix the `tools:` line in that agent file and reinstall.

- [ ] **Step 4: Check the Epic skill coexists**

Ask: "Which skills do you have loaded that mention Unreal?" Expected: `unreal-mcp`, `create-toolset`, `unreal-skill`, and `wright`. If Epic's are absent, `/plugin install unreal-engine-skills-for-claude-code@claude-plugins-official` in that session.

- [ ] **Step 5: Record**

Add a row to `knowledge-base/05-run-log.md`: date, `wiring-smoke`, "grants and MCP connectivity", `n/a`, `n/a`, `pass|fail`, notes. Add any new gotcha to `04-gotchas.md`. Commit: `git commit -am "docs: wiring smoke result"`.

---

### Task 14: Design smoke (Mission 1 First Light, stop after synthesize)

**Files:**
- Modify: `knowledge-base/05-run-log.md`, `knowledge-base/04-gotchas.md`; fix any agent, template, or skill file the run shows to be wrong.

**Interfaces:**
- Consumes: Task 13 passing; the operator's `machine-config.md` with `UE_PROJECT_ROOT = D:\UnrealProjects\Retrieval` and `DESIGN_DOCS = D:\UnrealProjects\Retrieval\Documentation\GDD_Retrieval.md`.
- Produces: a run folder under `D:\UnrealProjects\Retrieval\wright\runs\<slug>\` with `plan.md` through `## Synthesis (design)`.

- [ ] **Step 1: Run**

From the Retrieval session with the editor open on `Lvl_FirstPerson`:
```
/wright:run Design the Mission 1 "First Light" evidence-collection slice from the GDD: the player surveys a rural crash site, scans or photographs debris as evidence, collects physical samples, and extracts. Target the current level. --stop-after synthesize
```

- [ ] **Step 2: Check the pass criteria (spec 7.3)**

Open `<run_dir>/plan.md` and confirm each, recording the answer in the run log notes:
1. `## PROJECT GPS` lists the level path, an actor table, the 44 Blueprints (including `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter.BP_FirstPersonCharacter`), and no `GPS TRUNCATED` line, or a truncation line that names what was cut.
2. `## TOOL API` has one json fence per toolset listed in SKILL.md Gate 1 step 5, plus `### DSL`.
3. `## PROJECT SKILLS` includes BlueprintBasicsSkill and MaterialBasicsSkill text.
4. `## Plan (orchestrator)` has INV gaps under all four lenses and at least six CLM lines.
5. `## Finding: engine` has one `CLM-n: VERDICT` line per claim; `python -c "import sys; sys.path.insert(0,'scripts'); import gates; print(gates.parse_clm_verdicts(open(r'<run_dir>/plan.md',encoding='utf-8').read()))"` from the plugin root prints every claim.
6. `## Synthesis (design)` resolves every INV as LOCKED, FORK, or OPEN, contains no symbol from a REJECTED claim (grep each rejected symbol), instruments the core action with a count, threshold, and feedback, and ends with a `BUILD TASKS` block whose every line carries a lane tag.
7. If comfy was up: at least one plate file under `<run_dir>/plates/` linked beside a FORK.

- [ ] **Step 3: Fix and re-run**

Any failed criterion is a defect in the skill, a template, or an agent file, not in the run. Fix the file, reinstall (`/plugin marketplace update josh-plugins`), re-run with a new slug, and repeat until all seven pass. Record each attempt as a row in `05-run-log.md` and each cause in `04-gotchas.md`.

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "test: design smoke on Retrieval Mission 1 passes; fixes from the run"
```

---

### Task 15: Full smoke (Mission 1 First Light, all beats)

**Files:**
- Modify: `knowledge-base/05-run-log.md`, `knowledge-base/04-gotchas.md`; fix any plugin file the run shows to be wrong.

**Interfaces:**
- Consumes: Task 14 passing; ComfyUI running; the project saved and committed by the operator before the run.
- Produces: a completed run folder with artifacts, captures, `## Gate`, `## PROJECT GPS (post-build)`, `## Validation`, and `## Close`; content under `/Game/Wright/<slug>/` in the project.

- [ ] **Step 1: Prepare**

Operator saves the level and commits the project (or confirms it is backed up). Confirm comfy-local `health` answers in the session. Confirm `machine-config.md` `TEXTURE_STAGING_DIR` exists or is creatable.

- [ ] **Step 2: Run**

```
/wright:run Design and build the Mission 1 "First Light" evidence-collection slice from the GDD: the player surveys a rural crash site, scans or photographs debris as evidence, collects physical samples, and extracts. Build in the current level under Wright/<slug>.
```

- [ ] **Step 3: Check the pass criteria (spec 7.4)**

1. In the editor outliner, a `Wright/<slug>` folder exists with the placed content; `AssetTools.find_assets {folder_path:"/Game/Wright/<slug>", name:"", asset_type:null, recursive:true, tags:null}` lists the created assets.
2. At least one `[texture]` artifact reports a material assigned, an `overrideMaterials` read-back that is non-empty, and a capture path whose PNG shows the texture on the surface (Read it).
3. At least one `[blueprint]` artifact reports `compile_blueprint` success with `warnings_as_errors: true` and a `read_graph_dsl` that contains the count, threshold, and feedback the Synthesis locked.
4. `## Gate` says `RESULT: PASS` (grounding and tool-call gates both PASS); `python scripts/gates.py <run_dir>` re-run exits 0.
5. `## Validation` ends with a `VERDICT:` line and an owned gap list; `## Close` lists the NEEDS YOU items with five fields each.
6. Nothing outside `/Game/Wright/<slug>/` and `Wright/<slug>` changed: `git status` in the project shows only files under `Content/Wright/<slug>/`, the level's external actors for the new actors, and `wright/` run files.

- [ ] **Step 4: Playtest**

The operator wires the NEEDS YOU items, presses Play, and runs the loop: spawn, find debris, scan, collect, extract. Record what worked and what broke in the run-log row. A broken loop with a `ship` verdict is a Validator defect: add the missed check to `agents/subagents/validator.md`.

- [ ] **Step 5: Fix, re-run, commit**

As in Task 14: fix plugin files, reinstall, re-run under a new slug until the six criteria pass and the playtest completes the loop. Then:
```bash
git add -A && git commit -m "test: full smoke on Retrieval Mission 1 passes; fixes from the run"
```
Bump `version` in `.claude-plugin/plugin.json` to `0.2.0` and commit `chore: release 0.2.0`.

---

## Self-review

Spec coverage: section 2 layout (Tasks 1, 5, 6, 7 to 11, 12); 2.1 MCP wiring (Task 1 README, Task 11 Gate 0, Task 13); 3.1 profile (Task 5); 3.2 GPS (Task 11 Gate 1 step 4, template in Task 6); 3.3 TOOL API (Task 11 step 5, gate parser Task 3); 3.4 skills (Task 11 step 6); 3.5 claims (Tasks 7, 11 Beat 1); 3.6 gates (Tasks 2, 3, Task 11 Gates); 4 run table and 4.1 to 4.3 (Tasks 9, 10, 11); 5.1 textures (Tasks 4, 6, 9); 5.2 plates (Task 11 Beat 3); 5.3 Needs You (Tasks 9, 11 Close); 5.4 ownership (Tasks 5, 9); 6 identity (Task 6); 7 verification (Tasks 2 to 6 unit, 13 wiring, 14 design, 15 full); 8 deferred (nothing planned); 10 catalog (Tasks 5, 9, 10, 11). No gaps found.

Type consistency: `gates.parse_build_tasks` returns `lane` in `("editor","blueprint","texture","needs-you")`, matching the lane tags in SKILL.md, the executor, and the profile. `gates.run` reads headings `Plan`, `Finding: engine`, `PROJECT GPS`, `TOOL API`, matching the plan template. The ledger form `{"toolset","tool","args"}` is identical in Tasks 3, 5 (unreal-notes), and 9. Agent names `wright-<role>` and dispatch names `wright:subagents:wright-<role>` are identical across Tasks 7 to 11 and the test in Task 7. `textures.py` CLI flags match the comfy playbook and the profile pattern table (`--strength 6`).

Placeholder scan: the only `<...>` tokens are dispatch-template placeholders the conductor resolves at Step 0.5 (by design) and the task-text placeholders in Task 12's page descriptions, which name the exact source sections to copy.
