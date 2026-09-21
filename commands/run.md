---
description: Run the Wright game-development pipeline (Plan -> Investigate -> Synthesize -> Execute -> Validate) against the live Unreal Engine 5.8 editor.
argument-hint: <task> [--stop-after plan|investigate|synthesize|execute|validate] [--project <ue_project_root>]
---

Load and follow the `wright` skill. Parse the arguments below: everything before the first `--` flag is the task text; `--stop-after <beat>` ends the run after that beat; `--project <path>` overrides `UE_PROJECT_ROOT` from the machine config. Run Gate 0 and Gate 1, then the beats in order, coordinating the leaf subagents through the run's plan file, and finish with the Close summary and the NEEDS YOU list.

Task / arguments:

$ARGUMENTS
