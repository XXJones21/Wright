# Shared work-packet protocol

This protocol is host-neutral. Claude/Codex provides tools and execution; Wright's
stdlib helper stores bounded work and checks its recorded evidence. It does not
create levels, execute tools, authenticate connections, or prove an agent's claims.
Production phases, role selection and user approval follow
[production-pipeline.md](production-pipeline.md). New runs start in pre-production.

At normal checkpoints, capture [executor metrics](execution-metrics.md): who performed
the task, observed model/reasoning, work categories, retries, timing and available
usage counters. Keep measured values, estimates and unknowns distinct in every phase.

## 1. Establish environment

Resolve the selected absolute `.uproject` (or an explicit project directory with one
`.uproject`). Decide the intended map. For new pre-production establish one named
prototype sandbox, then use its rooms for the experiments across the game. For a
new standalone slice propose a distinct test map;
do not silently build in the current level. Existing-level work needs an explicit
user choice and a reason recorded by `--existing-level-reason`.

A level the user prepared specifically for this test is an explicit existing-level
choice. Use it directly, verify its canonical package path and saved state, and record
the user's selection as the reason. Skip level creation, duplication and Save As.
Package paths may contain hyphens; use the engine-resolved exact path, not an inferred
folder spelling or an old redirector. A fresh run is still required, with independent
mission assets and evidence. Record which default/template assets can be reused and
which earlier-run namespaces and artifacts are excluded from this evaluation.

```text
python <plugin>/scripts/work_packets.py init --project <absolute-project> --task evidence-test --target-level /Game/Wright/EvidenceTest --level-mode isolated --setup-tool-calls 20 --setup-minutes 5
```

Quote absolute paths. `--task` is a short filesystem-safe slug. Init returns the
unique run directory; the subsequent examples use `<run>` for that absolute path.
Optional project configuration stays at `<project>/wright/config.json`; see
`profiles/wright.project.example.json`. Helpers write only run/project-local data.

The environment contract is initially unverified. The first bounded prerequisite
is a supported route to create/open and persist the intended map. Inspect the
available host/engine capabilities. Before any setup mutation, establish connected
project identity and check whether the requested target already exists. In isolated
mode a pre-existing level cannot be claimed as newly created for this run. Choose a
fresh target or obtain the user's explicit existing-level choice; do not overwrite it.

Setup may create/open only the named target and owned setup objects within the user's
scope. Record each result promptly with `setup-progress`; setup has its own cumulative
budget because it precedes normal change packets. Write its evidence JSON inside the run:

```json
{"phase":"paused","proof":["findings/setup-readback.json"],"tool_calls":4,"elapsed_seconds":60,"objects":["/Game/Wright/EvidenceTest"],"next_action":"Inspect whether the level save completed before attempting another write.","uncertainty":true}
```

```text
python <plugin>/scripts/work_packets.py setup-progress --project <project> --run <run> --evidence <absolute-setup-json>
```

`phase` is running, paused or blocked; blocked requires `blocked_reason`. Stop on the
first uncertain write, exhausted setup budget or unsupported save route. Provide an
exact setup handoff. Status/resume includes this checkpoint. After an interruption,
inspect live state and use `setup-reconcile --evidence <absolute-reconciliation-json>`
with the usual `--project` and `--run` arguments. Reconciliation supplies `reason`,
`proof`, `objects`, `next_action`, `uncertainty:false`, and an optional additive
`budget_extension`, as in section 5. Never clear uncertainty without inspecting it.

Do not build scene content in another map while waiting. The helper does not automate
setup. After setup, record a JSON environment observation under the run with:

- `observed_project`: exact selected absolute `.uproject` path;
- `observed_level`: exact target package path;
- `level_created_for_run`: true only with actual provenance for isolated mode;
- `persistence_verified`: true only with independent persistence evidence;
- `evidence`: nonempty run-relative paths to observations supporting these claims.

```text
python <plugin>/scripts/work_packets.py environment --project <project> --run <run> --evidence <absolute-observation-json>
```

