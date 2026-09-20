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
