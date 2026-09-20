# 3. Tool survey (UE 5.8 Unreal MCP)

Status: static inventory complete from engine plugin source (2026-09-20); live confirmation pending `AllToolsets` being enabled in the Retrieval project. Live inventory at the time of the survey exposed only `ToolsetRegistry.AgentSkillToolset`, `PCGToolset.PCGToolset`, and `PCGToolset.PCGSpatialToolset`.

Engine: `D:\Unreal Engine\UE_5.8`. Toolset plugins live under `Engine/Plugins/Experimental/Toolsets/`. Python toolsets are under each plugin's `Content/Python/<pkg>/toolsets/*.py`; C++ toolsets expose `UFUNCTION(meta = (AICallable))` statics.

## How the server behaves

- Server: `ModelContextProtocol` plugin, HTTP at `http://127.0.0.1:8000/mcp` by default. Tool-search mode exposes `list_toolsets`, `describe_toolset`, `call_tool`. Toolset names as `call_tool` takes them are fully qualified (`editor_toolset.toolsets.scene.SceneTools`, `EditorToolset.EditorAppToolset`).
- Tool invocations execute on the game thread serially. Epic's own doc says clients should not issue overlapping calls; Epic's Claude Code plugin says serialize anything that touches the same asset or editor state and parallelize only independent, overlap-safe work. Wright treats the MCP as single-threaded.
- Console: `ModelContextProtocol.StartServer [port]`, `StopServer`, `RefreshTools` (after enabling a toolset plugin), `GenerateClientConfig ClaudeCode|Cursor|VSCode|Gemini|Codex|All` (writes the project `.mcp.json`, merges on re-run).
- `AllToolsets` is an aggregator that enables 21 toolset plugins. With only `ModelContextProtocol` enabled the server runs but exposes no editor tools. `AllToolsets` pulls in: AIModuleToolset, AnimationAssistantToolset, AutomationTestToolset, ConfigSettingsToolset, ConversationToolset, DataRegistryToolset, DataflowAgent, EditorToolset, GameFeaturesToolset, GameplayTagsToolset, GASToolsets, MCPClientToolset, NiagaraToolsets, PCGToolset, PhysicsToolsets, PluginToolset, SemanticSearchToolset, SlateInspectorToolset, StateTreeToolset, UMGToolSet, WorldConditionsToolset.
- `Terminal` is a native Slate terminal emulator inside the editor. It adds no tools; it is where Claude Code can run inside the editor window.
- Epic ships a Claude Code plugin, `unreal-engine-skills-for-claude-code` (official marketplace, MIT), with skills `unreal-mcp` (discovery flow, safety rules, project Agent Skills), `create-toolset`, `unreal-skill`, and a SessionStart hook that flags a UE project. It ships no `.mcp.json`; the project one is the connection. Local clone: `D:\Tools\Github-repos\unreal-engine-skills-for-claude-code-plugin`.

## EditorToolset (Python, 15 toolsets) plus EditorAppToolset (C++)

### SceneTools (20)
`load_level`, `get_current_level`, `get_collision_channels`, `find_actors(root, name, actor_type, tag, bounds, collision_channels)`, `add_to_scene_from_class(actor_type, name, xform, parent, snap_to_ground)`, `add_to_scene_from_asset(asset_path, name, xform, parent, snap_to_ground)`, `remove_from_scene`, `get_folders`, `get_actors_in_folder(folder_path, recursive)`, `set_actor_folder`, `rename_folder`, `delete_folder`, `trace_world(start, end)`, `merge_actors`, `create_level_instance`, `edit_level_instance`, `commit_level_instance`, `can_edit`, `is_checked_out`, `save_actor`.
No level-creation tool (unchanged from the-archive).

### ActorTools (17)
`get_label`, `set_label`, `get_tags`, `has_tag`, `add_tag`, `remove_tag`, `get_actor_transform`, `set_actor_transform(actor, xform, worldspace)`, `look_at`, `get_root_component`, `get_component_actor`, `get_parent_component`, `set_parent_component`, `get_actor_bounds`, `get_components(actor, component_type)`, `add_component(owner, component_type, name)` (actor instance or Blueprint), `remove_component`.

### AssetTools (21)
`create_folder`, `list_folders(root_path, recursive)`, `exists`, `duplicate`, `move`, `delete`, `find_assets(folder_path, name, asset_type, recursive, tags)`, `get_asset_tags`, `get_asset_class`, `get_metadata_tags`, `update_metadata_tags`, `load_asset`, `save_assets`, `is_dirty`, `can_edit_asset`, `is_checked_out`, `get_referencers`, `get_dependencies`, `get_plugin_content_paths`, `read_file`, `write_file`.
Resolves the "asset discovery under /Game" open item.

