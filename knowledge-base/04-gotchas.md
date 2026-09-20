# Gotchas

Every entry below is a footgun from `profiles/ue5.config.json`, in the order the profile lists them except that the two most common ones (missing keys, package versus object paths) are promoted to the front. Each Fix line is drawn from `skills/wright/references/unreal-notes.md` unless noted.

- Every parameter key in the describe schema must be present in the call, optional ones as explicit null or an empty string; a missing key is rejected with "input param ... is required". Build argument objects from the schema, never from memory.
  Fix: build each argument object from the describe schema; pass optional keys as null or an empty string. `find_actors` needs all six keys; `CaptureViewport` all three.

- `AssetTools.find_assets` returns package paths (`/Game/X/BP_Y`); Blueprint and asset tools need the object path (`/Game/X/BP_Y.BP_Y`). Append "." plus the asset name before passing it on.
  Fix: `find_assets` returns package paths; append "." plus the asset name to get the object path Blueprint and asset tools need.

- Object references are `{"refPath": "..."}` in and out. Actor refPaths look like `/Game/<Level>.<Level>:PersistentLevel.<ActorName>`; graph refPaths like `/Game/.../BP_X.BP_X:EventGraph`.
  Fix: object references are `{"refPath": "..."}` both ways.

- A parameter or schema error returns as a plain string starting with `Function "` or `Parameter error:`, not an MCP error, so results must be string-checked.
  Fix: errors arrive as plain strings (`Function "...`, `Parameter error: ...`). String-check every result.

- `ObjectTools.set_properties` takes `values` as a JSON string, not an object. A material refPath inside it needs the full Package.Object form.
  Fix: `ObjectTools.set_properties` `values` is a JSON string; material refPaths inside it use `Package.Object` form.

- `overrideMaterials` set through `set_properties` can return true and silently not persist; read back with `get_properties` and rebuild the actor if it did not take. `add_*` primitives attach as secondary components, so iterate every StaticMeshComponent from `get_components` when assigning materials.
  Fix: read back with `get_properties`; if `overrideMaterials` came back empty, rebuild the actor. Primitives attach as secondary components: iterate every StaticMeshComponent from `get_components`.

- `MaterialTools.connect_to_output` material_property values need the `MP_` prefix (`MP_BaseColor`, `MP_Normal`, `MP_EmissiveColor`); a bare `BaseColor` errors. TextureSample outputs are RGB, R, G, B, A, RGBA.
  Fix: `connect_to_output` needs `MP_`-prefixed properties.

- An xform with a rotation must give pitch, yaw, and roll together; omit a field for identity. Units are centimeters, Z up.
  Fix: rotation needs pitch, yaw, and roll together. Units cm, Z up.

- `EditorAppToolset.CaptureViewport` requires `captureTransform`, `annotations`, and `bShowUI` keys; `captureTransform` null captures the current viewport. Call `SelectActors` with an empty list first or the selection outline and gizmo bake into the capture. Editor sprites (lights, player start, cameras) and the axis widget still appear with `bShowUI` false; reviewers ignore them.
  Fix: `SelectActors([])` before every capture. `captureTransform: null` captures the current viewport; pass the `GetCameraTransform` result to be explicit. Editor sprites and the axis widget remain; ignore them when reviewing.

- `SceneTools.find_actors` returns refPaths only; the label comes from `ActorTools.get_label` and the class from `ObjectTools.get_class`. Batch-spawned actors share a `_UAID_` segment.
  Fix (not in unreal-notes.md; from the footgun itself): read the label with `ActorTools.get_label` and the class with `ObjectTools.get_class` after `find_actors`, per actor.

- The template level already has a DirectionalLight and sky; adding another directional light triggers a competing-lights warning. Reuse the existing sun.
  Fix (not in unreal-notes.md; from the footgun itself): reuse the existing sun instead of adding a second directional light.

- Pure Blueprint node outputs are recomputed per connected wire; store a reused result in a variable. Casting to a Blueprint class creates a hard load dependency; prefer interfaces.
  Fix (not in unreal-notes.md; from the footgun itself): store a reused pure-node result in a variable, and prefer interfaces over casting to a Blueprint class.

- `BlueprintTools.write_graph_dsl` compiles the Blueprint; a compile warning or error comes back in the result text, not as an exception. Class paths, enum values, and asset refs inside DSL must be quoted strings.
  Fix: `write_graph_dsl` compiles; read the result text for warnings. Compile with `warnings_as_errors: true` once per logical unit, then `read_graph_dsl` and compare to intent.

## Claude Code harness

- Agent `tools:` frontmatter is advisory for Wright's subagents in the sessions tested (2026-09-20, Retrieval): a subagent declared without Edit could still call Edit on a scratch file. The read-only boundary for the engine investigator and the validator is therefore their instructions (no mutating `call_tool`, no `execute_tool_script`, no edits to the plan or the project) and the CALL LEDGER the executor writes, not the grant list.
  Fix: keep the grant lists as documentation of intent; never rely on them as a safety boundary; the Validator's grounding check and the operator's git diff of the project are the real backstops.

## Survey source for the first two entries

`knowledge-base/03-tool-survey.md` confirmed both of the entries above live before they were generalized into the profile. `find_actors({})` and `find_actors({"name": ""})` were rejected with "input param ... is required"; the working call supplied all six keys with explicit nulls, which the profile generalizes to every tool. `find_assets` returned `/Game/FirstPerson/Blueprints/BP_FirstPersonCharacter`, which `list_variables` rejected until "." plus the asset name was appended, which the profile generalizes to every Blueprint and asset tool call.
