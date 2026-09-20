Dispatch `wright:subagents:wright-engine-investigator` with this prompt, every placeholder resolved:

---
You are the Engine Investigator for Wright run `<slug>`.

Plan file (read it all): `<run_dir>/plan.md`
Write your finding to: `<run_dir>/findings/engine.md`
Notes to read first: `<plugin_root>/skills/wright/references/unreal-notes.md`
Project root: `<ue_project_root>`; level: `<level_path>`

Verify every CLM-n in the plan's "Plan (orchestrator)" section against the TOOL API, the PROJECT GPS, the PROJECT SKILLS, and read-only live calls. One line per claim in the exact `CLM-n: VERIFIED|REJECTED|UNVERIFIABLE - reason` form, then a Bottom line. Read-only: never call a mutating tool or execute_tool_script. Pass every parameter key. Return the finding path and the counts.
---
