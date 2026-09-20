# Pipeline

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

## 4.1 Concurrency rules

- The MCP executes tool calls serially on the game thread, and Epic's guidance is to serialize anything that touches shared editor state. Wright treats the MCP as single-threaded: **build executors run one at a time**, in the order the BUILD TASKS block gives.
- The two investigators run in parallel: the reference investigator never touches the MCP, and the engine investigator issues read-only calls.
- The conductor never calls the MCP while a subagent that holds MCP tools is running.
- One `[texture]` generation at a time; one GPU serves ComfyUI. Texture generation may overlap with an executor's MCP work only when the conductor runs it between executors.

## 4.2 Executor discipline

`[editor]`: read back after every mutating call; capture the viewport after each major form and look at it; `SelectActors([])` before every capture; assign a lit material to blockout geometry immediately so captures show form. Never hand off an artifact you have not looked at.

`[blueprint]`: call `get_graph_dsl_docs` (from the plan's TOOL API) and `find_node_types` before writing any DSL; never guess a node type id or pin name; keep the Event Graph for events and use function graphs for reusable logic; `compile_blueprint(warnings_as_errors=True)` once per logical unit; `read_graph_dsl` back and diff against intent; `save_assets`. Prefer Epic's `blueprint_basics` skill rules where they differ.

`[texture]`: the recipe in section 5.1 of the design spec.

`[needs-you]`: the spec in section 5.3 of the design spec.

Every executor logs every `call_tool` to its ledger and checks each result: many tools return a status rather than raising, so anything that is not an explicit success is a stop.

## 4.3 Validator checks

1. Grounding: the Gate section plus a prose scan of artifacts for ungrounded symbols, node type ids, and properties.
2. Loop playability: walk the loop as the player from spawn against the post-build GPS, the Blueprint graphs read back through `read_graph_dsl`, and the artifacts. Completeness is graded against what exists in the level and the Blueprints, not the design's claims. A payoff stubbed with a PrintString is revise.
3. Design coverage: every INV resolved or explicitly OPEN; dropped ones listed.
4. Needs You completeness: every capability the loop needs that the MCP could not build has a spec with verifiable steps.

PIE: `StartPIE`/`StopPIE` exist. Whether the validator uses them in v1 is decided at the live survey; the default is no, because editor-only tools misbehave during PIE.

## Plan file section order

`skills/wright/references/plan-template.md` fixes two orderings: the sections the conductor writes once at Gate 1, always in this order, and the sections each beat appends afterward, each exactly once, the first time it runs.

Gate 1 sections (live headings, in file order):

1. `## Task`
2. `## Engine grounding config`
3. `## PROJECT GPS`
4. `## TOOL API`
5. `## PROJECT SKILLS`

Append order (never pre-create these headings; gates.py and later beats find a section by its first `## ` match, so a placeholder created early would shadow the real one appended later):

1. Plan (orchestrator): Appended by Beat 1: GOAL, INV-n gaps through the four lenses, CLM-n claims.
2. Finding: engine: Appended from `findings/engine.md`: one CLM-n VERIFIED, REJECTED, or UNVERIFIABLE line per claim, then the bottom line.
3. Finding: reference: Appended from `findings/reference.md`: grounded loop patterns, options per INV, what has no precedent.
4. Synthesis (design): Appended by Beat 3: every INV resolved as LOCKED, FORK, or OPEN, the instrumented core action, provisioning, economy values, adversary and exits, concept plates linked, then the BUILD TASKS block.
5. Artifact <n>: <title>: Appended per executor: the artifact body, the read-back evidence, capture paths, and the CALL LEDGER fence.
6. Gate: Appended by `scripts/gates.py`.
7. PROJECT GPS (post-build): Re-snapshot after Execute, same shape as PROJECT GPS.
8. Validation: Appended from the validator: four checks and VERDICT: ship or revise with the gap list.
9. Close: Beat statuses, artifact paths, the ordered NEEDS YOU list, the save reminder.
