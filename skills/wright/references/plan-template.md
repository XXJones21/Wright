# Wright run plan: <slug>

Shared state for the Wright pipeline. The conductor appends each section; every agent reads the whole file. Sections appear in this order and are never reordered.

- Run slug: <slug>
- Created: <YYYY-MM-DD>
- Project: <ue_project_root>
- Level: <level asset path from get_current_level>
- Stop after: <beat or "validate">
- Design docs: <design_docs>

## Task

<the task text verbatim>

## Engine grounding config

<contents of profiles/ue5.config.json, verbatim, as a ```json fence>

## PROJECT GPS

Snapshot of what exists in the live project at Gate 1. Read-only ground truth.

### Level
- Path: <level path>
- Outliner folders: <get_folders>

### Actors (<count>)
| refPath tail | label | class | location |
| --- | --- | --- | --- |

### Assets under /Game
- Folders: <list_folders /Game>
- Blueprints (<count>): <object paths>
- Materials (<count>): <object paths>
- Textures (<count>): <object paths>
- Data tables (<count>): <object paths>

### Blueprints named by the task
For each: parent class, variables (list_variables), functions (list_functions), custom events (list_events), and the EventGraph as DSL (read_graph_dsl).

<truncation notice if GPS_MAX_CHARS was hit: "GPS TRUNCATED at <n> chars: <what was cut>">

## TOOL API

Per toolset the run will touch: a `### <fully qualified toolset name>` heading, then the raw describe_toolset result as a JSON block. The tool-call gate reads these.

## PROJECT SKILLS

Output of AgentSkillToolset.GetSkills for every skill ListSkills returned whose description matches the task (always: BlueprintBasicsSkill, MaterialBasicsSkill). These rank above Wright's defaults.

## Append order (do not pre-create these headings)

Each beat appends exactly one of the headings below, in this order, the first time it runs. Never pre-create one ahead of the beat that owns it: gates.py and later beats find a section by its first `## ` match, so a placeholder heading created early would shadow the real one appended later.

```text
## Plan (orchestrator)
Appended by Beat 1: GOAL, INV-n gaps through the four lenses, CLM-n claims.

## Finding: engine
Appended from findings/engine.md: one CLM-n: VERIFIED|REJECTED|UNVERIFIABLE line per claim, then the bottom line.

## Finding: reference
Appended from findings/reference.md: grounded loop patterns, options per INV, what has no precedent.

## Synthesis (design)
Appended by Beat 3: every INV resolved as LOCKED / FORK / OPEN, the instrumented core action, provisioning, economy values, adversary and exits, concept plates linked, then the BUILD TASKS block.
BUILD TASKS
- [editor|blueprint|texture|needs-you] <title>: <brief>

## Artifact <n>: <title>
Appended per executor: the artifact body, the read-back evidence, capture paths, and the CALL LEDGER fence.

## Gate
Appended by scripts/gates.py.

## PROJECT GPS (post-build)
Re-snapshot after Execute, same shape as PROJECT GPS.

## Validation
Appended from the validator: four checks and VERDICT: ship|revise with the gap list.

## Close
Beat statuses, artifact paths, the ordered NEEDS YOU list, the save reminder.
```
