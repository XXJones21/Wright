# Production phases

The main host agent acts as the director. It owns scope, priorities, packet dispatch,
integration and user reviews; there is no separate director agent. Load only the
discipline brief needed for the next packet. A role can be performed by the current
agent or dispatched to a worker when that saves context or enables independent work.

## Three states

| State | Work | Review before advancing |
| --- | --- | --- |
| pre-production | Read the whole design; map shared and mission-specific mechanics. Build bounded experiments in rooms of one prototype sandbox, with debug HUD, equipment stand-ins and mission concept coverage. | Playable sandbox tour, mechanic coverage/evidence, selected concepts, explicit deferrals and named production target. User approves before production. |
| production | Build the selected mission/slice using the approved foundation, layout and concepts; implement production AI and agreed mechanics. Retain the sandbox for regression. | Integrated content and behavior work together in that playable mission/slice. User approves before post-production. |
| post-production | Refine lighting and materials, fix small presentation issues, run a short focused QA pass. | Present the polished result, smoke-test evidence and remaining issues for final user acceptance. |

Use [preproduction-planning.md](preproduction-planning.md) for the coverage plan,
room experiments, contextual UI and scope-aware production handoff. Game-wide
planning is the default; a focused probe remains explicitly scoped. Production can
target Mission 1 without claiming that all future mission mechanics are validated.

Phases organize production decisions; packets remain the unit of execution. Do not
turn a phase or an entire discipline into one enormous packet. Verification, saving
and functional testing happen throughout; post-production QA is a final smoke pass.
Every phase ends in a saved, runnable level for human-in-the-loop evaluation. Supply
the exact level, launch steps, controls, objectives, known issues and runtime evidence.
Pre-production can use blockout geometry and declared stand-ins, but its core loop
must be playable. Production and post-production preserve that playable loop while
adding content and polish. Screenshots, concepts and compiled graphs alone cannot
complete a phase. The user must play and evaluate the handoff before approval.
Record major defects as blocked work with the smallest corrective plan. Do not bury
a missing core mechanic under lighting polish or launch unbounded review loops.

For a focused capability probe, finish its requested outcome without pretending to
complete a whole production pipeline. Scope exclusions are visible in the review
and require user acceptance if the run is to advance.

## Shared foundations in every phase

Every discipline plans reuse across the project's known needs throughout all three
phases. Before creating a system or asset, inspect the existing foundation and its
consumers; choose reuse, a supported variation, a shared extension, or a justified
separate implementation. Record ownership, consumer references, variation points and
important compatibility constraints in the current plan. Carry this record through
phase handoffs and give workers the relevant entry. Reuse must respect asset ownership
and permitted sources; it does not authorize editing stock or unrelated assets.

Inspect supplied functional features as well as individual assets. For a template
weapon, examine the available input, aiming, firing/hit handling and animation path
together before rebuilding shooting logic and later swapping in its mesh. Record
which existing capability was inspected, the reuse/adaptation decision and the actual
requirement or incompatibility that justifies new work. Apply the same reasoning to
other provided gameplay and art systems; a fresh task does not imply a fresh implementation.

- Pre-production identifies and proves the smallest shared foundations and their
  important variations. Art experiments need only resolve risks relevant to that phase.
- Production builds the selected mission from those foundations, adds needed variants
  and updates shared contracts as new consumers reveal requirements.
- Post-production tunes existing variants and shared assets deliberately. Before
  changing a shared parent, identify affected consumers and verify representative
  uses after the change. Keep local adjustments local when that is their intended scope.

Apply this to code and content alike. Related trees may use a common material parent
with instances for compatible surface variations; reuse suitable texture sets and
parameter conventions. Related VFX may share effect logic, modules, materials or
textures while exposing the controls needed for their distinct uses. Modular layout
kits, equipment and animation follow the same reasoning. Assign VFX ownership for
the packet to the appropriate specialist and coordinate its gameplay trigger/feedback
contract; a new permanent role is not required.

Shared foundations need not collapse into one universal asset. Separate incompatible
surface behavior, animation requirements or effect structures when the design or
performance warrants it, and record why. Do not duplicate a working foundation merely
to change appearance, a role or a mission. Do not build unused variant libraries.
Verify actual behavior, appearance and relevant cost in representative consumers;
asset ancestry or a reuse claim alone is not evidence of successful integration.

## Roles and scheduling

Assign specialists ownership of shared capabilities across their known consumers,
not a separate implementation per mission or character role. Before dispatch, agree
the foundation, role-specific variations and interfaces in the current phase's plan.
For cross-discipline systems such as equipment animation, name one owner and the
collaborating discipline. Workers extend that contract or return a concrete mismatch
for reconciliation before duplicating it. A persona supplies specialist judgment;
it does not require another agent or a larger permanent team.

- [Layout artist](roles/layout-artist.md): navigable blockout, scale, sightlines and objectives.
- [Gameplay programmer](roles/gameplay-programmer.md): reachable player actions and progression.
- [AI programmer](roles/ai-programmer.md): squad/enemy decisions, navigation and reactions.
- [Environment artist](roles/environment-artist.md): pre-production concepts; production assets and dressing.
- [Lighting artist](roles/lighting-artist.md): lighting and material integration, chiefly post-production.
- [Reviewer](roles/reviewer.md): bounded play/visual checks and reproducible defects.