### BlueprintTools (53)
Creation and structure: `create(folder_path, asset_name, asset_type)`, `compile_blueprint(blueprint, warnings_as_errors)`, `get_default_object`, `get_parent`, `set_parent`, `list_graphs`, `get_graph`, `list_functions`, `list_events`, `add_function_graph`, `remove_function_graph`, `add_event`, `add_function_param`, `add_struct_function_param`, `add_object_function_param`, `remove_function_param`, `add_event_dispatcher`, `list_event_dispatchers`.
Variables: `add_variable(blueprint, name, type_name, graph, container_type)`, `add_struct_variable`, `add_object_variable`, `list_variables`, `remove_variable`, `set_variable_instance_editable`, `get/set_variable_replication`, `get/set_variable_category`.
Nodes and pins: `find_node_types(graph, type_id_filter, context_pins)`, `find_node_categories`, `get_node_type_pins(graph, type_id)`, `create_node(graph, type_id, pos, declaring_class)`, `delete_node`, `find_nodes`, `get_node_infos`, `get_connected_subgraph`, `add_node_pin`, `remove_node_pin`, `retarget_node_class`, `set_node_position`, `arrange_nodes`, `connect_pins`, `break_pins`, `set_pin_value`, `get_pin_value`, `list_component_events`, `add_component_bound_event(component, event_name, graph)`, `get/set_create_event_function`, `list_compatible_event_functions`.
DSL: `get_graph_dsl_docs()`, `write_graph_dsl(graph, code)` (populates and compiles), `read_graph_dsl(graph)`. The DSL is an S-expression language: `(event Name ...)`, `(fn Name (params) ...)`, `bind`, `if/elif/else`, `for`, `while`, `switch`, multi-exec continuations `(:ExecOut ...)`, node calls by `Category|Title` type id. Class paths, enum names, and asset refs must be quoted.
Consequence: Blueprint logic is authorable through the MCP. It is a Wright build lane, not a Needs You item.

### MaterialTools (22), MaterialInstanceTools (13), TextureTools (2)
Materials: `create_material`, `create_function`, `create_parameter_collection`, `list_expression_classes`, `add_expression(material_or_function, expression_class, x, y)`, `delete_expression`, `get_expressions`, `layout_expressions`, `get_expression_input_names`, `get_expression_output_names`, `connect_expressions`, `disconnect_expressions`, `get_expression_inputs`, `get_property_input`, `connect_to_output(expression, output_name, material_property)`, `disconnect_from_output`, `delete_unused_expressions`, `recompile`, `get_referencing_materials`, parameter-group tools.
Instances: `create(folder_path, asset_name, parent)`, `list_parameters`, get/set scalar, vector, texture, static-switch parameters, `set_parent`, `clear_parameters`, `set_parameter_override`.
Textures: `import_file(folder_path, asset_name, source_file)`, `get_size`.
Epic's shipped `material_basics` skill says: reuse an existing Material or MaterialInstance first, create an instance from a parent second, author a new Material last, and expose parameters for per-instance variation.

### ObjectTools (6)
`search_subclasses(base_class, class_name)`, `get_class(instance)`, `list_properties(instance)`, `get_properties(instance, properties)`, `set_properties(instance, values)`, `reset_properties`.
Resolves the "class discovery" open item.

### PrimitiveTools (4)
`add_cube(actor, name, dimensions, local_transform)`, `add_sphere`, `add_cylinder`, `add_cone`. Still the only primitives.

### StaticMeshTools (16), SkeletalMeshTools (22)
Static: `import_file`, LOD and vertex queries, `get_material_slots`, `get_material`, `set_material(mesh, slot_name, material)`, LOD thresholds, `generate_lods`, `generate_convex_collisions`, `remove_collisions`, `is/set_nanite_enabled`.
Skeletal: import, bones, sockets, material slots, physics asset.

### DataTableTools (10), CurveTableTools (9), StringTableTools (8), DataAssetTools (1)
Data tables: `search_row_structs`, `import_file`, `create(folder_path, asset_name, schema)`, `get_schema`, `list_rows`, `add_rows`, `remove_rows`, `rename_rows`, `get_rows`, `set_rows`. Relevant to Wright's economy lens: tuning values can live in a DataTable the executor authors.

### ProgrammaticToolset (2)
`get_execution_environment()` (must be called first; returns the sandbox instructions), `execute_tool_script(script)`: a Python script defining `run() -> dict`, allowed imports `json`, `math`, `datetime`, `copy`, `re`, `time`, calling toolset APIs in batch. Epic's README classes this as arbitrary privileged execution. Wright uses it only for read-only batch queries (GPS snapshot) in v1; never for mutation.

### EditorAppToolset (C++)
`SearchCVars`, `CaptureAssetImage(asset_path)`, `CaptureEditorImage()`, `CaptureViewport(CaptureTransform?, Annotations?, bShowUI=false)`, `GetSelectedActors`, `SelectActors(actors)` (pass an empty list to deselect before capture), `GetCameraTransform`, `SetCameraTransform`, `FocusOnActors`, `GetVisibleActors`, `WorldPosToScreenCoords`, `ScreenCoordsToWorld`, `GetSelectedAssets`, `SelectAssets`, `GetContentBrowserPath`, `SetContentBrowserPath`, `OpenEditorForAsset`, `GetOpenAssets`, `StartPIE(options)`, `StopPIE`, `IsPIERunning`.
Resolves the "deselect-all" open item: `SelectActors([])`. Gizmo-free capture mode: not found in source; deselect first remains the rule.

