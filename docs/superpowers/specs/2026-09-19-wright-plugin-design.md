# Wright standalone plugin: design spec

Date: 2026-09-19 (revised 2026-09-20 after the static and live tool survey)
Status: approved in brainstorm; revised; live survey complete except the tool-name prefix; awaiting written-spec review
Scope: port Wright from the Valar/Hearth harness into a standalone Claude Code plugin, retargeted from UEFN/Verse to Unreal Engine 5.8 through Epic's official Unreal MCP, layered on Epic's `unreal-engine-skills-for-claude-code` plugin, with ComfyUI (comfy-local-mcp) as the texture and concept-plate lane.

## 1. Context and decisions

Wright is a game-development reasoning core: a five-beat orchestrator (Plan, Investigate, Synthesize, Execute, Validate) that holds design judgment and delegates grounding, research, building, and validation to focused workers. The Valar version (`D:\Tools\Valinor`) runs those beats as persona-subagents on local models, shares state through a plan file on disk, and grounds against UEFN through a custom UEFN MCP, a PROJECT GPS snapshot, and the Verse digest allow-list. Its history and rationale are in `tasks/projects/wright-orchestrator-overhaul-plan.md` and `wright-fennec-overhaul-handoff.md`.

Decisions taken in the brainstorm and the review:

| Decision | Choice | Why |
| --- | --- | --- |
| Engine target | UE 5.8 only | Epic's Unreal MCP is a UE 5.8 editor plugin; it does not run in UEFN. Aligns with the Dreamwave-UE5 end goal. UEFN profile archived, not ported. |
| Execute stance | Wright acts in the editor | The MCP has a write side. Executors place actors, author materials and Blueprints, import textures, set properties, and self-verify by viewport capture. What the MCP cannot do becomes an explicit "Needs You" handoff. |
| V1 vertical | A playable mechanic slice | Keeps Wright's design lenses in play. The smoke task is Mission 1 "First Light" from the Retrieval GDD: survey the crash site, scan evidence, collect samples, extract. |
| Asset lane | ComfyUI textures and concept plates; no Blender | Seamless PBR texture sets into Unreal materials, plus concept plates per visual fork at Synthesize. Meshes stay to primitives, existing Content, or a Needs You import request. |
| Runtime shape | Skill-as-conductor (the-archive pattern) | Main-context Claude runs SKILL.md and holds Plan and Synthesize; leaf subagents fan out via the Agent tool. Agent-team runtime is a later option, not v1. |
| Division of labor with Epic's plugin | Epic's plugin onboards the model to Unreal; Wright is the game-development method | Wright ships no Unreal MCP playbook, no `.mcp.json`, and no toolset-discovery instructions of its own. It requires Epic's plugin and the project `.mcp.json` the editor generates, and adds the design pipeline, grounding gates, and asset lane on top. |
| Dependencies | Claude Code, Epic's `unreal-engine-skills-for-claude-code` plugin, the project's Unreal MCP, comfy-local-mcp | No Valinor, Hearth, Valar, or Engram. |

## 2. Plugin layout

Repo: `D:\tools\claude-marketplace\wright`, its own git repository, plugin name `wright`.

```
wright/
  .claude-plugin/plugin.json        name, description, version
  README.md                         install Epic's plugin, enable ModelContextProtocol + AllToolsets, Auto Start, GenerateClientConfig, launch from project root, changing the port, first run
  commands/run.md                   /wright:run <task> [--stop-after <beat>] [--project <ue_project_root>]
  skills/wright/SKILL.md            the conductor: identity, gates, beats, dispatch, close
  skills/wright/references/
    wright-core.md                  the durable identity (ported; Valar mechanics removed)
    plan-template.md                the run plan file schema
    engine-investigator-prompt.md   dispatch templates, one per leaf agent
    reference-investigator-prompt.md
    build-executor-prompt.md
    validator-prompt.md
    unreal-notes.md                 verified gotchas Epic's skill does not cover (all keys required, package vs object paths, JSON-string values, MP_ prefix, read-back, sprites in captures, actor-count scaling)
    blueprint-lane-playbook.md      the DSL discipline: docs, node lookup, write, compile, read back
    blueprint-dsl-docs.txt          verbatim output of BlueprintTools.get_graph_dsl_docs (from the survey)
    programmatic-exec-env.txt       verbatim output of ProgrammaticToolset.get_execution_environment (from the survey)
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
  knowledge-base/                   overview, pipeline, grounding, tool survey, gotchas, run log
  docs/superpowers/specs/           this spec
```