By default, allow one editor packet and one concept packet to run concurrently. The
director launches the environment artist with a narrow concept brief while layout
or gameplay work proceeds. Share the mission intent, known scale, landmarks, gameplay
requirements and art constraints. Ask for a small set of useful views, such as an
annotated top-down proposal and one mood/composition view, rather than a full asset pack.

Concept workers own only `concepts/<packet-id>/` under the run. They do not access
the live editor or import/place assets. Use the user's available image tools and
their relevant skill instructions. Record generation inputs, outputs and actual
cost/call information when available. Missing generation capability is an explicit
handoff; it must not silently become an invented image or automatic paid setup.

The concept queue covers the distinct planned mission environments, with bounded
layout/mood proposals and explicit gaps. Record the actual generator and show the
selected images to the user, rather than only linking a directory. The concept brief
may initially use mission requirements while the blockout is still
being explored. Before review, reconcile the selected concept with the actual layout.
Concepts are proposals, not proof that the level exists. Any blockout-derived proposal
names its packet dependency so changes can invalidate the dependent concept result.

Only one worker controls the editor, including reads that alter selection or view.
The director alone publishes helper transitions; workers return owned artifacts and
evidence. File locks protect those short writes, not live engine ownership. Count
each worker's calls in its packet and sum the work when reporting the run's cost.
If the host cannot delegate, execute the same packets sequentially.

## Phase review and approval

Finish or explicitly defer every packet in the current phase. Settle active workers
and resolve uncertain writes before a review. Deferrals keep their original status
and remain visible; they do not count as completed dependencies. Deferred work carried
forward gets a new, current-phase packet referencing inspected partial objects.

Present a concrete review: playable evidence, captures/art proposals where relevant,
what is in scope, remaining defects, deferrals, and the proposed next-phase work.
Ask for approval of that result. Never treat the initial build request, silence,
passing tests, the director's recommendation, or a worker report as user approval.
The user requested these phase gates; ordinary packets within an approved scope do
not need additional permission at every boundary.

Write review JSON inside the run:

```json
{
  "phase": "pre-production",
  "summary": "Review the crash-site blockout, one working evidence interaction and the selected visual direction.",
  "playable": {
    "level": "/Game/Wright/EvidenceTest",
    "launch_instructions": "Open the named level in the selected project and start Play In Editor.",
    "controls": "Record the actual tested movement and interaction bindings here.",
    "objectives": "Reach the evidence item, interact, verify repeat protection and complete the tiny test objective.",
    "known_issues": [],
    "runtime_status": "pass",
    "runtime_evidence": "findings/playtest.md"
  },
  "included_packets": ["site-blockout", "evidence-loop", "site-concept"],
  "deferred_packets": {},
  "checks": [
    {"id":"playable-blockout","status":"pass","evidence":"findings/blockout-review.md"},
    {"id":"core-loop","status":"pass","evidence":"findings/playtest.md"},
    {"id":"art-direction","status":"pass","evidence":"findings/art-direction.md"}
  ]
}
```

Use actual packet IDs and evidence. The required criterion IDs are:

- pre-production: `playable-blockout`, `core-loop`, `art-direction`;
- production: `level-content`, `ai-gameplay`, `integrated-playthrough`;
- post-production: `lighting-materials`, `smoke-qa`.

For game-wide pre-production, `playable-blockout` evidence covers the room tour,
entry/return and reset; `core-loop` covers the mechanics table, demonstrated player
actions, perspective/equipment and contextual HUD; `art-direction` covers the mission
concept index, images presented and selected directions. Each includes remaining
limitations and explicit deferrals. Keep scope and the next production target in the
review summary. The helper checks evidence presence/integrity, not GDD completeness
or the truth of playtest claims; the director and human review those meanings.

A criterion excluded from this task's scope uses `status:not_applicable`, an explicit
`reason`, and supporting `evidence`; show it to the user. A failure is not an exclusion.
The playable handoff is mandatory in all three phases and cannot be excluded.
`included_packets` must list all completed current-phase packets. `deferred_packets`
maps every other current-phase packet ID to its reason for deferral.

```text
python <plugin>/scripts/work_packets.py phase-review --project <project> --run <run> --evidence <absolute-review-json>
```

After the user actually plays, evaluates and approves the result, record the exact
message, playtest feedback and source in an approval JSON. Do not infer playtesting
from a generic approval message or from the agent's own runtime test:

```json
{"decision":"approved","approved_by":"user","user_message":"<actual user message>","human_evaluation":{"played":true,"feedback":"<actual user playtest feedback>","evidence":"findings/user-playtest.txt"},"review_fingerprint":"<fingerprint returned by phase-review>","proof":["findings/user-approval.txt"]}
```

```text
python <plugin>/scripts/work_packets.py phase-approve --project <project> --run <run> --evidence <absolute-approval-json>
python <plugin>/scripts/work_packets.py phase-advance --project <project> --run <run>
```

Advance moves only to the next state; after post-production it records acceptance
of the reviewed scope. It does not independently certify the entire mission. Evidence
and state are fingerprinted. Changes after review require a fresh review and approval.
Earlier-phase packets cannot silently resume after handoff. A significant change to
the approved scope needs a newly agreed pre-production iteration in a new run, linked
to the earlier run; preserve all evidence and avoid overwriting the prior acceptance.

The helper validates the approval record and its binding. It cannot authenticate a
human message or enforce engine permissions. The director must preserve real provenance.
Old preview runs lacking pipeline state must remain inspection evidence; start a new
run instead of silently migrating them into an approved phase.
