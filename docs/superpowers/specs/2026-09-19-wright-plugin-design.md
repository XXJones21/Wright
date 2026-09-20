# Wright standalone plugin: design spec

Date: 2026-09-19
Status: approved in brainstorm; awaiting written-spec review
Scope: port Wright from the Valar/Hearth harness into a standalone Claude Code plugin, retargeted from UEFN/Verse to Unreal Engine 5.8 through Epic's official Unreal MCP, with ComfyUI (comfy-local-mcp) as the texture and concept-plate lane.

## 1. Context and decisions

Wright is a game-development reasoning core: a five-beat orchestrator (Plan, Investigate, Synthesize, Execute, Validate) that holds design judgment and delegates grounding, research, building, and validation to focused workers. The Valar version (`D:\Tools\Valinor`) runs those beats as persona-subagents on local models, shares state through a plan file on disk, and grounds against UEFN through a custom UEFN MCP, a PROJECT GPS snapshot, and the Verse digest allow-list. Its history and rationale are in `tasks/projects/wright-orchestrator-overhaul-plan.md` and `wright-fennec-overhaul-handoff.md`.

Decisions taken in the brainstorm:

| Decision | Choice | Why |
| --- | --- | --- |
| Engine target | UE 5.8 only | Epic's Unreal MCP is a UE 5.8 editor plugin; it does not run in UEFN. Aligns with the Dreamwave-UE5 end goal. UEFN profile archived, not ported. |
| Execute stance | Wright acts in the editor | The MCP has a write side. Executors place actors, author materials, import textures, set properties, and self-verify by viewport capture. What the MCP cannot do becomes an explicit "Needs You" handoff. |
| V1 vertical | A playable mechanic slice | Keeps Wright's design lenses in play. Wright designs the loop, builds what the MCP can, and hands Blueprint or C++ logic to the operator as a spec. |
| Asset lane | ComfyUI textures and concept plates; no Blender | Seamless PBR texture sets into Unreal materials, plus concept plates per visual fork at Synthesize. Meshes stay to primitives, existing Content, or a Needs You import request. |
| Runtime shape | Skill-as-conductor (the-archive pattern) | Main-context Claude runs SKILL.md and holds Plan and Synthesize; four leaf subagents fan out via the Agent tool, in parallel where independent. Agent-team runtime is a later option, not v1. |
| Dependencies | Claude Code, the Unreal MCP, comfy-local-mcp | No Valinor, Hearth, Valar, or Engram. |

## 2. Plugin layout

Repo: `D:\tools\claude-marketplace\wright`, its own git repository, plugin name `wright`.

```
wright/
  .claude-plugin/plugin.json        name, description, version, userConfig (unreal_mcp_url)
  .mcp.json                         unreal-mcp: type http; url from user config, default http://127.0.0.1:8000/mcp
  commands/run.md                   /wright:run <task> [--stop-after <beat>] [--project <ue_project_root>]
  skills/wright/SKILL.md            the conductor: identity, gates, beats, dispatch, close
  skills/wright/references/
    wright-core.md                  the durable identity (ported; Valar mechanics removed)
    plan-template.md                the run plan file schema
    engine-investigator-prompt.md   dispatch templates, one per leaf agent
    reference-investigator-prompt.md
    build-executor-prompt.md
    validator-prompt.md
    unreal-mcp-playbook.md          the-archive's verified recipes and gotchas, trimmed and extended
    comfy-texture-playbook.md       the texture-set recipe end to end
    machine-config.example.md       per-machine fields (below)
  profiles/ue5.config.json          engine grounding profile
  agents/subagents/
    engine-investigator.md
    reference-investigator.md
    build-executor.md
    validator.md
  scripts/
    gates.py                        deterministic grounding gate and tool-call gate
    make_seamless_normal.py         ported from D:\UnrealProjects\TheArchive\Scripts
    height2normal.py                ported from the same place
    tests/test_gates.py
  knowledge-base/                   overview, pipeline, grounding, gotchas, run log
  docs/superpowers/specs/           this spec
```

Machine config fields: `UE_PROJECT_ROOT`, `RUNS_DIR` (default `<UE_PROJECT_ROOT>/wright/runs`), `TEXTURE_STAGING_DIR` (default `<UE_PROJECT_ROOT>/wright/textures`), `COMFY_TEXTURE_WORKFLOW`, `COMFY_PLATE_WORKFLOW`, `GPS_MAX_CHARS` (default 12000). The conductor substitutes these into every dispatch prompt; agents never hardcode paths.