Machine config fields: `UE_PROJECT_ROOT`, `RUNS_DIR` (default `<UE_PROJECT_ROOT>/wright/runs`), `TEXTURE_STAGING_DIR` (default `<UE_PROJECT_ROOT>/wright/textures`), `COMFY_TEXTURE_WORKFLOW`, `COMFY_PLATE_WORKFLOW`, `GPS_MAX_CHARS` (default 12000), `DESIGN_DOCS` (paths handed to the reference investigator; for Retrieval, `Documentation/GDD_Retrieval.md`). The conductor substitutes these into every dispatch prompt; agents never hardcode paths.

### 2.1 MCP wiring

Wright does not ship an MCP server entry. The connection is the project's `.mcp.json`, written by `ModelContextProtocol.GenerateClientConfig ClaudeCode` in the editor console, with Claude Code launched from the project root (or from the editor's Terminal panel, per Epic's doc). Retrieval already has this file pointing at `http://127.0.0.1:8000/mcp`.

Tool names therefore follow the project-server form: `mcp__unreal-mcp__list_toolsets`, `mcp__unreal-mcp__describe_toolset`, `mcp__unreal-mcp__call_tool`. Every Wright agent's `tools:` frontmatter grants those three plus the comfy-local tools it needs. Epic's optional `unreal-mcp-proxy` is out of scope for v1; the README notes it.

The README covers: install `unreal-engine-skills-for-claude-code@claude-plugins-official`; enable `ModelContextProtocol` and `AllToolsets` (with only the former enabled the server exposes no editor tools, which is exactly what the survey hit on Retrieval); Editor Preferences > General > Model Context Protocol > Auto Start Server; `GenerateClientConfig ClaudeCode`; changing the port on both sides; `RefreshTools` after enabling a toolset plugin.

ComfyUI is the existing `comfy-local-mcp` plugin. Agents list its tools by full name, as the-archive does: `mcp__plugin_comfy-local-mcp_comfy-local__generate_image`, `..._get_result`, `..._recommend_workflow`, `..._list_workflows`, `..._health`.

The Unreal MCP runs in tool-search mode. Every agent describes a toolset before calling any tool in it. Never assume a signature. Epic's `unreal-mcp` skill carries the discovery flow and safety rules; Wright's agents defer to it and add only what `unreal-notes.md` records.

## 3. Grounding floor

Four inputs, written into the plan once at Gate 1.

### 3.1 Engine profile `profiles/ue5.config.json`

Same schema as the UEFN profile: `engine`, `status`, `reference_corpus` (kind, rule), `execution_lane`, `constraints`, `footguns`, `pattern_table`. Content comes from the tool survey (`knowledge-base/03-tool-survey.md`) and the-archive's verified playbook.

