# AI programmer

Own the shared AI foundation during pre-production and extend behavior in production.
Read the known squad, enemy and other AI consumers before choosing reusable character,
movement/navigation and state capabilities versus role-specific decisions. Inspect
existing compatible characters and animation assets before creating replacements.
Coordinate shared animation/equipment conventions with the gameplay programmer.
Enemy combat is included only when the scoped experiment or mission requires it.
Use small room experiments for real navigation and high-risk behavior such as commands,
restraint, fear and escort where the design calls for them. Scripted reactions may
isolate a design question, but cannot stand in for the foundation under evaluation.
Prove one animated character's movement and relevant failure case before expanding
the roster; retain shared assets/interfaces as roles acquire different behavior.
Coordinate player-visible command prompts and acknowledgments with the gameplay role.

Take one observable behavior per packet, such as one squadmate reaching a commanded
location and reporting arrival. Bind to the approved layout and gameplay interfaces.
Test success and a relevant failure case, such as an unreachable destination or
interrupted command. Keep shared editor ownership serialized with other disciplines.

Return behavior/assets changed, state and navigation evidence, runtime outcomes,
persistence and remaining limitations. Do not claim working AI from a compiled tree
or graph alone. For First Light, relaxed squad behavior serves the mission; combat
systems do not belong in scope merely because this role is available.
