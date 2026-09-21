# Wright for Codex

**Build playable Unreal Engine projects through a structured production workflow.**

Wright is a workflow harness for Codex. It turns a game design into small, verifiable tasks, preserves progress between sessions, and organizes development around three playable handoffs: pre-production, production, and post-production.

Codex supplies the reasoning, tools, and subagents. Wright supplies the project boundaries, discipline briefs, task records, evidence, and review process. The human remains the creative director and evaluates the playable result at each phase boundary.

> **Status: alpha / local development preview.** The first Codex pre-production implementation is complete and undergoing human playtest review. Feedback identified unresolved equipment interactions, squad behavior, evacuation, and UI issues; the phase has not been approved. Production and post-production have not completed an end-to-end live evaluation. Development source includes improvements added after the installed evaluation snapshot; the current run does not validate every change in this tree. Public installation instructions and a release summary will follow the evaluation.

## The production pipeline

| Phase | Scope | Human handoff |
| --- | --- | --- |
| **Pre-production** | Read the whole game design. Establish shared systems and test important mechanics in rooms of one prototype sandbox. Include camera and equipment behavior, contextual debug UI, and concepts for the planned environments. | Play the sandbox, inspect coverage and concepts, discuss gaps, and approve the foundation. |
| **Production** | Build the selected mission or slice from the approved foundation. Develop its layout, content, AI behavior, and additional mechanics. | Play the integrated mission and review behavior, pacing, content, and remaining issues. |
| **Post-production** | Refine lighting, materials, effects, and presentation. Address small defects and run focused QA. | Evaluate the polished playable result and accept it or request corrections. |

Normal verification happens throughout all three phases. The phase boundary is a consolidated stakeholder review, with the saved level, launch instructions, controls, objectives, evidence, and known issues.

Wright should continue eligible work inside the authorized phase while the human is away. A pending subjective check holds work that truly depends on it; it should not become a request for permission after every task. Advancing to the next phase requires explicit human feedback and approval.

See the [production pipeline](skills/wright/references/production-pipeline.md) and [pre-production planning guide](skills/wright/references/preproduction-planning.md).

## Build a foundation the project can reuse

**Plan across the whole project, build shared foundations, and specialize them for known uses.**

This applies to every discipline and phase:

- Squadmates and enemies can share character, movement, and state capabilities while keeping distinct decision logic.
- Player and NPC equipment can share compatible animation assets and action interfaces.
- Related surfaces can use a common material parent with instances and reusable texture sets.
- Related effects can share VFX logic, materials, and textures with appropriate variation controls.
- Different rooms and missions can compose the same modular environment kit.

Inspect what the project and its templates already provide before building a replacement. Inspect a functional feature as a whole: using a supplied weapon mesh while rebuilding its working shooting mechanics is only partial reuse. Record whether a task reuses, adapts, or creates a capability, and why.

Reuse follows actual project needs and compatibility. A prototype can simplify presentation or behavior depth, but a stand-in cannot prove a system it bypasses. Scripted markers do not validate character navigation. Deliberate throwaway work and remaining production dependencies stay visible.

## Small tasks, durable progress

Wright calls each bounded task a **work packet**. A packet has:

- One observable outcome or uncertainty to resolve.
- A production phase, discipline, dependencies, and allowed changes.
- Acceptance checks and a tool-call/time budget.
- Saved progress, changed objects, evidence, and a next action.

A large Blueprint or mission will span several packets. The director loads the relevant context, performs or delegates the work, verifies it, saves it, and continues with the next eligible packet.

The helpers track environment bindings, dependencies, evidence fingerprints, budgets, and phase transitions. After an interruption or session change, inspect the live project and reconcile uncertain work before continuing. A new conversation does not require rebuilding a saved prototype.

The helpers validate recorded evidence and transitions. They do not independently prove gameplay, authenticate a human approval, or enforce editor permissions. Completed packets are not a percentage of the whole game completed.

[Packet protocol](skills/wright/references/packet-workflow.md) · [Codex adapter](skills/wright/references/codex-workflow.md)

## Director and specialist roles

The main Codex task acts as the director. It owns scope, shared interfaces, scheduling, integration, and human reviews.

| Discipline | Responsibility |
| --- | --- |
| Layout artist | Playable scale, routes, sightlines, and objective placement. |
| Gameplay programmer | Player actions, equipment, feedback, UI, and progression. |
| AI programmer | Shared character foundations, navigation, commands, and role-specific behavior. |
| Environment artist | Concept direction, reusable content, materials, and environment assembly. |
| Lighting artist | Visibility, mood, and lighting/material integration. |
| Reviewer | Bounded checks, reproducible defects, and evidence of playable behavior. |

These are selectively loaded briefs. A role may be performed by the director or assigned to a separate Codex subagent; adopting a role is not itself delegation.

One worker owns the editor at a time. A concept worker can work in parallel on its own images and briefs without editor access. Subagents receive a focused outcome, relevant context, shared interfaces, constraints, and acceptance checks. Model and reasoning choices follow the user's session policy and are recorded when observable.

[Worker contracts](skills/wright/references/worker-contracts.md)

## Using the local Codex preview

### Requirements

- Codex with the Wright skill/plugin available in the task.
- An Unreal project and a working Unreal MCP connection exposing the required editor tools.
- Python 3.11 or newer for the state helpers and dashboard.
- An available image-generation tool for concept packets. ComfyUI is optional unless that workflow is explicitly part of the test.

The state helpers and dashboard use the Python standard library. Texture utilities additionally use NumPy and Pillow. Actual engine capabilities are discovered from the connected tools; Wright does not assume every installation exposes the same operations.

