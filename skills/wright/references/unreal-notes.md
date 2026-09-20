# Unreal notes for Wright agents

Epic's `unreal-mcp` skill (plugin `unreal-engine-skills-for-claude-code`) owns discovery (`list_toolsets`, `describe_toolset`, `call_tool`), the safety rules (save first, wait for compiles, check every result, mind PIE), and project Agent Skills. Read it first. This file holds only what that skill does not say, all confirmed live on UE 5.8.

## Calls
- Every parameter key must be present. Build each argument object from the describe schema; pass optional keys as `null` or `""`. `find_actors` needs all six keys; `CaptureViewport` all three.
- Object references are `{"refPath": "..."}` both ways. `find_assets` returns package paths; append `.` plus the asset name to get the object path Blueprint and asset tools need.
- Errors arrive as plain strings (`Function "...`, `Parameter error: ...`). String-check every result.
- `ObjectTools.set_properties` `values` is a JSON string. Material refPaths inside it use `Package.Object` form. Read back with `get_properties`; if `overrideMaterials` came back empty, rebuild the actor.
- Primitives attach as secondary components: iterate every StaticMeshComponent from `get_components`.
- `connect_to_output` needs `MP_`-prefixed properties. Rotation needs pitch, yaw, and roll together. Units cm, Z up.
- `GameplayTagsToolset.AddTag`'s docstring requires explicit operator permission before it is called; prefer `ActorTools.add_tag` for run-scoped tagging, and put any gameplay-tag creation in a Needs You spec.

## Captures
- `SelectActors([])` before every capture. `captureTransform: null` captures the current viewport; pass the `GetCameraTransform` result to be explicit. Editor sprites and the axis widget remain; ignore them when reviewing. Decode `returnValue.image.data` (base64 PNG) to `<run_dir>/captures/` and Read it.
- Assign a lit material to blockout geometry before capturing; null-material primitives render black.

## Blueprints
- `get_graph_dsl_docs` and `find_node_types` before writing DSL; node type ids are `Category|Title`; quote class paths, enums, and asset refs.
- `write_graph_dsl` compiles; read the result text for warnings. Compile with `warnings_as_errors: true` once per logical unit, then `read_graph_dsl` and compare to intent.
- Structural changes need a compile before they exist on the CDO.

## Sandbox
- `execute_tool_script` results are `_StrictDict`: `.get()` with a default raises `_StrictDict.get() does not support a default value`; index with `["returnValue"]` and check `in` first.

## Ledger
Every mutating and read call an executor makes goes into its artifact's `CALL LEDGER` fence, one json object per line, so the tool-call gate can check it:

```jsonl
{"toolset": "editor_toolset.toolsets.scene.SceneTools", "tool": "add_to_scene_from_class", "args": ["actor_type", "name", "xform", "parent", "snap_to_ground"]}
```

The ledger's toolset is the fully qualified name exactly as the `### ` heading in the plan's TOOL API gives it; the short names in the playbooks and profile are prose shorthand.
