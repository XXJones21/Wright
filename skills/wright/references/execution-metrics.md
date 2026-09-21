# Execution metrics for every phase

Record who actually did the work, independently of the packet's discipline role.
An orchestrator adopting the AI-programmer brief is still the orchestrator; only an
identified separately spawned worker counts as delegated execution. The director
uses these measurements to assess direct implementation, coordination, verification
and rework. Do not optimize a delegation percentage at the expense of useful outcomes.

At normal progress/finish checkpoints, include an `execution` object in the evidence
document, or maintain `metrics/<packet-id>.json` as an additive run-local report. The
dashboard supports either; the separate report takes precedence. Update it atomically
and keep counters cumulative per executor for that packet, including resumed work.
These reports are operator evidence, not automatic interception of engine calls.
Keep existing packet budget counters authoritative; do not rewrite old immutable
results to retrofit attribution or change their call-counting convention.

```json
{
  "schema_version": 1,
  "coverage": "partial",
  "call_unit": "underlying_tools",
  "reuse_decision": {
    "decision": "unknown",
    "candidates": [],
    "reason": "Inspect the supplied functional feature before selecting reuse, adaptation or new implementation."
  },
  "delegation_reason": "Director owns editor integration; worker authors the bounded component and returns evidence.",
  "executors": [
    {
      "kind": "subagent",
      "id": "actual-worker-task-id",
      "role": "ai-programmer",
      "model": null,
      "reasoning_effort": null,
      "measurement": "unknown",
      "tool_calls": null,
      "implementation_calls": null,
      "verification_calls": null,
      "coordination_calls": null,
      "retry_calls": null,
      "active_seconds": null,
      "wait_seconds": null,
      "input_tokens": null,
      "cached_input_tokens": null,
      "output_tokens": null,
      "reasoning_output_tokens": null,
      "evidence": []
    }
  ],
  "limitations": ["Example only; replace with actual identities and available measurements."]
}
```

- `coverage`: complete only when all participating executors are accounted for;
  otherwise partial. Missing reports mean unknown, not orchestrator-only or zero.
- `kind`: orchestrator, subagent or human. Include director integration/review effort
  alongside worker effort; never count child calls again under the director.
- `reuse_decision`: reuse, adapt, new, mixed or unknown; name inspected candidates and
  why the choice fits. Consider the supplied mechanics and assets together. A stock
  mesh on newly duplicated logic is not full feature reuse. This decision explains
  avoidable rework; it is not a synthetic reuse score.
- `measurement`: measured, estimated or unknown. Cite the counter/timestamp/log source
  and explain estimates in limitations. Record actual observed model/reasoning; an
  intended dispatch setting is not proof of the worker's resolved setting.
- `call_unit`: underlying_tools, host_requests or unknown. Underlying tools exclude
  orchestration wrappers; host requests include wrappers. Keep units consistent within
  a report and do not combine unlike units into a delegation ratio. Activity categories
  are nonoverlapping subsets of total calls; retries are an additional subset.
- Unknown counters are null. Active versus waiting time needs actual timing evidence;
  wall time does not establish model compute time. Concurrent worker durations are
  effort totals, not additive project wall time. Preserve failures/retries and budget
  overruns even when the final result passes. Use existing acceptance evidence for
  outcomes, failed checks, persistence and rework rather than inventing quality scores.
- Tokens belong to their actual response/packet scope. Cached input is a subset of
  input, and reasoning tokens a subset of output. Do not sum cumulative checkpoints,
  copied parent history or parent/child aggregate totals. Report cost only when an
  actual provider cost is available; never infer account usage from raw token totals.

Keep planning/dispatch overhead outside a packet in a separate run-overhead report
with its actual scope, rather than charging it to several packets. Do not reconstruct
unknown history by expensive manual counting. A concise explanation of direct execution
or delegation is more useful than a mandatory new worker per small action. Supply
delegated workers with the outcome, context, shared interfaces, constraints and checks.
Honor the user's model/reasoning choices for the orchestrator and task workers;
record those session choices in the brief rather than assuming a universal default.

The optional dashboard `--session <rollout.jsonl>` view measures host requests and
unique response token records from explicitly configured Codex sessions and discovered
child sessions. It does not export transcripts or assign session totals to packets.
Treat its scope as narrower than the whole run unless all relevant sessions are included.
System approval reviewers are not specialist task workers. Historical role labels,
file timestamps and elapsed execution windows alone cannot prove worker ownership.
