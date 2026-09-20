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