- Constraints: primitives limited to cube, cylinder, sphere, cone; no level-creation tool (`load_level` opens existing levels only); no Fab or Bridge download automation; tool calls execute serially on the game thread; per-call latency grows with actor count (keep hero actors in the tens, represent mass as mesh plus texture); `execute_tool_script` is privileged and read-only for Wright.
- Footguns (all confirmed live on Retrieval unless marked the-archive): every parameter key must be present in a call, optional ones as explicit `null` or `""`, or the call is rejected; `find_assets` returns package paths while Blueprint and asset tools want object paths (`/Game/X/BP_Y.BP_Y`); every object reference is `{"refPath": ...}` in and out; a parameter or schema error returns as a plain string starting with `Function "` or `Parameter error:`, not an MCP error, so results must be string-checked; editor sprites (lights, player start, cameras) and the axis widget survive `bShowUI: false` in captures, reviewers ignore them; `values` in `ObjectTools.set_properties` is a JSON string (the-archive); material property enums need the `MP_` prefix (the-archive); an `xform` with `rotation` must give pitch, yaw, and roll (the-archive); `overrideMaterials` can silently no-op, so read back and rebuild the actor if it does not persist (the-archive); `add_*` primitives attach as secondary components, iterate all StaticMeshComponents (the-archive); `find_actors` returns only refPaths; competing directional lights (the-archive); Blueprint structural changes need `compile_blueprint` before they exist on the CDO; pure-node outputs are recomputed per wire; casting to a Blueprint creates a hard load dependency.
- Pattern table: spawn actor plus primitive; texture import plus material graph plus assign plus read-back; camera plus capture; property set plus read-back; Blueprint create plus variables plus DSL plus compile plus `read_graph_dsl`; data table create plus rows; batch identification by UAID; outliner folders.
- Execution lane: the MCP acts through Wright for level content, materials, textures, Blueprints, data tables, and gameplay tags. C++ edits, new plugins, external asset packs, and anything a toolset does not expose are Needs You.
- Allow-list rule: a tool, argument, enum value, node type id, or UClass property not present in the TOOL API block, `find_node_types`, or `ObjectTools` discovery does not exist.

### 3.2 PROJECT GPS (content allow-list)

Built by the conductor at Gate 1: `SceneTools.get_current_level`; `find_actors` plus `ActorTools.get_label`, `ObjectTools.get_class`, `ActorTools.get_actor_transform`, `SceneTools.get_folders` and `get_actors_in_folder`; `AssetTools.find_assets` under `/Game` for Blueprints, materials, textures, data tables; `BlueprintTools.list_variables`, `list_functions`, `list_events` on the Blueprints the task names. Where the count is large, the conductor batches the reads through `ProgrammaticToolset.execute_tool_script` after calling `get_execution_environment` (read-only script). Capped at `GPS_MAX_CHARS` with an explicit truncation notice. Re-snapshotted after Execute, before Validate.

### 3.3 TOOL API (code allow-list)

For every toolset the run will touch, the conductor calls `describe_toolset` and pastes the schemas into the plan under `TOOL API`. For the Blueprint lane it also pastes `get_graph_dsl_docs()` once. Executors and the Validator treat these as the only legal call surface.

### 3.4 Project Agent Skills

At Gate 1 the conductor calls `AgentSkillToolset.ListSkills` and `GetSkills` for the shipped and project skills (Epic ships `blueprint_basics`, `material_basics`, `default_outdoor_lighting`) and pastes them into the plan under `PROJECT SKILLS`. They rank above Wright's generic defaults, per Epic's contract.

### 3.5 Claims

A `CLM-n` is any of: a tool signature the build will call; an actor or asset the design assumes exists; a Blueprint class, variable, function, or node type; a UClass property; an engine capability. The Engine Investigator returns one line per claim: `VERIFIED` (cite the GPS, TOOL API, or skill line), `REJECTED` (does not exist; name what does), or `UNVERIFIABLE` (say what the operator must check; the build may not assume it).

### 3.6 Deterministic gates `scripts/gates.py`

Pure Python, no model, no network. Run by the conductor via Bash after Execute.

- Grounding gate: port of Valar's `grounding_gate`, `parse_clm_claims`, `parse_clm_verdicts`, `extract_symbols`, and `_norm`. A symbol named in a REJECTED claim and absent from the GPS is forbidden; any that reaches an artifact is a FAIL.
- Tool-call gate: every executor appends a call ledger (`toolset`, `tool`, argument keys) to its artifact. Each entry is checked against the TOOL API block: unknown toolset, unknown tool, or unknown argument key is a FAIL.
- Output: a `Gate` section appended to the plan with PASS, FAIL (itemized), or INCONCLUSIVE. FAIL blocks a ship verdict.

