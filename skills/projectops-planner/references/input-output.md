# Offline planner contract and release notes

The bundled CLI runs on Python 3.12+ using only the standard library. It accepts
one existing UTF-8 JSON file, or `-` (the default) for standard input, up to
65,536 bytes. Duplicate JSON object fields and nonfinite numbers are rejected.
It writes one result JSON document to standard output on success (exit 0).
Expected read/validation errors go to standard error without input contents or
file paths (exit 2). It does not access the network or launch subprocesses.

## Input

The root object has exactly `as_of`, `work_windows`, `busy` and `tasks`.

| Field | Required value |
| --- | --- |
| `as_of` | Explicit planning timestamp; not automatically the current time. |
| `work_windows` | List of `{ "start": timestamp, "end": timestamp }` objects. |
| `busy` | List of the same interval objects, explicitly supplied by the caller. |
| `tasks` | List of task objects defined below. |

Each task has exactly `id`, `title`, `deadline`, `estimate_minutes`, `priority`.
IDs are unique nonempty strings without surrounding whitespace. Titles are
nonempty strings. Estimates are positive integer elapsed minutes. Priority is a
nonnegative integer; larger numbers win only when deadlines tie. Boolean values
are not accepted as integer estimates or priorities. Empty lists are valid.

All timestamps use ISO 8601 with `T` and `Z` or a numeric UTC offset such as
`2026-11-16T09:00:00-08:00`. Resolve named zones and ambiguous local times before
calling the CLI. Every interval's end must be after its start in elapsed time.
The offline CLI does not verify the caller's `as_of` or `busy` against a clock or
Calendar. Missing values must be clarified rather than guessed.

## Algorithm and output

The engine merges overlapping/adjacent windows and busy intervals, clamps work
to `as_of`, and subtracts busy time. It orders tasks by earliest deadline, then
larger priority, then lexical ID. Each task receives the earliest remaining
contiguous block that fits before or exactly at its deadline. The result is
deterministic; identical input yields identical output without reading a clock.

The returned object includes:

- `kind: deterministic_planning_result` and `execution: planning_only`.
- `algorithm: earliest_deadline_first_nonpreemptive` and UTC `as_of`.
- `schedule`: suggested blocks, ordered by start time and task ID. Each includes
  `task_id`, title, deadline, estimate, priority, status, UTC start and UTC end.
- `unscheduled`: tasks with `status: not_scheduled` and either
  `deadline_not_after_as_of` or `no_contiguous_slot_under_heuristic`.
- A note explaining that this is calculation without changes to external state.

Tasks are never split. This is a greedy heuristic; an unscheduled task is not
proof that no alternative allocation exists, and the result is not claimed to
be globally optimal. No tasks are saved and no Calendar events are created.

## Reproducible synthetic example

`examples/planner_input.json` uses a fixed planning time on November 16, 2026,
two fictional work windows, two fictional busy intervals and four tasks. It
does not read the user's current time or connected Calendar.

Expected chronological suggestions, in the fixture's explicit UTC−08:00 offset:

| Task ID | Suggested block | Same block in UTC |
| --- | --- | --- |
| `demo-prepare-review` | 09:00–09:45 | 17:00–17:45Z |
| `demo-check-evaluation` | 10:30–12:00 | 18:30–20:00Z |
| `demo-draft-follow-up` | 13:00–13:30 | 21:00–21:30Z |

`demo-long-report` is deferred: there is no remaining contiguous two-hour block
under this allocation. The 15-minute gap before 10:00 cannot fit the 30-minute
follow-up; it is suggested after lunch instead.

## Provenance and release integrity

This skill packages the ProjectOps course project's student-created
`src/projectops/planner.py` as `scripts/planner_engine.py`, byte for byte. The
implementation uses earliest-deadline-first allocation without an external
scheduler library. The package's MIT license applies to this skill package.
`references/release-manifest.json` records the engine's SHA-256 and the expected
file hashes. Repository maintenance uses `scripts/package_planner_skill.py` to
refresh the copy and manifest, or `--check` to reject drift without changing it.
Neither maintenance action publishes anything.

## Publication and clean-install procedure

The proposed public source is the GitHub Hermes tap
`PriyankaAmrute/projectops-skills`, with this exact layout:
`skills/projectops-planner/`. Repository creation/publication needs a separate
review and authorization; it has not been performed by this packaging step.
An immutable release commit must be recorded after publication. No public
repository or verified clean Hermes installation is claimed yet.

On a fresh Hermes installation, use a separate empty `HERMES_HOME`, record the
installed Hermes version and then use the native commands:

```text
hermes skills tap add PriyankaAmrute/projectops-skills
hermes skills inspect PriyankaAmrute/projectops-skills/skills/projectops-planner
hermes skills install PriyankaAmrute/projectops-skills/skills/projectops-planner
hermes skills list
hermes skills audit projectops-planner
```

This Hermes release does not expose an install `--ref` or `@COMMIT` selector.
Native installation resolves the tap's default branch and records a source
tree SHA. Before execution, compare all installed files with this release
manifest, verify the expected source tree, and separately record the public
immutable commit containing that tree. Stop on any mismatch. Do not describe
the tree SHA as a commit SHA or claim native arbitrary-commit selection.

For the controlled execution demonstration, configure an authorized model and
permit only the tools needed in the fresh environment, then run:

```text
hermes chat --oneshot --toolsets skills,terminal --skills projectops-planner -q "Use the ProjectOps planner's bundled synthetic example and report the calculated schedule and deferred tasks."
```

Retain the full sanitized installation, skill activation, actual CLI/tool
execution, useful output, hashes, source commit and platform version. An empty
profile alone is not evidence of a fresh Hermes installation. This controlled
demo does not enable generic terminal execution in the deployed ProjectOps
assistant, where `projectops_plan_work` is the intended integration.
