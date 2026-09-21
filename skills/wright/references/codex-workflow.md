# Codex adapter

Read packet-workflow.md for the shared protocol. This file only adapts that protocol
to the host. Wright does not create another agent runtime or assume Claude command,
Agent, ToolSearch, or tools-frontmatter behavior exists in Codex.

- Discover available Unreal tools by capability: list_toolsets, describe_toolset,
  call_tool. Record the actual callable names. A Claude-generated .mcp.json is not
  assumed to configure Codex. Do not rewrite MCP settings as part of a build.
- Use the existing host's file, shell, image-inspection, and research tools. The plugin
  root is two levels above this skill folder. Quote absolute paths to Python helpers.
- Read engine-provided project skills using exact paths from ListSkills when available.
  Epic's Claude plugin is not a required Codex package. Describe schemas for tools
  actually needed; cache them with server/engine version and context provenance.
- Discover optional comfy-local tools separately. No texture generation is required
  for a functional interaction test. Missing ComfyUI should not block that test.
- Use Codex subagents only for a concrete independent investigation or useful review.
  Also dispatch a bounded environment-art concept packet alongside editor work when
  useful in pre-production. Load its discipline brief, phase, lane and owned output
  paths; the main orchestrator remains the director. Discover available image tools
  and follow their skills. Concept workers receive no editor assignment.
  Supply a fresh, bounded packet when supported. Use native wait/send operations;
  do not create sidebar tasks or automations for leaf workers. If delegation is
  unavailable, perform the roles sequentially.
- Report live progress in terms of the packet outcome and blocker. At a model/session
  transition load the compact packet status and its evidence paths, verify the actual
  editor binding, and reconcile uncertain writes before continuing.
  Resume also reports the production phase and pending review; a model/session
  change cannot supply or bypass user approval.
- Open meaningful captures or reports when useful. Do not create screenshots for
  nonvisual asset operations solely to satisfy a blanket reporting rule.
- Show selected concept boards directly during the human review, identify the actual
  generator, and link the game-wide concept/coverage index. A saved image hidden in a
  run folder is not a presented art-direction decision.

## Plugin updates and continuation

After reinstalling Wright, prefer a new Codex task for reliable discovery of updated
skills/tools. Do not assume an existing conversation has hot-reloaded instructions.
For an explicitly requested same-task continuation of an instruction-only update,
read the newly installed manifest, SKILL.md and changed references by their verified
absolute paths; record that this is an explicit instruction refresh, not proof that
the host reloaded its plugin registrations or MCP tools. Changed tools need fresh
discovery and the host's supported refresh/new-session boundary.

In either case, preserve the saved prototype and run evidence. Inspect helper status,
read current scope/coverage and user feedback, and reconcile live project, canonical
map, PIE and pending work before writes. Record the new version and dated scope
amendment separately; never rewrite the original run's provenance. A fresh task can
continue an unapproved run; it does not mean starting the game assets from scratch.

The shared helpers perform no editor calls. They validate recorded evidence and
state transitions. Permissions and actual tool execution remain with Codex and the
connected tool servers; a role prompt or ledger is not a security boundary.

The .claude-plugin, commands, and agents/subagents directories are historical v0.1
harness files. They are not active Codex registrations. Porting those wrappers to
this same packet protocol is separate from changing the method or data format.
