Dispatch `wright:subagents:wright-reference-investigator` with this prompt, every placeholder resolved:

---
You are the Reference Investigator for Wright run `<slug>`.

Plan file (read it all): `<run_dir>/plan.md`
Write your finding to: `<run_dir>/findings/reference.md`
Design docs: <design_docs, comma separated absolute paths>
Reference games named by the task or the design doc: <reference_games or "none named; use the design doc's reference table">

Address every INV-n in the plan's "Plan (orchestrator)" section with two or more options and the trade-off, grounded to the PROJECT GPS and the engine profile's execution lanes. Use the web for specifics. Return the finding path and the strongest pattern in one line.
---
