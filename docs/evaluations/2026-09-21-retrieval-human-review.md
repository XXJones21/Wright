# Retrieval pre-production: human review and design alignment

Captured 2026-09-21 from the user's partial sandbox playthrough and two attached
screenshots. This is a development-side feedback record, not a run-state update,
production approval, implemented fix, or independently reproduced defect report.

Run: `20260920-first-light-prepared-5e9adfd01e174004811b32c34a008461`.
Level: `/Game/Wright/codex_mission1-first-light/Level/L_Prototyping`.
The user considers the result good overall, with interaction, AI and presentation
details needing a design meeting before further implementation.

## Human observations and requested direction

| Area | Observation / direction | Next acceptance experiment |
| --- | --- | --- |
| Body-camera framing | The user accepts the higher, mid-screen pistol framing as appropriate for the intended body-camera presentation. Do not lower it to conventional FPS framing. This does not approve every aspect of camera motion or feel. | Preserve this reference while comparing lowered and raised equipment states in the actual gameplay camera. |
| Sidearm aiming | The user reports RMB is required to shoot, but there is no clear aiming transition. A simple raise would communicate the state. | Actual RMB visibly raises/aims; release lowers; LMB behavior agrees with the stated aiming rule. Do not silently add hip fire. |
| Camera | The placeholder appears attached to the player without a holding animation. Desired interaction: RMB raises/aims, LMB takes a photo instead of E. | Equip, raise, aim at a valid subject, photograph, receive feedback, lower, switch tools; check invalid targets and repeated input. |
| Sample kit | Same attachment/holding limitation. Desired use input is LMB instead of E. | Show a held tool and simple use feedback; LMB samples a valid target; tool switching cannot accidentally fire or photograph. Whether sampling also requires RMB remains a design detail to clarify only if needed. |
| Squad locomotion | Following only walks; evacuation is extremely slow. | Demonstrate walking, catching up at a run, and urgent movement with matching animation. Repeat with fear and injury; make any intentional limits and recovery readable. |
| Evacuation | User reports it does not work as expected. Exact failure path is not yet reproduced. | Reproduce using normal player controls; identify unmet predicates per survivor; complete evacuation and verify one relevant blocked case without diagnostic relocation or forced state. |
| Squad damage | Shooting squadmates did not visibly establish injury/death for the user. Existing forced/debug state checks do not settle this report. | Inspect collision, projectile instigator filtering, damage routing, health/state transitions and feedback. Demonstrate real projectile injury/death if friendly fire is the agreed rule; do not assume the root cause. |
| Fear / behavior | The user needs an accessible way to test and understand these systems. | Provide repeatable calm/fearful/injured scenarios and visible behavioral differences, command acknowledgment/refusal reasons and reset. Debug controls may supplement ordinary gameplay triggers. |
| HUD / menus | Current UI is diagnostic. User proposes a dedicated UI/menu specialist and a concept/design/implementation cycle for the first-person view. | Review a gameplay-screen proposal, implement a minimal readable version, then compare an actual capture. Keep developer details available separately; prompts must match real bindings. |

Screenshot references (original local attachments, not copied into the repository):

- `C:/Users/josh2/AppData/Local/Temp/codex-clipboard-89823c41-73cb-413a-9174-3e76ca86c980.png`: accepted pistol framing; evacuation blocked; both squad members fear 2 and obey slowly.
- `C:/Users/josh2/AppData/Local/Temp/codex-clipboard-ba7cbf98-6bad-4278-8042-53b9fe781b9f.png`: camera/sample placeholder attachment; injured technical member; protection prompt and dense diagnostic overlays.

The images corroborate displayed states and presentation. They cannot establish
input behavior, animation timing, damage routing or the cause of evacuation failure.
Fear/injury speed penalties are a hypothesis to investigate, not a diagnosed cause.

## Proposed shared contracts and bounded work

Preserve the working shared AI and stock pistol/projectile foundation. Extend a
shared equipment action contract for equip, held/lowered, raised/aiming, primary use,
feedback and interruption. Use compatible template poses/animations first; a simple
readable pose/raise is sufficient for a prototype. Do not build unrelated custom rigs.
Keep E for contextual world interactions where appropriate; primary tool actions
belong on LMB as requested. The chosen inputs must propagate to prompts and tests.

Suggested order, subject to the evacuation design decision:

1. AI programmer performs a bounded investigation of locomotion, damage and exit
   conditions, returning observed causes and a small repair sequence. Each issue
   gets its own playable acceptance check; this is not a single giant AI rewrite.
2. Gameplay programmer implements the agreed equipment action contract and visible
   state transitions, reusing the accepted pistol framing.
3. UI/menu specialist proposes the first-person composition, objective/action
   hierarchy, squad status/commands and actionable blocked feedback. Review the
   proposal before implementing its consequential design choices. Menu work is
   scoped to the test/replay flow actually needed, not a full front end by default.
4. Reviewer exercises the resulting input-to-outcome chains and a short integrated
   escape scenario. Record physical-input evidence separately from diagnostic tests.

The director supplies scoped context and reconciles interfaces. When dispatched,
new specialist workers use medium reasoning per the user's preference; the director
may retain high. Keep one editor owner at a time. Independent design/concept work
can occur alongside it; one editor owner need not mean the director does all work.

## Design meeting as a Wright workflow improvement

Proposed workflow change, not yet installed: before committing to consequential
player-facing interactions, the director presents a compact decision brief with
references, recommended inputs, visible behavior, important failure cases and open
choices. Use screenshots/concepts when framing or UI is the decision. Record user
decisions once and pass the contract to relevant specialists.

Do this during initial pre-production alignment and after phase playtests expose
new design questions. It is not a fourth production state or an approval request at
every packet. Settled choices and ordinary implementation remain autonomous; only
genuinely unresolved decisions hold dependent work. Continue independent authorized
work while the user is absent.

For this meeting, inputs and pistol framing are already directed by the user. The
main open question is evacuation intent: an explicit command sending able squadmates
running to the exit, following the player at a useful pace, or the existing protection
then extraction sequence with better explanation. An explicit Evacuate command is
the current recommendation, not an approved requirement.

## Review disposition

Implementation completion is retained as historical evidence. This human feedback
leaves evacuation, squad damage behavior, locomotion and revised equipment input
acceptance unresolved. Do not preserve an unconditional player-experience pass for
those behaviors on the strength of earlier diagnostic checks. Do not relabel a
reported failure as mere polish or an accepted deferral.

Repair and re-review the relevant pre-production experiments before requesting
approval, or present specific deferrals and their production dependencies for an
explicit user decision. Preserve the original evidence and distinguish new results.
