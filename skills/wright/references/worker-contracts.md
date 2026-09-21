# Optional worker contracts

The default is one capable host agent working through bounded packets. Use a separate
role only when it reduces context, enables independent research, or adds useful review.
The host orchestrator is the director. Select discipline briefs and phase gates from
[the production pipeline](production-pipeline.md); there is no separate director worker.
Every dispatch contains the environment binding, packet spec, current progress, relevant
dependency summaries, evidence paths, and allowed operations. Workers do not read the
entire mission plan or edit run.json directly.
Include the active phase, selected role and lane. For shared systems, include the
relevant foundation entry: known consumers, existing assets,
interfaces, owning discipline and allowed variations. Return interface conflicts to
the director before creating a parallel implementation. A concept worker receives mission
constraints and only its owned output directory; it has no editor access. The director
can run it beside one editor worker and publishes both results through the helper.

## Capability probe

Resolve the packet's named uncertainty with scoped reads. Describe before calling;
record exact query scope and outcomes. Return supported, unsupported, or still unknown
with evidence. No live mutation in a probe. If the answer requires a write, identify
that as a separate change/setup operation rather than expanding read-only scope.

## Reference research

Answer the one design question supplied. Provide alternatives and trade-offs grounded
in the named game/project references. Do not survey every design lens or choose the
final design on the designer's behalf. No editor access is required.

## Change worker

Include actual executor identity and measurement expectations in the brief. Return
the [execution metrics](execution-metrics.md) alongside the outcome; role names alone
do not establish delegation. The director records its own integration/review effort
separately. Apply this to concept, research and review packets as well as editor work.

For editor-lane work, implement the packet outcome inside the verified target level and allowed changes.
Recheck project/level/PIE immediately before mutations. Only one worker holds the editor.
Record created or modified object references as they occur. Inspect the current schema
and relevant read-backs, not a full raw API dump. Use the Blueprint or texture playbook
only when needed.

Measure cumulative tool calls and elapsed time. After each logical unit publish a
progress checkpoint through the conductor: changed objects, last result, next action,
and uncertain writes. At the packet budget stop starting new operations; settle the
one in flight, save what can be saved within scope, and hand off. A timeout does not
prove a write failed. Never replay a create without checking existing state.

Verify acceptance checks individually. A failed call remains in the evidence with its
correction; do not erase history. An asset-only task does not require staging a viewport
object just for a screenshot. Confirm persistence before dependent scene expansion;
a save-all affecting unrelated dirty assets is outside the owned save scope.

Return concise outcomes, actual tool observations, evidence files, call/time metrics,
and remaining work. A compiled graph is static evidence; record runtime NOT RUN until
an actual test occurs. An unknown persistence route blocks completion of a change.

## Independent review

Review the current packet definition and result, relevant dependency evidence, and
fresh targeted observations if needed. Check acceptance coverage, ownership, persistence,
and whether runtime claims are supported. Do not require research and an independent
reviewer on every mechanical edit. Novel mechanisms and changes to shared behavior are
stronger candidates. Report concrete gaps and their owner; do not silently implement fixes.

## Handoff

For unavailable operations, return what to do, why the available tools cannot currently
do it, exact steps or required input, how to verify, and which packet it unblocks.
Do not mark a behavior complete because a handoff was written. The conductor records
blocked/paused state with the specific next action.