Keep source evidence files intact; the helper fingerprints recorded evidence. Recheck
the actual editor project and map immediately before writes and on session/model
changes. File integrity does not establish that the editor stayed on the same map.
If the project/map binding is unchanged, record that fresh inspection in the packet's
reconciliation proof; do not replace the setup observation merely to log another read.
An environment refresh that changes the binding invalidates dependent assumptions,
including probe results. A pre-setup probe can answer its immediate question, but must
be reconciled and reverified after setup before serving as a completed dependency.
Once setup is verified, subsequent editor changes belong to normal packets.

## 2. Define only the next useful work

First map the GDD and user decisions in a compact run-local PLAN.md using
[preproduction-planning.md](preproduction-planning.md). Keep all mission mechanics
and concepts visible there; register only the next bounded room experiment. A room
is an owned area of the same contracted level, not a new environment per packet.

Write a JSON spec inside the run. A packet is a single observable outcome or a single
question answered. The example spec in `examples/01-evidence-state.json` shows the
shape; adapt its object paths, budgets and acceptance to the actual request.

| Field | Contract |
| --- | --- |
| id | Stable filesystem-safe identifier; do not repurpose it. |
| kind | probe (no mutations) or change (editor changes require verified environment). |
| phase | pre-production, production or post-production; defaults to the current phase when registered. |
| role | layout-artist, gameplay-programmer, ai-programmer, environment-artist, lighting-artist or reviewer; defaults to gameplay-programmer. |
| lane | editor (default) or concept; concept requires environment-artist and permits only owned run-local files. |
| outcome | One concrete result. |
| depends_on | Existing completed packet IDs whose evidence this work uses. |
| allowed_changes | Exact permitted objects/surfaces; empty for a probe. |
| checks | IDs and descriptions, optional kind static or runtime. |
| budget | Positive tool_calls and minutes; initial estimates, not guarantees. |

```text
python <plugin>/scripts/work_packets.py add --project <project> --run <run> --spec <absolute-spec-json>
python <plugin>/scripts/work_packets.py start --project <project> --run <run> --packet evidence-state
```

The spec becomes an immutable definition. An editor change requires verified environment
and completed dependencies with intact evidence. Only one packet per lane may be running.
Future-phase work can be queued but cannot start until user-approved advancement.
Concept changes can run before editor setup; their `allowed_changes` must be paths
under `concepts/<packet-id>/`. A successful concept change also supplies an `outputs`
list of actual saved run-relative files within those paths. The helper hashes those
files. Concept packets never authorize editor calls or project asset imports.
For broad missions keep a short backlog in ordinary notes; do not pre-design every
detail or register eight oversized artifacts. A changed outcome gets a new packet ID.

Work toward a functional chain first: one test object, reachable input/targeting,
one state change, repeat protection, and a tiny completion outcome. Split these when
their implementation/discovery exceeds a budget. Do not define an entire director's
variables, timers and economy before proving its first action. Art-first tasks are
appropriate when visual design is the actual objective.
Include contextual HUD feedback and the specified player/tool action in that first
chain. Verify actual input and the placed runtime instance before replicating it;
static-only completion must not be mistaken for demonstrated gameplay coverage.

## 3. Execute with bounded context

Load the packet report, environment summary and direct dependency results. Full API
schemas, research and logs are linked evidence loaded only when required. Avoid a
growing global plan as mandatory worker input. Discover only relevant actor sets,
properties or node types. Cache findings with server/version/project/object scope;
revalidate on version, graph structure, project or level changes.

Use the optional roles in worker-contracts.md as needed. A normal packet need not
spawn agents or write research findings. Only parallelize work independent of editor
access. Preserve exact tool-call observations in compact local evidence; helper
commands and filesystem/research tools count toward model-visible calls too.

After each logical unit write progress JSON inside the run:

```json
{"tool_calls":12,"elapsed_seconds":180,"objects":["/Game/Wright/EvidenceTest/BP_Evidence.BP_Evidence"],"next_action":"Read back the logged state and save the owned asset.","uncertainty":false}
```

