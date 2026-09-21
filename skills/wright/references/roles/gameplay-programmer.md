# Gameplay programmer

Use for player interaction, feedback, evidence collection or mission progression.
In pre-production, prove the smallest reachable action-to-outcome loop, including
repeat protection. Use the game-wide coverage row to choose a small sandbox-room
experiment; prototype the specified camera perspective and visible equipment actions.
In production, extend only the mechanics in the approved mission/slice scope.

Inspect the project's shared-foundation plan before implementing a local mechanic.
Identify player, squad and enemy consumers of equipment actions, animation and state;
reuse compatible assets and shared interfaces with role-specific variations. Agree
ownership and animation/equipment conventions with the AI role so a player-only
implementation does not become a second independent system when NPCs need it.

Read the packet and relevant engine schemas/Blueprint playbook. Keep each change
observable: input reaches the intended object, changes state once, gives feedback
and contributes to the expected objective. One Blueprint can span several packets.
Use temporary stand-ins for unrelated systems rather than building them speculatively;
label those stand-ins and their replacement requirements in the handoff.

Implement the basic debug HUD/contextual interaction prompt as part of the first
player-action chain. Show the actual input, target/action, prerequisites and outcome;
clear or update it on exit, completion, equipment changes and reset. A primitive held
tool can demonstrate documenting or collecting; a differently named proximity flag
does not demonstrate tool use. See preproduction-planning.md for the UI contract.
Read back compiled bindings and placed runtime components, and prove one real input
chain before extending it. Keep room state/reset isolated unless testing a dependency.

Return affected graphs/assets, compilation and persistence evidence, and actual
runtime results or NOT RUN. A function present in a graph is not proof that a player
can invoke it. Coordinate squad behavior through explicit interfaces with the AI role.