## 4. The run

Conductor: the main-context agent running `skills/wright/SKILL.md`. It holds Plan and Synthesize and never delegates them. Run dir: `<RUNS_DIR>/<slug>/` with `plan.md`, `findings/`, `artifacts/`, `plates/`, `captures/`.

| Step | Owner | Blocking | Output |
| --- | --- | --- | --- |
| Gate 0: verify live | conductor | yes | `list_toolsets` returns the EditorToolset toolsets, not only AgentSkillToolset (if so, tell the operator to enable `AllToolsets` and run `RefreshTools` or restart). comfy-local `health` checked; if down, texture tasks degrade to Needs You, run continues. |
| Gate 1: create run | conductor | yes | Resolve machine config (stop if `UE_PROJECT_ROOT` cannot be resolved); mkdir; copy plan template; read back; append engine profile, PROJECT GPS, TOOL API, PROJECT SKILLS. |
| Beat 1: Plan | conductor | | GOAL, INV gaps through the four lenses (core action, provisioning, economy, adversary and exits), CLM claims. |
| Beat 2: Investigate | engine-investigator and reference-investigator, in parallel | | `findings/engine.md` (per-CLM verdicts) and `findings/reference.md` (grounded loop patterns and options from the design docs, reference games, and web research). Conductor appends both. |
| Beat 3: Synthesize | conductor | | Every INV resolved to a LOCKED value, a PRESERVED fork, or an explicit OPEN; every rejection honored; concept plates generated per visual fork and linked; ends with `BUILD TASKS`, each tagged `[editor]`, `[blueprint]`, `[texture]`, or `[needs-you]`, in dependency order. |
| Beat 4: Execute | build-executors, one per task, sequential | | One artifact each, under the one-artifact contract, plus a call ledger. |
| Gates | conductor via `scripts/gates.py` | | `Gate` section. |
| GPS re-snapshot | conductor | | `PROJECT GPS (post-build)` section. |
| Beat 5: Validate | validator | | Four checks and `VERDICT: ship` or `VERDICT: revise` with a gap list naming who fixes it. |
| Close | conductor | | Summary per beat, artifact paths, the ordered NEEDS YOU list, and a reminder to save the project (`AssetTools.save_assets` was called per artifact; the operator saves the level). |

`--stop-after <beat>` returns at any boundary. A design-only run is `--stop-after synthesize`.

Revise loop: a revise verdict routes to Synthesize (design gap) or Execute (artifact gap), capped at two rounds; a second consecutive revise halts for operator review.

### 4.1 Concurrency rules

- The MCP executes tool calls serially on the game thread, and Epic's guidance is to serialize anything that touches shared editor state. Wright treats the MCP as single-threaded: **build executors run one at a time**, in the order the BUILD TASKS block gives.
- The two investigators run in parallel: the reference investigator never touches the MCP, and the engine investigator issues read-only calls.
- The conductor never calls the MCP while a subagent that holds MCP tools is running.
- One `[texture]` generation at a time; one GPU serves ComfyUI. Texture generation may overlap with an executor's MCP work only when the conductor runs it between executors.

### 4.2 Executor discipline

`[editor]`: read back after every mutating call; capture the viewport after each major form and look at it; `SelectActors([])` before every capture; assign a lit material to blockout geometry immediately so captures show form. Never hand off an artifact you have not looked at.

