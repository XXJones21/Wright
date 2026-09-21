# Game-wide pre-production in one sandbox

Read this when planning or expanding pre-production. The default scope is the game's
shared foundation and distinct mission mechanics, even when production will build
only the first mission. Honor an explicitly narrower capability test; name its scope
and never report it as game-wide validation. Broad planning does not authorize
unrequested editor work or implementation of every future mission.

## Read broadly, execute small

Read the whole available GDD and current user decisions before selecting packets.
Identify the player perspective, equipment/actions, shared systems, mission-specific
mechanics, cross-mission dependencies and consequential state carried between missions.
Include how familiar mechanics change: a reliable tool may later become ineffective,
or a helpful command may become difficult under fear. Check those transitions as well
as isolated actions. Record missing design decisions instead of inventing requirements.

Before the first gameplay packet, create a compact run-local PLAN.md that the user
can find. Keep it as the index rather than copying the GDD into every worker prompt.
Include the canonical sandbox level, design source/version, user clarifications,
pre-production scope, intended production mission/slice, and these two small tables:

| Mechanic or design question | Source / affected missions | Room / player experiment | Dependencies | Acceptance / evidence | Status / next decision |
| --- | --- | --- | --- | --- | --- |
| One row per distinct behavior or important transition | Source section and mission IDs | Smallest playable demonstration | Shared systems needed | Observable result, linked when tested | demonstrated, placeholder, untested or deferred |

| Mission / environment | Layout and mood concept | Generator / provenance | Selected direction / open question |
| --- | --- | --- | --- |
| Every planned mission | Linked board or explicit pending/deferral | Actual tool, workflow/model when available | What the human is evaluating |

Every core mechanic must be represented in the coverage table. A placeholder proves
only its actual behavior. Untested rows and deferrals remain visible with a reason,
the affected production work and the next test/decision. A failure is not a deferral
or a demonstrated mechanic. Do not convert optional GDD ideas into required features.

Prioritize shared player feel and equipment, then high-risk interactions and mission
transitions. For each, ask one question and define a bounded playable experiment.
Register only the next useful packets; the coverage table is not a giant execution
queue. Update it after each verified result. Workers receive the relevant row,
room, direct dependencies and evidence, not the full campaign transcript.

## Build foundations for the whole project

