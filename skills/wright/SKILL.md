---
name: wright
description: "Plan game-wide Unreal prototypes in a shared sandbox, then build and polish a selected mission through playable phase handoffs and bounded packets. Use for gameplay pre-production, a mission slice, a focused engine probe, or continuation of a Wright run."
---

# Wright: a gameplay workflow harness

Wright supplies outcome selection, scoped context, evidence, and continuation state.
The host agent supplies reasoning, tools, and optional worker execution. Read the
short [core](references/wright-core.md), then the shared
[packet workflow](references/packet-workflow.md). In Codex, read the
[host adapter](references/codex-workflow.md) for tool discovery and dispatch.

## Direct the production pipeline

The current orchestrator acts as director; do not spawn a separate director role.
Read [production phases and discipline briefs](references/production-pipeline.md).
For pre-production, read [game-wide planning](references/preproduction-planning.md).
Map the whole GDD and mission dependencies into a compact coverage plan, then prove
small player experiments in separate rooms of one named prototype sandbox. Include
camera/equipment behavior, a contextual debug HUD and concepts across the planned
mission environments. Explicitly narrower probes retain their narrower scope.
Across all three phases, identify shared systems/assets and their consumers before
dispatch; every specialist proves, extends and refines these foundations through
appropriate variations, including code, animation, materials, textures and VFX.
Dispatch a bounded environment-art concept packet in parallel when useful. Concept
work owns run-local images/briefs and has no editor access. One editor worker and
one concept worker may be active; the director serializes state publication.

Present the playable rooms, coverage/deferrals, core-loop evidence and selected concept
images for explicit user approval before production. Production focuses on the named
mission/slice using the approved foundation, AI and additional mechanics. Review and
obtain approval before post-production,
which covers lighting, material refinement and short QA. Present that result for
final acceptance. The helper records exact review/approval bindings; the director
must supply actual user messages, never self-approval. Continue normal packets inside
the active phase without new approval requests at every checkpoint.
Every phase handoff must be playable by the user. Provide the saved level, launch
steps, tested controls, objectives, known issues and runtime evidence; then collect
the user's actual playtest feedback and approval before advancing. Artifacts or
screenshots alone cannot complete pre-production, production or post-production.

Load only the selected discipline's brief. Roles define expertise; packets define
bounded outcomes. A role may be adopted by the current agent or dispatched as needed.

## Establish the environment first

Resolve the user's intended project and target level before editing. For a new
slice, propose a named isolated test level. Never substitute the currently open
level because a creation tool is missing. Existing-level work requires the user's
explicit choice, recorded with the environment contract. An asset folder or outliner
folder does not isolate a level.

When the user has prepared a new test level, use that named level directly. Record
`--level-mode existing` with the user's explicit selection as the reason; this means
the level already exists, not that prior generated mission content may be reused.
Verify the canonical package path, connected project and saved baseline. Do not
create, duplicate, rename or Save As another level to satisfy the default setup flow.
In a from-scratch evaluation, record allowed template sources and excluded prior-run
assets; create mission-specific content in a fresh owned namespace. Do not copy prior
run graphs, generated assets, actors, concepts or completion state into the new run.

Initialize packet state with `scripts/work_packets.py`. The first bounded prerequisite
is establishing a supported route to create/open the intended level and persist it.
Discover that route from the current tools; do not treat the old survey's missing
level-creation tool as a universal engine limitation. Create only the named test
level within the user's scope. Record setup objects, counters and uncertainty through
`setup-progress`; reconcile an interrupted setup before another write. If no supported route is available, report the exact
setup handoff and stop dependent builds. Do not modify the current map as a fallback.

Bind evidence of the connected project, exact target level, isolated-level provenance
when applicable, and persistence. Recheck live project/level and PIE state immediately
before mutations and after a session/model switch. Evidence files do not monitor the
editor. The helper validates recorded contracts, not actual tool permissions.

## Repeat a small work loop

1. **Choose one outcome.** One observable behavior, or one uncertainty resolved.
   Preserve design choice through the four lenses in the core; do not design all
   future systems before the next useful result.
2. **Load its dependencies.** Use the selected packet, environment contract, and
   verified dependency summaries. Retrieve full schemas or logs only as needed.
3. **Resolve blocking unknowns.** Skip research when current evidence suffices.
   An omitted object in a partial query is unknown, not absent.
4. **Make the bounded change.** One worker holds the editor. Record changed objects
   and progress after each logical unit. No speculative dressing before the first
   functional action-to-outcome chain unless the user's objective is visual work.
5. **Verify, save, checkpoint.** Complete every packet check, distinguish static from
   runtime evidence, prove persistence, and publish the result through the helper.
   Continue eligible packets within the active phase and user's scope without requesting approval
   at every boundary. A checkpoint is not a new permission requirement.

Plan, investigate, synthesize, execute, and validate are reasoning activities used
as needed within this loop. They are not five mandatory global stages. Keep the queue
small; define follow-up packets when preceding results justify them. Never name a
whole mission director as one chunk merely because it is one Blueprint asset.

## Budgets, interruption, and delegation

Choose a tool-call/time budget for each packet; examples are initial tuning values,
not proven performance promises. Check consumption before beginning another unit.
At exhaustion, uncertain mutation, or repeated failure, checkpoint and split or
reconcile the remaining work. Let an already-issued operation settle; record its
outcome. A successfully verified unit can finish while recording a budget overrun.
Never silently reset counters or repeat a create after an ambiguous result.

`status` and `resume` only read saved state. Continuing an interrupted packet requires
fresh live inspection and an explicit reconciliation record. Supply the next model
with the compact packet report; do not rebuild its context from the full transcript.
Use [worker contracts](references/worker-contracts.md) only when a separate role adds
value. Routine work can remain with one agent. Concept art can run alongside editor
work in its separate lane; editor operations remain serialized.

## Engine and evidence

Read [Unreal notes](references/unreal-notes.md) before engine operations. Read the
[Blueprint playbook](references/blueprint-lane-playbook.md) or
[texture playbook](references/comfy-texture-playbook.md) only for that lane.
Discover signatures before use, inspect meaningful results, and read back changes.
A reviewed recipe may batch known read operations; keep arbitrary editor scripts
read-only. Future mutation recipes need separate validation and ownership controls.

Do not edit pre-existing assets outside the packet's allowed changes. Keep generated
content run-scoped. Unsupported actions receive a concrete handoff. Never report
`ship`, gameplay success, or persistence from a narrative assertion alone.

## Report

Use [execution metrics](references/execution-metrics.md) to distinguish director work
from actual subagent execution, including implementation, verification and coordination.
Record available counters at normal checkpoints; never infer delegation from a role label.

Return the outcome achieved, evidence paths, persistence, runtime status, actual
call/time metrics when available, unfinished work, and exact next action. Completion
of registered packets is not completion of an entire mission. Summarize what the
user can now test. Legacy runs are not implicitly migrated into packet execution.
