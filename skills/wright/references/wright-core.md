# Wright core

Wright is a dev-time game-development harness named for Will Wright. It helps a
designer explore reactive systems by building small, observable changes. Preserve
the designer's choices; ground engine claims in evidence; prefer the smallest
useful experiment over speculative infrastructure.

The host (Claude, Codex, or another capable agent) supplies reasoning and tools.
Wright supplies environment contracts, work packets, evidence requirements, and
continuation state. The method and saved packet format are host-neutral. Host
adapters resolve real tool names and optional agent dispatch. Adding workers is a
choice based on useful independence. The main orchestrator acts as director across
pre-production, production and post-production, with user-reviewed phase handoffs.
Discipline workers are selected as needed within those states.

Across every phase and discipline, plan across the whole project, build shared
foundations, and specialize them for known uses. This includes code, animation,
materials, textures and VFX. Follow the shared-foundation guidance in
[the production pipeline](production-pipeline.md); small packets should extend a
coherent project foundation rather than accumulate isolated solutions.

## Four lenses

Use the lenses relevant to the decision. Record what is deliberately deferred.

- CORE ACTION: what the player does, what changes, what it counts toward, its
  threshold, and the observable feedback. First prove one action and one outcome.
- PROVISIONING: what the player must have or be able to cause from spawn. A callback
  existing in a graph does not establish that the player can reach it.
- ECONOMY: counts, costs, timers, rewards, and their variation. State concrete values
  or explicit playtest questions; avoid building the full economy ahead of its need.
- ADVERSARY AND EXITS: duplicates, abuse, failure, interruption, leaving, and recovery.
  Prioritize the cases that could invalidate the current experiment.

## Unit of progress

A work packet completes one observable behavior or resolves one uncertainty. It has
an explicit starting environment, allowed changes, dependencies, acceptance checks,
and a call/time budget. A large Blueprint can require many packets. Multiple small
files may belong to one packet when they are inseparable from a single behavior.

Plan, investigate, synthesize, execute, and validate are activities inside the work
loop, not a requirement to survey and design an entire slice first. Use a probe when
a capability is unknown; reuse evidence when its validity conditions still hold.
Save and verify at each logical boundary so interruption loses as little as possible.

## Grounding and ownership

Describe a live tool before relying on its signature. Query exact nodes/properties
when needed. Keep raw schemas as referenced evidence and give workers only relevant
subsets. Content queries record scope and time: absence from an incomplete snapshot
means unknown. A tool missing from one MCP survey is not proof that the engine or
host has no supported way to perform the action.

Before scene work, establish project identity, the intended level, and persistence.
A folder does not provide level isolation. New-slice work proposes an isolated test
level; modification of an existing level requires an explicit user choice. A setup
blocker remains a blocker until resolved, never an excuse to substitute another map.
If the user already prepared and selected the test level, validate and use it directly;
do not create a second one. Permission to reuse template assets does not include
earlier runs' generated gameplay, art or completion claims in a from-scratch test.

Report actual results with provenance. Static inspection, runtime testing, and
persistence are separate checks. A handoff describes what, why, exact steps, how to
verify, and what it unblocks. A completed packet is useful progress even when the
broader design remains unfinished.
