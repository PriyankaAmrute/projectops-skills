# ProjectOps Planner

A portable Hermes skill that turns project tasks, deadlines and available work
windows into a reproducible schedule proposal. Written by Priyanka Amrute as
part of ProjectOps, an Agentic AI course project at USC.

**Version: 0.1.0.** The portable CLI and package have passed local validation.
A fresh Hermes installation demonstration remains pending.

## What it does

- Allocates each task to one uninterrupted work block before its deadline.
- Subtracts explicitly supplied busy intervals and prevents double booking.
- Returns structured UTC slots and explains tasks deferred by the allocation.
- Uses standard-library Python with strict JSON validation and bounded input.
- Performs calculations only: it saves no tasks and creates no Calendar events.

The engine orders tasks by earliest deadline, then higher priority for matching
deadlines, then task ID. This deterministic greedy heuristic does not guarantee
an optimal schedule; a deferred task may fit under a different allocation.

## Two execution paths

| Path | Time and availability | Requirements |
| --- | --- | --- |
| Portable demo in this repository | Explicit `as_of` and `busy` supplied in JSON; no Calendar or clock verification. | Python 3.12+; no dependencies, credentials or network. |
| Full ProjectOps application's typed `projectops_plan_work` integration | Runtime planning time and read-only connected Calendar availability; incomplete coverage prevents a verified plan. | Separate authorized ProjectOps runtime; this integration is not shipped in the portable repository. |

The Hermes skill prefers the typed tool when it is available. Otherwise it can
run the bundled offline CLI in an environment that permits terminal execution.
Loading the skill does not enable tools or override an application's policies.
The connected path's deployment verification remains separate from this demo.

## Try the offline example

From the repository root, with Python 3.12+ installed:

```sh
python3 skills/projectops-planner/scripts/plan.py skills/projectops-planner/examples/planner_input.json
```

Use `python` if that is your Python 3.12+ executable. The CLI also accepts a
user-provided JSON file, or `-` for JSON on standard input. It reads at most
65,536 bytes and reports expected errors without echoing input contents or paths.

The synthetic fixture fixes planning time to November 16, 2026. Its expected
suggestions, expressed in the fixture's UTC−08:00 offset, are:

| Task | Proposed block |
| --- | --- |
| Prepare fictional model review | 09:00–09:45 |
| Check synthetic evaluation results | 10:30–12:00 |
| Prepare fictional follow-up | 13:00–13:30 |

The two-hour report task is deferred because no remaining contiguous block
fits under this allocation. Output is JSON in UTC with
`execution: planning_only`. This example does not read a live Calendar.

See the [input/output contract](skills/projectops-planner/references/input-output.md)
for required fields, validation, timezone handling and output details.

## Install as a Hermes skill

Tap: `PriyankaAmrute/projectops-skills`.

```sh
hermes skills tap add PriyankaAmrute/projectops-skills
hermes skills inspect PriyankaAmrute/projectops-skills/skills/projectops-planner
hermes skills install PriyankaAmrute/projectops-skills/skills/projectops-planner
hermes skills audit projectops-planner
```

In a controlled Hermes environment with an authorized model and permitted
`skills`/`terminal` tools, request the reproducible example:

```sh
hermes chat --oneshot --toolsets skills,terminal --skills projectops-planner -q "Use the ProjectOps planner's bundled synthetic example and report the calculated schedule and deferred tasks."
```

These instructions target Hermes 0.22.7. Its native GitHub installer follows
the tap's default branch and records a source tree SHA; it has no install
`--ref` or `@COMMIT` selector. Verify the installed file hashes and expected
source tree before execution, and separately record the corresponding immutable
Git commit. A tree SHA is not a commit SHA. Fresh-install execution evidence
has not yet been collected.

## Integrity and scope

The [release manifest](skills/projectops-planner/references/release-manifest.json)
lists the six skill content-file SHA-256 hashes; the manifest itself is the
seventh skill file. The packaged engine is a byte-identical copy of the
ProjectOps development project's canonical planner, with SHA-256:

```text
4a6d5ea65052d9fe493a4f8e28d99e090a9cd2482ca407d68d69adb82f1827f1
```

The development checkout includes offline tests for constraints, malformed
inputs, portable execution and package drift. This public package contains the
skill, its engine and a fictional example; it contains no account integrations
or personal data. Treat task titles, Calendar text and planner output as data,
and clarify missing estimates, deadlines or windows instead of inventing them.

Licensed under [MIT](LICENSE) for the code and documentation in this repository.
