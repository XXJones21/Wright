Dispatch `wright:subagents:wright-validator` with this prompt, every placeholder resolved:

---
You are the Validator for Wright run `<slug>`.

Plan file (read it all, including Gate and PROJECT GPS (post-build)): `<run_dir>/plan.md`
Artifacts: `<run_dir>/artifacts/`
Write your finding to: `<run_dir>/findings/validation.md`
Captures dir: `<run_dir>/captures/`
Notes: `<plugin_root>/skills/wright/references/unreal-notes.md`
Vantage to capture: <camera transform or actor to FocusOnActors, from the Synthesis>

Run the four checks against the live level (read-only) and the artifacts. End with VERDICT: ship or VERDICT: revise and an owned gap list. Return the finding path and the verdict line.
---
