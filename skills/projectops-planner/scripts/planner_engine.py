"""Suggest work slots from explicit timestamps and structured synthetic tasks.

API: ``plan(payload)`` returns a JSON-compatible result without modifying its
input or any external state. All timestamps must use ISO 8601 with ``T`` and an
explicit numeric UTC offset or ``Z``. Named zones and naive timestamps are not
accepted; callers must resolve local clock ambiguity before calling this API.

Tasks use earliest deadline first, then larger integer priority, then lexical
ID. Each task occupies one contiguous block. This greedy heuristic does not
prove that an unscheduled task is impossible under another allocation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re


class PlanningInputError(ValueError):
    """A required input is missing, malformed, or unsupported."""


_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,6})?)?(?:Z|[+-]\d{2}:\d{2})"
)


@dataclass(frozen=True)
class _Task:
    id: str
    title: str
    deadline: datetime
    estimate_minutes: int
    priority: int


def _object(value, required, path):
    if not isinstance(value, dict):
        raise PlanningInputError(f"{path} must be an object.")
    missing = required - value.keys()
    if missing:
        raise PlanningInputError(f"{path} is missing: {', '.join(sorted(missing))}.")
    unsupported = value.keys() - required
    if unsupported:
        raise PlanningInputError(f"{path} has unsupported fields: {', '.join(sorted(unsupported))}.")
    return value


def _timestamp(value, path):
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise PlanningInputError(f"{path} must be an ISO timestamp with T and an explicit offset or Z.")
    if not value.endswith("Z") and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        raise PlanningInputError(f"{path} has an invalid UTC offset.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as error:
        raise PlanningInputError(f"{path} is not a valid timestamp.") from error


def _list(value, path):
    if not isinstance(value, list):
        raise PlanningInputError(f"{path} must be a list.")
    return value


def _intervals(value, path):
    intervals = []
    for index, raw in enumerate(_list(value, path)):
        label = f"{path}[{index}]"
        record = _object(raw, {"start", "end"}, label)
        start = _timestamp(record["start"], f"{label}.start")
        end = _timestamp(record["end"], f"{label}.end")
        if end <= start:
            raise PlanningInputError(f"{label}.end must be after start in elapsed time.")
        intervals.append((start, end))
    return intervals


def _tasks(value):
    tasks = []
    ids = set()
    fields = {"id", "title", "deadline", "estimate_minutes", "priority"}
    for index, raw in enumerate(_list(value, "tasks")):
        label = f"tasks[{index}]"
        record = _object(raw, fields, label)
        for name in ("id", "title"):
            if not isinstance(record[name], str) or not record[name].strip():
                raise PlanningInputError(f"{label}.{name} must be a nonempty string.")
        task_id = record["id"]
        if task_id != task_id.strip():
            raise PlanningInputError(f"{label}.id must not have surrounding whitespace.")
        if task_id in ids:
            raise PlanningInputError("Task IDs must be unique.")
        ids.add(task_id)
        estimate = record["estimate_minutes"]
        priority = record["priority"]
        if type(estimate) is not int or estimate <= 0:
            raise PlanningInputError(f"{label}.estimate_minutes must be a positive integer.")
        if type(priority) is not int or priority < 0:
            raise PlanningInputError(f"{label}.priority must be a nonnegative integer; larger wins ties.")
        tasks.append(_Task(
            id=task_id,
            title=record["title"],
            deadline=_timestamp(record["deadline"], f"{label}.deadline"),
            estimate_minutes=estimate,
            priority=priority,
        ))
    return sorted(tasks, key=lambda task: (task.deadline, -task.priority, task.id))


def _merge(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _free_intervals(windows, busy, as_of):
    free = []
    for start, end in _merge(windows):
        cursor = max(start, as_of)
        if cursor >= end:
            continue
        for busy_start, busy_end in _merge(busy):
            if busy_end <= cursor:
                continue
            if busy_start >= end:
                break
            if busy_start > cursor:
                free.append((cursor, busy_start))
            cursor = max(cursor, busy_end)
            if cursor >= end:
                break
        if cursor < end:
            free.append((cursor, end))
    return free


def _utc(value):
    return value.isoformat().replace("+00:00", "Z")


def plan(payload):
    """Allocate tasks without overlap; raise PlanningInputError for invalid data.

    Required root fields: as_of, work_windows, busy, tasks. Intervals contain
    start/end. Tasks contain id/title/deadline/estimate_minutes/priority. Empty
    lists are valid. Higher priority only breaks equal-deadline ties.
    """
    record = _object(payload, {"as_of", "work_windows", "busy", "tasks"}, "input")
    as_of = _timestamp(record["as_of"], "as_of")
    windows = _intervals(record["work_windows"], "work_windows")
    busy = _intervals(record["busy"], "busy")
    tasks = _tasks(record["tasks"])
    free = _free_intervals(windows, busy, as_of)
    scheduled = []
    unscheduled = []
    for task in tasks:
        item = {
            "task_id": task.id,
            "title": task.title,
            "deadline": _utc(task.deadline),
            "estimate_minutes": task.estimate_minutes,
            "priority": task.priority,
        }
        if task.deadline <= as_of:
            unscheduled.append({
                **item,
                "status": "not_scheduled",
                "reason_code": "deadline_not_after_as_of",
                "reason": "Deadline is at or before the planning time.",
            })
            continue
        for index, (start, end) in enumerate(free):
            # Compare an integer duration against available elapsed time before
            # adding it, so unreasonable input durations cannot overflow dates.
            latest_end = min(end, task.deadline)
            if task.estimate_minutes > (latest_end - start) // timedelta(minutes=1):
                continue
            finish = start + timedelta(minutes=task.estimate_minutes)
            scheduled.append({**item, "status": "suggested", "start": _utc(start), "end": _utc(finish)})
            free[index:index + 1] = [(finish, end)] if finish < end else []
            break
        else:
            unscheduled.append({
                **item,
                "status": "not_scheduled",
                "reason_code": "no_contiguous_slot_under_heuristic",
                "reason": "No remaining contiguous slot before the deadline under this allocation heuristic; another allocation may differ.",
            })
    return {
        "kind": "deterministic_planning_result",
        "execution": "planning_only",
        "algorithm": "earliest_deadline_first_nonpreemptive",
        "as_of": _utc(as_of),
        "schedule": sorted(scheduled, key=lambda item: (item["start"], item["task_id"])),
        "unscheduled": unscheduled,
        "note": "This planner performs calculations only; it does not invoke a model or change external state.",
    }