Apply the [shared-foundation rules for every phase](production-pipeline.md#shared-foundations-in-every-phase).
Pre-production establishes the record that production and post-production extend.

Build and prove the underlying systems that production depends on, with reuse guided
by the whole project scope. Before assigning implementation packets, group related
coverage rows by shared capability and inspect existing project/template assets.
In the same plan, record each foundation's known consumers, shared interface/assets,
role-specific variations, owning discipline and first playable proof. Pass the relevant
entry to each worker; separate room or mission packets must not independently reinvent it.

For example, squadmates and enemies may share character movement, navigation and
state components while using different decision logic. Player and squad equipment
may share attachment/action conventions and compatible animations, with perspective
or skeleton differences requiring explicit variants. Inspect compatibility before
promising asset reuse. Reuse may use components, interfaces, data or inheritance;
do not force every role into one class or assume all animations are interchangeable.

The responsible specialist identifies common behavior and intentional differences
across the known consumers. Build the smallest real foundation for the first consumer,
then exercise a second distinct consumer when reuse is a consequential design risk.
Defer unrelated behavior depth and polish. A scripted substitute can answer an isolated
design question, but cannot validate a shared foundation it bypasses: interpolated
markers do not prove character navigation. Record deliberate throwaway work, what it
proves and what must replace it before dependent production work. Do not build a
speculative framework for hypothetical consumers beyond the project scope.

## One level, several test rooms

Use one named prototype level as a sandbox by default. Prefer rooms or separated
zones within it over one map per mechanic or mission. Preserve the user's exact
canonical map name; L_Prototype is an example, not a rename instruction. Establish
the environment once, then extend its owned rooms. Do not recreate a working map.

Provide a simple hub or readable route, room labels and an entry/return path. Give
each room one experiment, scoped actors/state, clear start conditions and a replay
or reset action. Resetting one room must not accidentally complete another. Keep
progression independent except where a packet intentionally tests a cross-room or
cross-mission dependency. Use a recorded reset procedure if a local reset is not yet
implemented; mark the limitation in the handoff.

Room dimensions, station transforms and interaction reach belong to the layout
contract. Prefer references to owned actors/components over hard-coded world
coordinates so repositioning a room does not silently detach gameplay from props.
Use primitive geometry and equipment, but preserve the player action being tested:
holding/raising a camera, aiming at evidence, taking a photograph, or issuing an
order cannot be validated solely by entering a zone that flips an objective flag.
Match the specified camera/body perspective early, before evaluating other rooms.

Minimal scripted AI reactions can isolate command or state-design questions before
full production behavior. Use the real shared movement/animation foundation when
the experiment depends on moving characters. Label scripted stand-ins and their limits;
do not claim autonomous navigation or general decision-making from scripted success.
Technical research and offline simulations inform an experiment but do not replace
playable evidence inside the sandbox.

## Debug HUD and contextual guidance

Include a basic player-visible HUD or equivalent screen-space prototype UI in
pre-production. It need not be final art. Show the current room/objective, selected
equipment or relevant squad command, and a concise result or blocked reason. On
entering an interaction trigger or acquiring a valid target, show the actual bound
input and action, for example "Press E to photograph" or "Press Q to order Hold".
Choose inputs from the implemented bindings; these examples are not mandated keys.

Prompts describe actions available now. Resolve overlapping targets predictably;
clear/update prompts when the player leaves, changes target/tool, completes the
action or resets. If a prerequisite is missing, show that reason instead of a false
action prompt. Keep developer counters optional; do not expose implementation details
as the player's main instructions. World markers supplement the HUD, not replace it.

Verify the first complete input/UI/action/feedback chain at runtime before replicating
it across rooms. Check compiled input values and the placed runtime instance after
changing Blueprint defaults/components. Compilation and template readback alone do
not prove working input, visible prompts or correct placed instances. Exercise entry,
action, leave, re-entry, repeat protection and reset in a bounded smoke test. Where
automated input is unavailable, obtain actual human results rather than claiming pass.

## Concept coverage and presentation

Develop layout and mood concepts across the planned missions, not only the first
production mission. Use a small bounded concept packet for each distinct environment
or a useful grouped board. Start with one proposal per distinct mission environment;
iterate only to resolve an identified question. Allow one concept worker alongside
the single editor worker. Missing concepts remain explicit pending work or deferrals.

Honor any user-selected generator. Otherwise select an available suitable tool and
record its identity explicitly: ComfyUI-local versus built-in image generation, plus
model/workflow/seed when exposed, prompt, outputs and actual call/time observations.
Availability of ComfyUI does not prove it was used. Do not silently substitute another
generator when the local generation workflow is itself under evaluation.

Show the selected images directly in the human handoff, together with the actual
sandbox captures and a short explanation of what each proposes. Link the concept
index for the remaining boards. Reconcile scale, landmarks, equipment and perspective
with the playable rooms; concept art remains a proposal, never implementation proof.

## Scope-aware handoff into production

Keep the existing three states. Pre-production maps the whole game and tests its
foundation and important risks; production fleshes out the selected mission/slice;
post-production refines that integrated playable result. Do not require finished
versions of every mission before a focused production slice can begin.

Before requesting approval, present the sandbox tour, coverage table, runtime results,
debug UI, selected concepts, unresolved decisions and explicit deferrals. Say whether
the human is accepting a mechanic, a mission slice or the shared game foundation.
Name the production target and the shared systems it will consume. For each deferred
mechanic, state whether that mission depends on it and whether proceeding would
commit to an unproven design. Critical blockers remain blockers; non-blocking future
work may be accepted as an explicit deferral. Never label a partial proof as complete
gameplay coverage because all registered packets happened to finish.

Carry the accepted action/input/state contracts, reusable assets, layout constraints,
concept choices and tests into the production plan. Retain the sandbox as a regression
space. Production map selection is a separate explicit environment decision; extending
the sandbox does not authorize replacing it with a dressed mission. Create a linked
mission run when changing the target map so the helper's level contract stays truthful.

When broadening an earlier mission-only prototype, preserve its evidence and useful
assets. If the old pre-production phase is still unapproved, record a dated scope
amendment and add new packets in that phase; do not relabel earlier evidence as broader
validation. After approval, use a linked new pre-production iteration as described in
production-pipeline.md. A new conversation alone does not require a new map or a
from-scratch rebuild.