```text
python <plugin>/scripts/work_packets.py progress --project <project> --run <run> --packet evidence-state --evidence <absolute-progress-json>
```

Counters are cumulative for the packet, including retries. At a budget boundary do
not start another operation. Settle an in-flight call and checkpoint partial objects.
Uncertain writes pause the packet. Two failures of the same operation without new
evidence require rescoping or a concrete handoff. Do not loop on save/dirty-state checks.

## 4. Verify and finish

Finish JSON supplies exactly one result for each acceptance check, measured counters,
persistence and runtime status. Evidence paths are run-relative nonempty files:

```json
{
  "checks": [{"id":"state-readback","status":"pass","evidence":"findings/state-readback.json"}],
  "persistence": {"status":"verified","evidence":"findings/save-proof.json"},
  "runtime": {"status":"not_run"},
  "tool_calls":18,
  "elapsed_seconds":240
}
```

This illustrates structure only; supply every check from the actual spec, including
`compile` when using the example spec. Never manufacture pass evidence. A probe can use
`persistence.status: not_applicable`. A change cannot. Record a failed or unverified
save with `persistence.status: failed` or `unknown` and supporting evidence; the
result stays blocked. Runtime pass/fail requires an
evidence file; a passed runtime-kind check also requires runtime pass. Blueprint
compilation is a static check. Where automated runtime execution is unavailable or
outside scope, use an explicit operator test and record its result. Otherwise the
runtime packet remains blocked, not implicitly passed.

```text
python <plugin>/scripts/work_packets.py finish --project <project> --run <run> --packet evidence-state --evidence <absolute-result-json>
```

The helper fingerprints results, checks acceptance coverage, environment/dependencies,
and persistence. Failure is blocked. A valid result can finish after crossing a soft
budget and records the overrun; that does not justify starting another oversized packet.
A packet paused only for its budget can finish with already-gathered evidence. If
finalizing evidence adds helper/file calls or time, report the increased counters
and `no_new_engine_work:true`; this declaration permits accounting overhead only.
Further engine work requires reconciliation and sufficient remaining budget.
Successful packets can continue automatically within the active phase and user's requested scope.
Report completed outcomes separately from broader mission completion. The helper's
`registered_packets_complete` is never a claim that an entire game or mission is done.

## 5. Resume and reconcile

```text
python <plugin>/scripts/work_packets.py resume --project <project> --run <run> --packet evidence-state
```

Status/resume is read-only and compact, including the setup checkpoint, queue summaries,
observed objects and next action from the latest verified progress or reconciliation.
A running/paused packet is not automatically
restarted. Inspect its objects and any operation with uncertain outcome. Check the
live environment. Then write reconciliation JSON with `reason`, `proof` (run-relative
evidence files), `objects`, `next_action`, and `uncertainty:false`. Optional
`budget_extension:{tool_calls:10,minutes:3}` adds explicitly justified capacity;
it preserves consumed totals. Do not treat quota resets as permission to reset budgets.

```text
python <plugin>/scripts/work_packets.py reconcile --project <project> --run <run> --packet evidence-state --evidence <absolute-reconciliation-json>
```

If it should instead be split, leave the partial packet paused/blocked and define a
new narrow outcome with explicit references to inspected partial objects. Do not
claim the unfinished predecessor as a completed dependency. Retain the pending work
in the final report; never hide it to obtain an all-complete status.

## Existing runs and legacy helpers

Packet mode is explicit (`workflow: packets-v1`). Never convert or resume the stopped
Claude baseline implicitly. `run_state.py`, `gates.py`, the large plan template, and
legacy role files remain for inspection/testing of old runs. Packet runs use the
commands above; legacy register/checkpoint/gate operations cannot mark them complete.
No plugin install, engine action, model switch, or usage reset is performed by these helpers.
Pre-pipeline packet previews without `pipeline` state also require a new run, not
an inferred approval. Phase-review, phase-approve and phase-advance commands are
documented in production-pipeline.md; resume never advances a phase automatically.