### AgentSkillToolset (ToolsetRegistry)
`ListSkills`, `GetSkills(skillPaths)`, `CreateSkill`, `UpdateSkill`. Epic ships `blueprint_basics`, `material_basics`, `default_outdoor_lighting`, `unreal_skill_best_practices`. Wright reads the shipped skills at Gate 1 and folds them into the grounding floor. Wright may later register its own project skill (deferred).

## Gameplay-side toolsets (under AllToolsets)

| Toolset | Surface | Wright use |
| --- | --- | --- |
| GASToolsets (C++) | `FindAttributeSetClasses`, `ListAttributes`, `GetAttributeValues`, `GetActiveEffects`, `GetGrantedAbilities`, `GetActiveTags`; GameplayCues `ListCues`, `GetCueInfo`, `CreateCueNotifyAsset`, `AddCueTag`, `RemoveCueTag`, `ExecuteCueOnSelectedActor` | read-only inspection; cue tags authorable. Retrieval does not enable GameplayAbilities. |
| GameplayTagsToolset (C++) | `ListTags`, `GetTagInfo`, `AddTag`, `RemoveTag`, `RenameTag`, `FindReferencersByTag` | authorable; useful for mission and evidence state tags |
| StateTreeToolset (Python, 9) | `get_editor_data`, `get_root_states`, `get_children`, `get_tasks`, `get_enter_conditions`, `get_transitions`, `get_global_tasks`, `get_evaluators`, `get_node_description` | read-only inspection. Retrieval enables StateTree and GameplayStateTree. |
| AIModuleToolset (Python, 7) | Behavior tree inspection: `get_blackboard`, `list_nodes`, `get_children`, `get_subtree` | read-only |
| UMGToolSet (C++, 25) | `CreateWidgetBlueprint`, `AddWidget`, `GetWidgets`, `MoveWidget`, `RemoveWidget`, `BindToEventProperty`, `CompileWidgetBlueprint`, and more | authorable HUD and prompts; deferred from v1 |
| NiagaraToolsets (C++, 56) | create systems, add emitters, modules, renderers, parameters | authorable; deferred |
| PhysicsToolsets (C++, 17) | physics asset bodies and constraints | deferred |
| LiveCodingToolset (C++, 1) | `CompileLiveCoding` (blocks until done, returns MSVC diagnostics) | the C++ lane's compile step; new UFUNCTIONs still need an editor restart |
| AutomationTestToolset (C++, 7) | `DiscoverTests`, `RunTests`, `RunTestsByFilter`, `GetTestResults` | Validator candidate for C++ projects; deferred |
| SlateInspectorToolset (C++, 14) | `Click`, `Type`, `Screenshot`, `Snapshot`, `FillForm` on editor UI | not used |
| DataRegistryToolset, ConfigSettingsToolset, GameFeaturesToolset, PluginToolset, DataflowAgent, SemanticSearchToolset, WorldConditionsToolset, ConversationToolset, AnimationAssistantToolset, MCPClientToolset | various | not used in v1 |

## Resolved open items

| Item | Answer |
| --- | --- |
| Asset discovery under `/Game` | `AssetTools.find_assets`, `list_folders`, `get_asset_class` |
| ActorTools getters | `get_label`, `get_actor_transform`, `get_components`, `get_actor_bounds`; class via `ObjectTools.get_class`; folder via `SceneTools.get_folders` and `get_actors_in_folder` |
| Class discovery | `ObjectTools.search_subclasses`, `list_properties` |
| Deselect before capture | `EditorAppToolset.SelectActors([])` |
| Gizmo-free capture mode | none found in source; deselect first |
| Gameplay authoring boundary | Blueprint graphs, variables, components, events, dispatchers, data tables, gameplay tags, materials, and widgets are authorable. C++ is file edits plus `CompileLiveCoding`. Level creation is not exposed. |
| Blueprint-adjacent toolsets | `BlueprintTools` in EditorToolset, including the DSL |

## Still to confirm live (after AllToolsets is enabled)

1. `list_toolsets` shows the EditorToolset toolsets and the fully qualified names.
2. `describe_toolset` schemas match the static inventory (argument names, enums, `xform` shape).
3. `get_graph_dsl_docs()` full text, saved for the Blueprint lane playbook.
4. `get_execution_environment()` text, saved for the GPS batch script.
5. Whether `CaptureViewport` with no `CaptureTransform` captures the current viewport, and whether `SelectActors([])` clears the selection outline.
6. The tool-name prefix Claude Code assigns when the server comes from the project `.mcp.json` (expected `mcp__unreal-mcp__<tool>`).
