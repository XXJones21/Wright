# Overview

Wright is a game-development reasoning core: a five-beat orchestrator (Plan, Investigate, Synthesize, Execute, Validate) that holds design judgment and delegates grounding, research, building, and validation to focused workers. It runs as a skill-as-conductor, the-archive pattern: main-context Claude runs `skills/wright/SKILL.md` and holds Plan and Synthesize itself, while four leaf agents (engine-investigator, reference-investigator, build-executor, validator) fan out through the Agent tool for the beats that need grounding, research, building, or validation. Every beat shares state through one run plan file, `plan.md`, whose section order and append order are fixed by `skills/wright/references/plan-template.md`.

Wright divides labor with Epic's `unreal-engine-skills-for-claude-code` plugin: Epic's plugin onboards the model to Unreal, and Wright is the game-development method built on top of it. Wright ships no Unreal MCP playbook, no `.mcp.json`, and no toolset-discovery instructions of its own; it requires Epic's plugin and the project `.mcp.json` that the editor generates, and adds the design pipeline, the grounding gates, and the ComfyUI asset lane on top. The engine target is UE 5.8 only, since Epic's Unreal MCP is a UE 5.8 editor plugin that does not run in UEFN.

Wright's dependencies are Claude Code, Epic's `unreal-engine-skills-for-claude-code` plugin, the target project's Unreal MCP, and `comfy-local-mcp`; it needs no Valinor, Hearth, Valar, or Engram. Its own repo layout carries the conductor skill and its references, the four leaf-agent prompts under `agents/subagents/`, the engine grounding profile at `profiles/ue5.config.json`, the deterministic gate scripts under `scripts/`, this knowledge base, and the design spec under `docs/superpowers/specs/`. A run lands in `<RUNS_DIR>/<slug>/`, with `plan.md` as the shared state file plus `findings/`, `artifacts/`, `plates/`, and `captures/` subfolders for what each beat produces.

## Requirements

1. Unreal Engine 5.8 with a project that has the `ModelContextProtocol` and `AllToolsets` plugins enabled (Edit > Plugins). With only `ModelContextProtocol` enabled the server exposes no editor tools.
2. Editor Preferences > General > Model Context Protocol: Auto Start Server on, port 8000, URL path `/mcp`, Enable Tool Search on.
3. In the editor console: `ModelContextProtocol.GenerateClientConfig ClaudeCode`. This writes `.mcp.json` next to the `.uproject`.
4. Claude Code plugins: `unreal-engine-skills-for-claude-code@claude-plugins-official` and `comfy-local-mcp@josh-plugins`, plus this plugin (`wright@josh-plugins`).
5. ComfyUI running with comfy-local configured (`/comfy-setup` if not).
6. Python 3.11+ with `numpy` and `pillow` for the texture scripts, `pytest` for the tests.
