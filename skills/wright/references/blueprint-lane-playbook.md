# Blueprint lane playbook

Packet mode: apply only the steps needed for the packet's one outcome. Use its
bounded context, relevant schema cache and acceptance checks in place of the legacy
whole-plan TOOL API/PROJECT SKILLS sections. Compile, read back and save a logical
unit before beginning the next; one asset can span several packets. Evidence files
are attached to packet progress/results. CALL LEDGER below describes the legacy
report format; it does not require reconstructing the legacy global pipeline.

For one `[blueprint]` build task. Every call goes in the CALL LEDGER. Stop on any result that is not an explicit success.

Use fully qualified toolset names from current discovery in call evidence; the short names below are prose shorthand. Legacy runs use the plan's TOOL API and CALL LEDGER.

1. Read BlueprintBasicsSkill when available and the current schemas for tools needed by this packet from `BlueprintTools`, `ActorTools`, `AssetTools`, `SceneTools`, or `LogsToolset`. The DSL reference is `references/blueprint-dsl-docs.txt`; newer `get_graph_dsl_docs` evidence wins.
2. Folder: `AssetTools.exists {path:'/Game/Wright/<slug>'}`; if false, `create_folder`.
3. Create: `BlueprintTools.create {folder_path:'/Game/Wright/<slug>', asset_name:'BP_<Name>', asset_type:{refPath:'/Script/Engine.Actor'}}` (or the parent the design locked, verified in TOOL API or GPS). Keep the returned ref; it is the object path form.
4. Add only structure required by this packet: `add_variable` for its values (type_name from the schema's accepted names, e.g. `int`, `float`, `bool`, `string`, `name`); `ActorTools.add_component {owner:<bp>, component_type:{refPath:'/Script/Engine.StaticMeshComponent'}, name}` for required visible parts; `add_event_dispatcher` for required reactions; `set_variable_instance_editable` for required tuning knobs. Defer future-system scaffolding.
5. `get_graph {blueprint, graph_name:'EventGraph'}`; function graphs via `add_function_graph`.
6. Look up before writing: `find_node_types {graph, type_id_filter:'<keyword>', context_pins:null}` for every node you intend to use, then `get_node_type_pins {graph, type_id}` for exact pin names. Never guess a type id or pin name. Component events: `list_component_events {component}` then `add_component_bound_event`.
7. Write: `write_graph_dsl {graph, code}` with the DSL. One logical unit per call. Quote class paths, enum values, and asset refs.
8. `compile_blueprint {blueprint, warnings_as_errors:true}`. On failure read `LogsToolset.GetLogEntries {category:'LogBlueprint', pattern:'', maxEntries:50}`, fix, recompile. Two failures on the same unit without new evidence: stop and record a blocked result or paused progress with an exact handoff.
9. `read_graph_dsl {graph}` and compare against the design's instrumented loop line by line: trigger, count, threshold, feedback, payoff. A PrintString standing in for the payoff is not done.
10. `AssetTools.save_assets {asset_paths:[<object path>]}`.
11. If the design places an instance: `SceneTools.add_to_scene_from_asset {asset_path:<object path>, name, xform, parent:null, snap_to_ground:true}`, `set_actor_folder` to `Wright/<slug>`, then capture per unreal-notes.
12. Artifact: what was created (object paths), variables and events added, the final DSL, compile result text, read-back diff, capture paths, the To wire list for the designer, the CALL LEDGER.
