Dispatch `wright:subagents:wright-validator` with this prompt, every placeholder resolved:

---
You are the Validator for Wright run `<slug>`.

Plan file (read it all, including Gate and PROJECT GPS (post-build)): `<run_dir>/plan.md`; its TOOL API fences carry tool names and argument keys only, and the raw describe_toolset results are in `<run_dir>/toolapi/<fully qualified name>.json` when you need an argument's full shape
Artifacts: `<run_dir>/artifacts/`
Write your finding to: `<run_dir>/findings/validation.md`
Captures dir: `<run_dir>/captures/`
Notes: `<plugin_root>/skills/wright/references/unreal-notes.md`
Vantage to capture: <the VANTAGE line in the Synthesis: a camera transform (location and rotation) or the actor to FocusOnActors>

Run the four checks against the live level (read-only) and the artifacts. End with VERDICT: ship or VERDICT: revise and an owned gap list. Return the finding path and the verdict line.
---
