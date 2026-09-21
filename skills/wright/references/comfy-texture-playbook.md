# ComfyUI texture playbook

Packet mode: use only when a visual outcome is requested or needed by the current
packet. Use the packet's relevant schemas/evidence instead of the legacy full plan.
Record generation/import results as packet evidence. Texture generation is not a
prerequisite for proving a gameplay interaction with an existing basic material.

For one `[texture]` build task: a seamless PBR tile onto a named surface. One generation at a time.

Use fully qualified toolset names from current discovery in call evidence; the short names below are prose shorthand. Legacy runs use the plan's TOOL API and CALL LEDGER.

1. Read MaterialBasicsSkill when available and current schemas for tools needed by this packet from `TextureTools`, `MaterialTools`, `MaterialInstanceTools`, `AssetTools`, `ActorTools`, `ObjectTools`, or `EditorAppToolset`. Build every argument object from those schemas; pass every key.
2. Discover comfy-local's actual `health` tool in this host. If unreachable, record a blocked result with a handoff (prompt, target surface, import steps) and stop; retain attempted calls in the evidence.
3. Discover `list_workflows` and confirm `<comfy_texture_workflow>` is listed; else call the available `recommend_workflow` for a seamless tile and use its returned workflow and overrides.
4. Call the discovered `generate_image` with the live schema, requested dimensions 1024 x 1024, workflow and prompt. Prompt shape: "seamless tileable top-down texture of <material>, <descriptors>, even lighting, no shadows, no objects, photographic". Note the returned file path; wait through the result tool if generation is asynchronous.
5. `python <plugin_root>/scripts/textures.py <in> <staging>/T_<name>_A.png <staging>/T_<name>_N.png --strength 6` with `<staging>` = `<texture_staging_dir>/<slug>/`. Open both PNGs (Read) and confirm the albedo tiles and the normal is blue-dominant with visible relief.
6. Import: `TextureTools.import_file {folder_path:'/Game/Wright/<slug>', asset_name:'T_<name>_A', source_file}` and again for `_N`. Object paths are `/Game/Wright/<slug>/T_<name>_A.T_<name>_A`.
7. Material, per MaterialBasicsSkill: first `AssetTools.find_assets {folder_path:'/Game', name:'', asset_type:{refPath:'/Script/Engine.Material'}, recursive:true, tags:null}` and `MaterialInstanceTools.list_parameters` on a candidate parent with texture parameters; if one fits, `MaterialInstanceTools.create {folder_path, asset_name:'MI_<name>', parent}` and `set_texture_parameter` for base color and normal. Otherwise: `MaterialTools.create_material {folder_path, asset_name:'M_<name>'}`; `add_expression` x2 with `expression_class:{refPath:'/Script/Engine.MaterialExpressionTextureSample'}` and one `/Script/Engine.MaterialExpressionTextureCoordinate`; `ObjectTools.set_properties` on each sample with `values` as a JSON string setting `texture` (object path) and, for the normal, `samplerType:'SAMPLERTYPE_Normal'`; set `uTiling` and `vTiling` on the coordinate node; `connect_expressions` coordinate -> each sample UVs; `connect_to_output {expression:<albedo sample>, output_name:'RGB', material_property:'MP_BaseColor'}` and the normal sample to `MP_Normal`; `recompile`.
8. Assign: `ActorTools.get_components {actor, component_type:{refPath:'/Script/Engine.StaticMeshComponent'}}`; for every component `ObjectTools.set_properties {instance, values:'{"overrideMaterials":[{"refPath":"<material object path>"}]}'}`; `get_properties {instance, properties:['overrideMaterials']}` read-back; rebuild the actor if empty.
9. `AssetTools.save_assets` on the textures and material. Capture per unreal-notes and Read it.
10. Artifact: prompt, workflow, file paths, object paths, tiling value, read-back result, capture path, CALL LEDGER.