### 2.1 MCP wiring

The Unreal MCP is a session MCP shipped by the plugin, not an HTTP client script. `.mcp.json`:

```json
{ "mcpServers": { "unreal-mcp": { "type": "http", "url": "${user_config.unreal_mcp_url}" } } }
```

with `plugin.json` declaring `userConfig.unreal_mcp_url` (string, default `http://127.0.0.1:8000/mcp`, Epic's default). TheArchive runs on 8050, so the operator sets this once.

Verification item (first implementation task): confirm user-config substitution applies to the `url` field. If it does not, ship a fixed `http://127.0.0.1:8000/mcp` and document the one editor setting (Editor Preferences > Model Context Protocol > Server Port = 8000).

Tool names, as observed in this session for plugin MCPs: `mcp__plugin_<plugin>_<server>__<tool>` with hyphens preserved, so `mcp__plugin_wright_unreal-mcp__list_toolsets`, `..._describe_toolset`, `..._call_tool`. Confirm at the wiring smoke and pin the exact strings in every agent's `tools:` frontmatter.

ComfyUI is the existing `comfy-local-mcp` plugin. Agents that need it list its tools by full name, as the-archive does: `mcp__plugin_comfy-local-mcp_comfy-local__generate_image`, `..._get_result`, `..._recommend_workflow`, `..._list_workflows`, `..._health`. Wright ships no ComfyUI code.

The Unreal MCP runs in tool-search mode: `list_toolsets`, `describe_toolset`, `call_tool`. Every agent describes a toolset before calling any tool in it. Never assume a signature.

## 3. Grounding floor

Three inputs, written into the plan once at Gate 1.

### 3.1 Engine profile `profiles/ue5.config.json`

Same schema as the UEFN profile: `engine`, `status`, `reference_corpus` (kind, rule), `execution_lane`, `constraints`, `footguns`, `pattern_table`. Content comes from the-archive's verified playbook.

- Constraints: primitives limited to cube, cylinder, sphere, cone; no level-creation tool; no Blueprint graph or C++ authoring; no console-command or arbitrary Python exec; no build-lighting or bake tool; Fab/Bridge downloads not automatable; per-call latency grows with actor count (keep hero actors in the tens, represent mass as mesh plus texture).
- Footguns: `values` in `ObjectTools.set_properties` is a JSON string; material property enums need the `MP_` prefix; an `xform` with `rotation` must give pitch, yaw, and roll; `overrideMaterials` can silently no-op (read back, rebuild the actor if it does not persist); `add_*` primitives attach as secondary components (iterate all StaticMeshComponents); `CaptureViewport` needs `captureTransform`, `annotations`, and `bShowUI`; selection gizmo and wireframe leak into captures (deselect first); `find_actors` returns only refPaths; competing directional lights; skydome needs two-sided unlit.
- Pattern table: spawn actor plus primitive; texture import plus material graph plus assign plus read-back; camera plus capture; property set plus read-back; batch identification by UAID; outliner folders.
- Execution lane: the MCP acts through Wright; Blueprint logic, C++, asset import from outside Content, and Fab downloads are Needs You.
- Allow-list rule: a tool, argument, enum value, or UClass property not present in the TOOL API block or ObjectTools discovery does not exist.

### 3.2 PROJECT GPS (content allow-list)

Built by the conductor at Gate 1 through MCP calls: current level; every actor's refPath, label, class, folder, and transform; asset discovery for `/Game` as far as the toolsets expose it (materials, textures, Blueprint classes). Capped at `GPS_MAX_CHARS` with an explicit truncation notice rather than a silent cut. Re-snapshotted after Execute, before Validate, so the Validator grades the live level.

### 3.3 TOOL API (code allow-list)

For every toolset the run will touch, the conductor calls `describe_toolset` and pastes the schemas into the plan under `TOOL API`. This replaces the Verse digest. Executors and the Validator treat it as the only legal call surface.

### 3.4 Claims

A `CLM-n` is any of: a tool signature the build will call; an actor or asset the design assumes exists; a UClass property; an engine capability. The Engine Investigator returns one line per claim: `VERIFIED` (cite the GPS or TOOL API line), `REJECTED` (does not exist; name what does), or `UNVERIFIABLE` (say what the operator must check; the build may not assume it).

### 3.5 Deterministic gates `scripts/gates.py`

Pure Python, no model, no network. Run by the conductor via Bash after Execute.

- Grounding gate: port of Valar's `grounding_gate`, `parse_clm_claims`, `parse_clm_verdicts`, `extract_symbols`, and `_norm`. A symbol named in a REJECTED claim and absent from the GPS is forbidden; any that reaches an artifact is a FAIL.
- Tool-call gate: every executor appends a call ledger (`toolset`, `tool`, argument keys) to its artifact. Each entry is checked against the TOOL API block: unknown toolset, unknown tool, or unknown argument key is a FAIL. This is the code allow-list enforced in code.
- Output: a `Gate` section appended to the plan with PASS, FAIL (itemized), or INCONCLUSIVE (claims parsed but no artifacts, or unparseable verdicts). FAIL blocks a ship verdict.

## 4. The run

Conductor: the main-context agent running `skills/wright/SKILL.md`. It holds Plan and Synthesize and never delegates them. Run dir: `<RUNS_DIR>/<slug>/` with `plan.md`, `findings/`, `artifacts/`, `plates/`, `captures/`.

| Step | Owner | Blocking | Output |
| --- | --- | --- | --- |
| Gate 0: verify live | conductor | yes | `list_toolsets` returns scene toolsets (not only AgentSkillToolset). comfy-local `health` checked; if down, texture tasks degrade to Needs You, run continues. |
| Gate 1: create run | conductor | yes | Resolve machine config (stop if `UE_PROJECT_ROOT` cannot be resolved); mkdir; copy plan template; read back; append engine profile, PROJECT GPS, TOOL API. |
| Beat 1: Plan | conductor | | GOAL, INV gaps through the four lenses (core action, provisioning, economy, adversary and exits), CLM claims. |
| Beat 2: Investigate | engine-investigator and reference-investigator, in parallel | | `findings/engine.md` (per-CLM verdicts) and `findings/reference.md` (grounded loop patterns and options). Conductor appends both. |
| Beat 3: Synthesize | conductor | | Every INV resolved to a LOCKED value, a PRESERVED fork, or an explicit OPEN; every rejection honored; concept plates generated per visual fork and linked; ends with `BUILD TASKS`, each tagged `[editor]`, `[texture]`, or `[needs-you]`. |
| Beat 4: Execute | build-executors, one per task | | One artifact each, under the one-artifact contract, plus a call ledger. |
| Gates | conductor via `scripts/gates.py` | | `Gate` section. |
| GPS re-snapshot | conductor | | `PROJECT GPS (post-build)` section. |
| Beat 5: Validate | validator | | Four checks and `VERDICT: ship` or `VERDICT: revise` with a gap list naming who fixes it. |
| Close | conductor | | Summary per beat, artifact paths, the ordered NEEDS YOU list. |

`--stop-after <beat>` returns at any boundary. A design-only run is `--stop-after synthesize`.

Revise loop: a revise verdict routes to Synthesize (design gap) or Execute (artifact gap), capped at two rounds; a second consecutive revise halts for operator review.

### 4.1 Parallelism rules

- The two investigators always run in parallel.
- Executors run in parallel only when their level targets are disjoint (different actors, assets, folders). The conductor decides per batch from the BUILD TASKS.
- At most one `[texture]` executor at a time; one GPU serves ComfyUI.
- MCP calls execute on the editor tick; parallel executors sharing an actor would race. Disjointness is the rule, not a suggestion.

### 4.2 Executor discipline (`[editor]`)

Lifted from the-archive: read back after every mutating call; capture the viewport after each major form and look at it; never hand off an artifact you have not looked at; deselect before capture; assign a lit material to blockout geometry immediately so captures show form. Log every `call_tool` to the ledger.

### 4.3 Validator checks

1. Grounding: the Gate section plus a prose scan of artifacts for ungrounded symbols.
2. Loop playability: walk the loop as the player from spawn against the post-build GPS and the artifacts. Completeness is graded against what exists in the level and the Needs You specs, not the design's claims. A stubbed payoff is revise.
3. Design coverage: every INV resolved or explicitly OPEN; dropped ones listed.
4. Needs You completeness: every capability the loop needs that the MCP could not build has a spec with verifiable steps.

## 5. Asset lane and Needs You

### 5.1 Texture sets (`[texture]`)

1. `recommend_workflow(goal="seamless tileable PBR texture ...")`, then `generate_image` with the returned workflow and overrides. Save to `<TEXTURE_STAGING_DIR>/<slug>/`.
2. `python scripts/make_seamless_normal.py <in> <out_albedo> <out_normal> --strength 6`: half-offset cross-fade for seamlessness, wrap-aware Sobel on a blurred luminance for the normal.
3. `TextureTools.import_file` into `/Game/Wright/<slug>/T_<name>`; set `samplerType` for the normal.
4. `MaterialTools.create_material`, TextureSample expressions, TexCoord tiling, `connect_to_output` to `MP_BaseColor` and `MP_Normal`, `recompile`.
5. Assign through `overrideMaterials` on every StaticMeshComponent of the target; `get_properties` read-back; rebuild the actor if the override did not persist.
6. Capture and look.

### 5.2 Concept plates (Synthesize)

One plate per visual fork, `generate_image` with `COMFY_PLATE_WORKFLOW`, saved to `<run_dir>/plates/`, linked in the plan beside the fork. Plates never enter Unreal.

### 5.3 Needs You (`[needs-you]`)

One `artifacts/needs-you-<n>.md` per task with five fields: what to do; why the MCP cannot (cite the profile constraint); exact editor steps or code; how to verify; which INV or loop step it unblocks. The Close compiles them into one ordered NEEDS YOU list. The HTML build console is deferred.

### 5.4 Ownership and safety

Everything Wright creates lives under `/Game/Wright/<slug>/` and in outliner folder `Wright/<slug>`. Wright is add-only: it never deletes or renames content it did not create in this run.

## 6. Identity port

`wright-core.md` is copied into `skills/wright/references/` with the Valar-specific Architecture and memory sections replaced by a pointer to this spec. The lineage, stance, loop, grounding discipline, and distilled method carry over unchanged. Each leaf agent's prompt condenses the core plus its role, as the Valar persona JSONs did; their system prompts are the source text for the agent markdown files.

The stance line changes in one place: "you never claim to have placed, wired, compiled, or shipped anything" becomes "you never claim to have done in the editor what your call ledger and read-backs do not show; Blueprint logic, C++, and imports you cannot perform are handed to the designer as Needs You".

## 7. Verification

1. Unit: `pytest scripts/tests/test_gates.py` covering the claim and verdict parsers, the grounding gate, and the tool-call gate. No editor.
2. Wiring smoke: plugin loads from the marketplace; `/mcp` shows unreal-mcp connected at the configured URL; `list_toolsets` and `describe_toolset` answer; comfy-local `health` answers; agent tool names resolve.
3. Design smoke: `/wright:run --stop-after synthesize` against TheArchive (`D:\UnrealProjects\TheArchive`, UE 5.8, MCP on 8050) with a pickup-to-turn-in bounty loop. Pass: no rejected symbol appears in the Synthesis; every INV is locked, forked, or OPEN; every CLM verdict cites a GPS or TOOL API line.
4. Full smoke: same task, all beats. Pass: placed content exists under `Wright/<slug>`; at least one ComfyUI texture reaches a material and survives read-back and capture; both gates PASS; the Validator issues a verdict; the NEEDS YOU list names the Blueprint logic with verifiable steps. The operator wires the Blueprint and playtests; the playtest is the terminal bar.

## 8. Deferred

Blender mesh-artist lane; the Dreamwave bridge (end goal: Wright, comfy-local-mcp, and Dreamwave as one package); the UEFN profile; persistent Wright memory (patterns that repeat are written into the profile's pattern table by hand); the HTML build console; the agent-team runtime; multi-run sampling for design-depth tuning; the external multi-lens producer eval (`wright-eval-lens`).

## 9. Open items to resolve during implementation

- Whether `${user_config.*}` substitutes into `.mcp.json` `url` (section 2.1).
- Exact plugin MCP tool-name strings (section 2.1).
- Which Unreal toolsets expose asset discovery for `/Game` (section 3.2); if none, the GPS lists actors only and the profile says so.
- Whether a viewport-capture mode exists that excludes gizmos by construction (the-archive gotcha).