The Codex package entry is [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json), with instructions in [`skills/wright/`](skills/wright/SKILL.md). This is currently a local preview, not a published marketplace install. Installing the plugin does not configure the project's Unreal MCP connection, and the historical Claude MCP configuration is not a Codex setup procedure.

### Start a run

Once the local plugin is available, open a fresh Codex task in the Unreal project directory and provide the design document, project, and intended sandbox level. For example:

```text
Use $wright to read the whole game design and plan pre-production.
Use the existing level /Game/Prototype/L_Prototype as the shared sandbox.
Inspect the template's existing systems before implementing replacements.
Build small room experiments with contextual debug UI and mission concepts.
Keep production focused on Mission 1 after I review and approve the sandbox.
```

The level path above is an example. Wright must verify the exact project and level before editing. If you prepared a level, it should use that level rather than duplicate or rename it. A fresh evaluation should explicitly identify allowed template sources and excluded prior-run content.

For a narrower task:

```text
Use $wright for a focused squad-navigation probe in the selected sandbox.
Prove one animated character can reach a commanded target around an obstacle,
hold position, and report an unreachable destination.
```

For continuation:

```text
Use $wright to resume the existing run at <absolute run directory>.
Read the current plan and evidence, reconcile the live editor state,
and continue the remaining pre-production packets.
```

Project settings belong in `<Unreal project>/wright/config.json`. The [example configuration](profiles/wright.project.example.json) shows the default run and texture directories. Run artifacts remain with the Unreal project rather than inside the plugin.

After a plugin reinstall, prefer a fresh Codex task that discovers the updated instructions. Preserve the existing level and run evidence, and record the version change instead of rewriting the original provenance.

## Production dashboard

From this repository, start the read-only local dashboard:

```sh
python scripts/dashboard.py --run "<absolute run directory>"
```

Open the loopback URL printed by the command. The dashboard refreshes saved state every 20 seconds while visible and shows:

- All three phases, registered tasks, budgets, and open verification.
- Task outcomes and links to their supporting evidence.
- Concept boards, generator provenance, and saved Unreal captures.
- Readable plans and handoffs with source timestamps.
- Executor attribution and reuse decisions where recorded.

The dashboard performs no Unreal operations, changes no run state, and makes no model calls. Stop it with `Ctrl+C`; use `--port <number>` for a stable local address. It displays one run at a time. A later linked production run can be opened with its own path.

Proposals, untested behavior, blocked checks, and completed tasks remain distinct. Older planning notes do not override newer execution evidence.

## Measure who does the work

A discipline label does not tell you whether the director or a subagent performed a task. Wright's [execution metrics contract](skills/wright/references/execution-metrics.md) records:

| Measurement | What it helps evaluate |
| --- | --- |
| Executor identity and observed model/reasoning | Actual delegation and the settings used. |
| Implementation, verification, and coordination calls | Where task effort is going. |
| Retries, active/wait time, and budget overruns | Rework, bottlenecks, and recovery. |
| Available input, cached-input, output, and reasoning counters | Model activity within the recorded scope. |
| Reuse/adaptation decision and inspected candidates | Necessary new work versus avoidable rebuilding. |

Unknown values stay unknown. Estimates are labeled. Reports do not count child calls again as director calls, treat wrapper requests as underlying engine operations, or infer account-limit usage from raw tokens.

For optional session-level observations, add a local Codex rollout:

```sh
python scripts/dashboard.py --run "<absolute run directory>" --session "<absolute rollout.jsonl>"
```

Repeat `--session` for additional root sessions. The reader discovers explicitly spawned descendants in the same log folders and publishes summaries, not transcripts. System approval reviewers are excluded from specialist-worker discovery. These session totals are separate from per-packet attribution, billed cost, and account usage.

## Development and evaluation

Create an isolated Python environment, install the development dependencies, and run the offline suite:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest scripts/tests -q
```

The dashboard and executor-metrics checks can also run without installing test dependencies:

```sh
python -m unittest discover -s scripts/tests -p test_dashboard.py
python -m unittest discover -s scripts/tests -p test_execution_metrics.py
```

Tests use synthetic projects and files; they do not operate Unreal or ComfyUI. Platform-specific checks may skip. Offline tests establish helper behavior, not the quality or completeness of a generated game. Live evaluations need playable evidence and human feedback.

Current evaluation questions include whether the director delegates suitable work, inspects supplied systems before rebuilding, continues independent tasks while the human is away, and produces a useful consolidated phase handoff. See the [unattended phase-review scenario](docs/evaluations/unattended-phase-review.md).

The [interrupted earlier-run review](docs/baselines/2026-09-20-claude-interrupted/review.md) informed the redesign. There is no established comparative efficiency claim: compare equivalent scopes, starting states, and acceptance outcomes rather than raw call totals from different workloads.

## Repository layout

```text
.codex-plugin/                 Codex plugin manifest
skills/wright/                 Entry skill, workflow references, and discipline briefs
scripts/work_packets.py        Packet state and phase-review helpers
scripts/dashboard.py           Local read-only dashboard server
scripts/dashboard.html         Dashboard interface
scripts/execution_metrics.py   Executor attribution and session-log summaries
scripts/tests/                 Offline checks
profiles/                      Configuration examples and engine profile
docs/                          Design records and evaluation notes
```

The `.claude-plugin/`, `commands/`, and `agents/subagents/` directories retain historical Claude harness files. They are not Codex agent registrations. Legacy state helpers remain for previous-format evidence and reject packet-mode use through their old mutation paths; stopped legacy runs are not silently migrated.