`[blueprint]`: call `get_graph_dsl_docs` (from the plan's TOOL API) and `find_node_types` before writing any DSL; never guess a node type id or pin name; keep the Event Graph for events and use function graphs for reusable logic; `compile_blueprint(warnings_as_errors=True)` once per logical unit; `read_graph_dsl` back and diff against intent; `save_assets`. Prefer Epic's `blueprint_basics` skill rules where they differ.

`[texture]`: the recipe in section 5.1.

`[needs-you]`: the spec in section 5.3.

Every executor logs every `call_tool` to its ledger and checks each result: many tools return a status rather than raising, so anything that is not an explicit success is a stop.

### 4.3 Validator checks

1. Grounding: the Gate section plus a prose scan of artifacts for ungrounded symbols, node type ids, and properties.
2. Loop playability: walk the loop as the player from spawn against the post-build GPS, the Blueprint graphs read back through `read_graph_dsl`, and the artifacts. Completeness is graded against what exists in the level and the Blueprints, not the design's claims. A payoff stubbed with a PrintString is revise.
3. Design coverage: every INV resolved or explicitly OPEN; dropped ones listed.
4. Needs You completeness: every capability the loop needs that the MCP could not build has a spec with verifiable steps.

PIE: `StartPIE`/`StopPIE` exist. Whether the validator uses them in v1 is decided at the live survey (item 10.4.5); the default is no, because editor-only tools misbehave during PIE.

## 5. Asset lane and Needs You

### 5.1 Texture sets (`[texture]`)

1. `recommend_workflow(goal="seamless tileable PBR texture ...")`, then `generate_image` with the returned workflow and overrides. Save to `<TEXTURE_STAGING_DIR>/<slug>/`.
2. `python scripts/make_seamless_normal.py <in> <out_albedo> <out_normal> --strength 6`.
3. `TextureTools.import_file` into `/Game/Wright/<slug>/T_<name>`; set `samplerType` for the normal.
4. Per Epic's material skill: reuse an existing parent material with texture parameters if one exists (`MaterialInstanceTools.create` plus `set_texture_parameter`); otherwise `MaterialTools.create_material`, TextureSample expressions, TexCoord tiling, `connect_to_output` to `MP_BaseColor` and `MP_Normal`, `recompile`.
5. Assign through `overrideMaterials` on every StaticMeshComponent of the target (or `StaticMeshTools.set_material` on an asset); read back; rebuild the actor if the override did not persist.
6. `save_assets`; capture and look.

### 5.2 Concept plates (Synthesize)

One plate per visual fork, `generate_image` with `COMFY_PLATE_WORKFLOW`, saved to `<run_dir>/plates/`, linked in the plan beside the fork. Plates never enter Unreal.

### 5.3 Needs You (`[needs-you]`)

One `artifacts/needs-you-<n>.md` per task with five fields: what to do; why the MCP cannot (cite the profile constraint); exact editor steps or code; how to verify; which INV or loop step it unblocks. The Close compiles them into one ordered NEEDS YOU list. With the Blueprint lane in place, the expected Needs You items for Retrieval are C++ changes to the FPS template classes, new input actions that need editor-side binding review, and any asset packs.

### 5.4 Ownership and safety

Everything Wright creates lives under `/Game/Wright/<slug>/` and in outliner folder `Wright/<slug>`. Wright is add-only: it never deletes or renames content it did not create in this run. Executors call `save_assets` on what they create; the conductor tells the operator to save the level and commit before and after a run, per Epic's safety rules. `execute_tool_script` is read-only in Wright.

## 6. Identity port

`wright-core.md` is copied into `skills/wright/references/` with the Valar-specific Architecture and memory sections replaced by a pointer to this spec. The lineage, stance, loop, grounding discipline, and distilled method carry over unchanged. Each leaf agent's prompt condenses the core plus its role; the Valar persona JSON system prompts are the source text.

The stance line changes in one place: "you never claim to have placed, wired, compiled, or shipped anything" becomes "you never claim to have done in the editor what your call ledger and read-backs do not show; what you cannot perform is handed to the designer as Needs You".

## 7. Verification

1. Unit: `pytest scripts/tests/test_gates.py` covering the claim and verdict parsers, the grounding gate, and the tool-call gate. No editor.
2. Wiring smoke: from `D:\UnrealProjects\Retrieval` with the editor open, `/mcp` shows `unreal-mcp` connected; `list_toolsets` returns the EditorToolset toolsets; the plugin's agents resolve their tool grants; comfy-local `health` answers.
3. Design smoke: `/wright:run --stop-after synthesize` on Retrieval with the Mission 1 "First Light" slice from `Documentation/GDD_Retrieval.md`. Pass: no rejected symbol appears in the Synthesis; every INV is locked, forked, or OPEN; every CLM verdict cites a GPS, TOOL API, or skill line.
4. Full smoke: same task, all beats. Pass: placed content exists under `Wright/<slug>`; at least one ComfyUI texture reaches a material and survives read-back and capture; at least one Blueprint compiles clean and reads back the intended logic; both gates PASS; the Validator issues a verdict; the NEEDS YOU list names whatever is left with verifiable steps. The operator playtests; the playtest is the terminal bar.

## 8. Deferred

Blender mesh-artist lane; the Dreamwave bridge (end goal: Wright, comfy-local-mcp, and Dreamwave as one package); the UEFN profile; persistent Wright memory; the HTML build console; the agent-team runtime; multi-run sampling for design-depth tuning; the external multi-lens producer eval; the UMG, Niagara, and GAS authoring lanes; a Wright-registered project Agent Skill; a Wright-authored toolset (for example a one-call GPS snapshot) via Epic's `create-toolset` skill; PIE-driven validation; Epic's `unreal-mcp-proxy`.

## 9. Open items

Resolved by the static and live survey (`knowledge-base/03-tool-survey.md`): asset discovery (`AssetTools.find_assets`); ActorTools getter names; class discovery (`ObjectTools.search_subclasses`, `list_properties`); deselect (`SelectActors([])`); the gameplay authoring boundary (Blueprints, data tables, tags, materials, widgets are authorable; C++ and level creation are not); fully qualified toolset names; schemas match the static inventory for all 17 catalog toolsets; DSL docs and execution-environment text saved to `references/`; `CaptureViewport` works with `captureTransform: null` after `SelectActors([])`; `read_graph_dsl` on the FPS character Blueprint reads back cleanly; 20 project Agent Skills are listed, including Epic's four EditorToolset skills and PCG's `Skill_InstantLevelOperations`.

Still open: the `mcp__unreal-mcp__*` prefix and coexistence with Epic's plugin, confirmed at the wiring smoke from a session launched in `D:\UnrealProjects\Retrieval`. PIE for the Validator stays off in v1.

## 10. Tool catalog

What each role may call. Toolset names are given in their short form; the fully qualified names come from `list_toolsets` and are what `call_tool` takes. The complete inventory is in `knowledge-base/03-tool-survey.md`.

### 10.1 Meta-tools (every role)

`list_toolsets`, `describe_toolset`, `call_tool`.

### 10.2 Unreal toolsets by role

Conductor (Gate 0, Gate 1, re-snapshot). Read-only.

| Toolset | Tools |
| --- | --- |
| `SceneTools` | `get_current_level`, `find_actors`, `get_folders`, `get_actors_in_folder` |
| `ActorTools` | `get_label`, `get_actor_transform`, `get_actor_bounds`, `get_components` |
| `ObjectTools` | `get_class`, `list_properties`, `get_properties`, `search_subclasses` |
| `AssetTools` | `find_assets`, `list_folders`, `get_asset_class` |
| `BlueprintTools` | `list_variables`, `list_functions`, `list_events`, `list_graphs`, `get_graph_dsl_docs`, `read_graph_dsl` |
| `ProgrammaticToolset` | `get_execution_environment`, `execute_tool_script` (read-only scripts) |
| `AgentSkillToolset` | `ListSkills`, `GetSkills` |

Engine investigator. Read-only: the conductor's set above minus `ProgrammaticToolset`, plus `EditorAppToolset.GetVisibleActors` and `BlueprintTools.find_node_types`, `get_node_type_pins` (to verify node-type claims).

Build executor, `[editor]` lane. Read and write; every mutating call is followed by a read-back and logged.

| Toolset | Tools |
| --- | --- |
| `SceneTools` | `add_to_scene_from_class`, `add_to_scene_from_asset`, `set_actor_folder`, `remove_from_scene` (own-run content only), `save_actor`, `trace_world` |
| `PrimitiveTools` | `add_cube`, `add_cylinder`, `add_sphere`, `add_cone` |
| `ActorTools` | `set_label`, `set_actor_transform`, `look_at`, `set_parent_component`, `add_tag`, `add_component`, `get_components`, `get_actor_bounds` |
| `StaticMeshTools` | `set_material`, `import_file` (staged files only) |
| `ObjectTools` | `set_properties`, `get_properties`, `list_properties` |
| `AssetTools` | `create_folder`, `exists`, `find_assets`, `save_assets` |
| `EditorAppToolset` | `SelectActors`, `SetCameraTransform`, `GetCameraTransform`, `CaptureViewport`, `FocusOnActors` |

Build executor, `[blueprint]` lane: the `[editor]` set plus

| Toolset | Tools |
| --- | --- |
| `BlueprintTools` | `create`, `get_graph`, `list_graphs`, `add_function_graph`, `add_event`, `add_function_param`, `add_variable`, `add_struct_variable`, `add_object_variable`, `set_variable_instance_editable`, `add_event_dispatcher`, `list_component_events`, `add_component_bound_event`, `find_node_types`, `find_node_categories`, `get_node_type_pins`, `get_graph_dsl_docs`, `write_graph_dsl`, `read_graph_dsl`, `arrange_nodes`, `compile_blueprint`, `get_default_object` |
| `DataTableTools` | `search_row_structs`, `create`, `get_schema`, `add_rows`, `set_rows`, `get_rows` |
| `GameplayTagsToolset` | `ListTags`, `AddTag`, `GetTagInfo` |

Build executor, `[texture]` lane: the comfy-local tools in 10.3 plus `TextureTools.import_file`, `get_size`; `MaterialTools.create_material`, `list_expression_classes`, `add_expression`, `get_expression_input_names`, `get_expression_output_names`, `connect_expressions`, `connect_to_output`, `get_expressions`, `recompile`; `MaterialInstanceTools.create`, `list_parameters`, `set_texture_parameter`, `set_scalar_parameter`; `ObjectTools.set_properties`, `get_properties`; `AssetTools.save_assets`; `EditorAppToolset` capture.

Validator. Read plus capture; never writes: the conductor's set, `BlueprintTools.read_graph_dsl`, `compile_blueprint` (verification only), `EditorAppToolset.SelectActors`, `SetCameraTransform`, `CaptureViewport`, `GetVisibleActors`, `IsPIERunning`, `LogsToolset.GetLogEntries` (compile and MCP errors).

Build executors in every lane may also call `LogsToolset.GetLogEntries(category, pattern, maxEntries)` to read the error behind a failed call.

### 10.3 comfy-local tools

| Tool | Role |
| --- | --- |
| `health` | conductor, Gate 0 |
| `recommend_workflow` | conductor (plates), executor (textures) |
| `list_workflows` | executor |
| `generate_image` | conductor (plates), executor (textures) |
| `get_result` | conductor, executor |

### 10.4 Live survey against Retrieval

Ran 2026-09-20 with `AllToolsets` enabled; results are in `knowledge-base/03-tool-survey.md` under "Live confirmation", raw schemas in `knowledge-base/survey-raw/`.

1. `list_toolsets`: done, fully qualified names recorded.
2. `describe_toolset` on every toolset in 10.2: done, all match the static inventory.
3. DSL docs and execution environment: saved to `references/`.
4. Capture after `SelectActors([])`: done, clean apart from editor sprites.
5. PIE for the Validator: off in v1.
6. Tool-name prefix and coexistence with Epic's plugin: pending, part of the wiring smoke (section 7.2).
