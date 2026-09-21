# Interrupted Claude evaluation: 2026-09-20

Observed interval: 10:08:09 to 11:33:04 PDT (about 85 minutes).
Source run: `D:\UnrealProjects\Retrieval\wright\runs\20260920-mission1-first-light-build`.
Source plugin baseline: `43783a8e0ee08ba288710401d907f9e016fd31ef`, version 0.1.2.

The user reported a session limit on a 2x Pro account. The logs record a limit at
11:25:43, a reset notice at 11:31:14, resumed executor activity, then an out-of-usage-
credits result at 11:33:03-04. This review did not resume Claude, run a gate, contact
Unreal/ComfyUI, or alter the source run. Activity continued while it was inspected;
the cutoff is an observation boundary, not proof of a permanently stopped session.

## Observed output

Eight tasks were planned. Four artifact reports exist: marker materials, site
geometry, scorch textures/material, and BP_EvidenceItem. Their Unreal call ledgers
contain 50, 102, 50, and 52 rows. These are reports, not freshly verified editor state.
The current plan was 239,700 bytes. No Gate, post-build GPS, Validation, or Close
section had been produced by the observation cutoff.

Task 5 (BP_MissionDirector core) is partial. Its worker made 122 logged tool calls;
the last written function was Radio180, followed by a compile with a null result.
No task-5 artifact or save_assets call was present in that worker log. Tasks 6-8
have no artifact reports. No StartPIE call was logged in the measured build interval.

The site-dressing report explicitly marks four actors NOT PERSISTED (artifact 02,
line 48). Save-actor and external-package attempts failed; a level-save response did
not establish changed files. It warns of loss on editor close. Current persistence
must be checked by the operator or a separately authorized live inspection before
closing or relying on those actors. The item Blueprint report records compilation
and saving but no placed instance (artifact 04, lines 6 and 56 onward).

## Logged metrics

| Metric | Observed total |
| --- | ---: |
| Distinct tool-use IDs | 713 |
| Explicit is_error results | 16 |
| Output tokens | 346,624 |
| Uncached input tokens | 6,680 |
| Cache creation input tokens | 1,864,332 |
| Cache read input tokens | 36,391,270 |

Cache reads are repeated context processing, not unique source content. These sums
are log metadata, not subscription consumption, pricing, or account-limit estimates.
The counts exclude MCP calls hidden within shell helpers and unflagged error strings.

The conductor and workers contributed 40 / 196 / 17 / 73 / 123 / 72 / 70 / 122
calls respectively (conductor, engine investigator, reference investigator, executors
1 through 5). Executor 5's last successful request included 204,291 cache-read input
tokens. The engine investigator made 55 get_actor_bounds and 42 get_label calls;
executor 5 made 23 find_node_types and 30 get_node_type_pins calls.

## Reproduction and evidence

[snapshot.json](snapshot.json) records per-log metrics, the measured interval, capture
time, and SHA256/size/mtime for every file in the source run. Raw conversation logs
are not copied into the plugin repository.

Main source log:
`C:\Users\josh2\.claude\projects\D--UnrealProjects-Retrieval\00041cb2-faec-43b9-8a4b-cabf2aa23b76.jsonl`.
Relevant lines: 1001-1002 initial limit; 1007 reset notice; 1009/1018 resume;
1026-1027 credits failure. Task 5's worker log lives in the matching session's
`subagents/agent-awright-exec-05-608841eeeb5470af.jsonl`: 335-340 last write/compile;
343 credits failure.

Counting method: read JSONL as data, include timestamps from
2026-09-20T17:08:09.144Z through 2026-09-20T18:33:04.350Z inclusive. Include the main
session, second-run investigators (`*-inv-2-*`), and build executors (`*exec-*`).
Deduplicate assistant usage by message.id, retaining the record with the largest
output_tokens value; sum the four top-level usage fields. Deduplicate tool invocations
by tool_use.id and flagged errors by tool_use_id. The parent review independently
recomputed the totals reported here.

## Changes this evidence motivates

1. Scoped worker packets and task-relevant schema/node discovery instead of reading
   the entire growing plan. Preserve raw evidence as links, not repeated context.
2. Build and persist one functional action-to-outcome milestone before optional art
   and scene expansion. Prove the owned actor persistence route early and bound retries.
3. Split the director into saved, independently inspectable units. Record partial
   objects and the exact next action before another large tool sequence.
4. Treat task coverage, current revision hashes, and incomplete evidence as gate
   conditions. A subset of successful artifacts is not completion of the requested run.

This is an interrupted baseline. No Codex performance improvement has yet been measured.
The next live comparison should use an equivalent project starting state and task;
do not reuse the modified Claude level as though it were the same starting state.
