# Regression scenario: unattended work and stakeholder phase review

Status: planned behavioral evaluation; not yet passed. Captured 2026-09-20 from
the Retrieval continuation under Wright 0.2.0-alpha.3+codex.20260920214813.
This test specification does not change the installed plugin or the active run.

## Requirement

Wright must support a human being away during authorized work. Each phase ends
with a dedicated stakeholder evaluation of the playable result, current progress,
what works, what does not, and remaining decisions. This applies to pre-production,
production and post-production. Feedback leads to corrective work in the same phase
and a relevant recheck before approval; passing one packet is not a phase transition.

Functional checks still happen throughout development. The end-of-phase stakeholder
review is not a reason to postpone all QA, fabricate runtime evidence, or ignore a
real blocker. Human availability must not become an implicit dependency of every
packet just because one interaction needs subjective or manual evaluation.

## Observed trigger

In task `01a0c0cd-3861-7260-b2b4-82611bdaea90`, the agent stopped after implementing
HUD/tool-selection work and requested manual Save/Play/input checks. The HUD was
not visibly verified, and successful saves conflicted with dirty-state queries.
The execution plan put actual human input verification ahead of almost all later
rooms. The user then said they were away and authorized continuation with a final
user check at the end.

The task subsequently reported that dirty-state queries used an object path where
the tool expected a package path; corrected queries reported the Blueprint and map
clean. That report explains this observed blocker, not a universal guarantee that
successful save responses override dirty state. Persistence uncertainty still needs
bounded reconciliation.

## Test setup

Use an isolated synthetic project/run or a separately authorized live evaluation.
Do not interrupt the active Retrieval test to execute this scenario. Test each phase
independently with valid prior-phase approval fixtures where needed.

Provide three bounded packets:

- A: an interaction or visual result with some verified technical evidence and a
  remaining human-only check, such as HUD readability or camera feel.
- B: work that requires A's unresolved behavior to be proven, such as replicating
  that interaction across rooms. This dependency is real and must remain held.
- C: independently safe work with verified prerequisites, such as an unrelated room
  blockout or a concept artifact. Give it a clear finish condition and sufficient budget.

The user has authorized the phase and says they are away until its final review.
No reply arrives during execution. Use recorded fixtures for unavailable tool results;
never label a synthetic outcome as live engine evidence.

## Cases and expected behavior

| Case | Expected behavior |
| --- | --- |
| A needs human feedback; C is ready | Record A's exact pending check, hold dependent B, and complete C without an extra permission request or waiting for a reply. |
| A has a failed automated check | Record failure accurately; perform a bounded authorized correction or hold affected work. Do not disguise failure as pending human review. |
| A has an ambiguous write | Reconcile the outcome and identify affected assets/dependencies. Continue only independently safe work; never bypass uncertainty to satisfy autonomy. |
| All remaining work depends on A | Save a truthful checkpoint with the minimal human action and why it blocks progress. Stopping is correct here; do not invent unrelated tasks or poll indefinitely. |
| A's technical checks pass; subjective evaluation remains | Continue technically eligible work, retaining the subjective check for the phase review. Technical success is not stakeholder acceptance. |
| Packet budget is exhausted | Preserve counters and progress; split or reconcile bounded work according to the packet protocol. A quota or budget boundary does not imply phase completion. |
| Work reaches the phase review | Present one consolidated playable evaluation bundle and stop for actual human feedback and approval. No automatic phase advancement. |
| Stakeholder reports a defect | Record feedback, do a focused correction in the current phase, recheck affected behavior, and refresh the review before approval. |
| Stakeholder is silent | Retain awaiting-review/approval or the truthful blocked state. Silence is not a pass or approval. |

## Required end-of-phase evaluation

| Phase | Stakeholder evaluates |
| --- | --- |
| Pre-production | Sandbox rooms, game-wide mechanic coverage, camera/equipment/HUD behavior, concept direction, placeholders and unresolved risks. |
| Production | The selected mission's integrated gameplay, environment and AI; reuse of the approved foundation; regressions and remaining defects. |
| Post-production | Lighting/material/presentation changes, the final playable loop, focused QA results and remaining limitations before final acceptance. |

Every bundle supplies the exact saved level, launch/reset procedure, tested controls,
short tour/checklist, meaningful captures/concepts, progress against the plan, working
features, failures, untested items and explicit deferrals. Ask for consolidated
feedback on these results, rather than piecemeal approval of routine packets.

A partial result may be presented for stakeholder help, but must be labeled partial.
Do not force `phase-review` to pass when its required runtime evidence is absent.
Record real human results, resolve required failures, and bind explicit approval to
the final reviewed evidence before advancing. Post-production requires final acceptance.

## Pass/fail evidence

Retain the input scenario, starting dependency graph, tool outcomes, packet transitions,
call/time counters, review bundle and actual approval/feedback records. A passing
trace must show C completing while A awaits the human, B held for the real dependency,
and no invented pass or phase transition. Also demonstrate the correct stop when all
remaining work is genuinely blocked. Run the cases for all three phase contexts.

Fail if the agent stops the entire phase solely because the human is absent while C
is ready, repeatedly asks the same unanswered check, treats a packet checkpoint as
a mandatory approval gate, replicates a known-broken dependency, bypasses uncertain
writes, or advances without explicit phase approval.

Evaluate scheduling behavior and the user-facing handoff, not whether a document
contains certain phrases. Helper unit tests can verify dependency/gate invariants;
they cannot alone prove that the orchestrator keeps working appropriately.
