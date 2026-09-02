#!/usr/bin/env python3
"""AD1 · four fixtures, one per way the stop rule gets shipped wrong."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402


def main(attempt: str) -> int:
    stop_at = load_solution(attempt, required=("stop_at",)).stop_at
    c = Checker()

    c("stops at the first sufficient step",
      stop_at([{"a"}, {"b"}, {"c"}, {"a", "b"}], {"a", "b"}) == 1,
      f"got {stop_at([{'a'}, {'b'}, {'c'}, {'a', 'b'}], {'a', 'b'})}; a and b are both known "
      "after step 1, and steps 2 and 3 are paid for nothing")
    c("does not stop early",
      stop_at([{"a"}, {"b"}, {"c"}], {"a", "b", "c"}) == 2,
      f"got {stop_at([{'a'}, {'b'}, {'c'}], {'a', 'b', 'c'})}; some evidence at step 0 is not "
      "enough evidence")
    c("returns None when the budget runs out",
      stop_at([{"a"}, {"a"}, {"a"}], {"a", "b"}) is None,
      f"got {stop_at([{'a'}, {'a'}, {'a'}], {'a', 'b'})}; b never arrived and the loop must "
      "say so rather than answer")
    c("evidence carries across steps",
      stop_at([{"a"}, set(), {"b"}], {"a", "b"}) == 2,
      f"got {stop_at([{'a'}, set(), {'b'}], {'a', 'b'})}; a was found at step 0 and is still "
      "known at step 2")
    c("an empty requirement is satisfied immediately", stop_at([{"x"}], set()) == 0)
    c("no steps at all returns None", stop_at([], {"a"}) is None)
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
