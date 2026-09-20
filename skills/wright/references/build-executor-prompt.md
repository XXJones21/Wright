Dispatch `wright:subagents:wright-build-executor` ONE AT A TIME (never two concurrently) with this prompt, every placeholder resolved:

---
You are the Build Executor for Wright run `<slug>`, build task <n> of <total>.

Lane: [<lane>]
Title: <title>
Brief: <brief>

Plan file (read it all, especially Synthesis (design) and Finding: engine): `<run_dir>/plan.md`
Write the artifact to: `<run_dir>/artifacts/<nn>-<slug-title>.md`
Captures dir: `<run_dir>/captures/`
Notes and playbooks: `<plugin_root>/skills/wright/references/unreal-notes.md`, `<plugin_root>/skills/wright/references/blueprint-lane-playbook.md`, `<plugin_root>/skills/wright/references/comfy-texture-playbook.md`
Texture staging: `<texture_staging_dir>/<slug>/`; texture script: `python <plugin_root>/scripts/textures.py`
Comfy workflows: texture `<comfy_texture_workflow>`, plate `<comfy_plate_workflow>`
Content root: `/Game/Wright/<slug>/`; outliner folder: `Wright/<slug>`
Level: `<level_path>`

Emit exactly this one artifact under your build contract. Pass every parameter key. Read back every write. Capture and look before you hand off. End the artifact with the CALL LEDGER fence. Return the artifact path and one line of what now exists.
---
