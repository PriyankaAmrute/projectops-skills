"""Calculate an offline proposal from an explicit JSON file or standard input.

No account access, subprocesses, model calls, task persistence or Calendar writes
are performed. Expected input errors never echo input contents or file paths.
"""

import argparse
import json
from pathlib import Path
import sys

# An installed skill is read-only input; importing its engine need not alter it.
sys.dont_write_bytecode = True

from planner_engine import PlanningInputError, plan


MAX_INPUT_BYTES = 65_536


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "Invalid command arguments. Use --help for usage.\n")


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("JSON constants must be finite.")


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument("input", nargs="?", default="-", help="Existing JSON file, or - for standard input.")
    args = parser.parse_args(argv)
    try:
        if args.input == "-":
            raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        else:
            with Path(args.input).open("rb") as stream:
                raw = stream.read(MAX_INPUT_BYTES + 1)
    except OSError:
        print("Cannot read planning input. Provide a readable JSON file or standard input.", file=sys.stderr)
        return 2
    if len(raw) > MAX_INPUT_BYTES:
        print("Planning input exceeds the 65536-byte limit.", file=sys.stderr)
        return 2
    try:
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    except (UnicodeError, ValueError, RecursionError):
        print("Invalid planning JSON. Use UTF-8 JSON with unique fields and finite numbers.", file=sys.stderr)
        return 2
    try:
        result = plan(payload)
    except (PlanningInputError, RecursionError):
        print("Invalid planning input. Check required fields, timestamps, intervals, estimates and unique task IDs.", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
