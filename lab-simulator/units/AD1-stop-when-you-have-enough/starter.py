"""AD1 · Stop when you have enough.

`steps` is a list, one entry per search step in order; each entry is the set of gold-piece
names that step's retrieved chunks satisfied. `required` is the set of piece names the
question needs. Return the 0-based index of the FIRST step at which everything gathered so far
covers `required`, or None if no prefix of `steps` ever does.

    stop_at([{"a"}, {"b"}, {"c"}], {"a", "b"})  -> 1
    stop_at([{"a"}, {"a"}, {"a"}], {"a", "b"})  -> None
"""
from __future__ import annotations


def stop_at(steps: list[set[str]], required: set[str]) -> int | None:
    # TODO — remember what you have gathered, and stop the first time it is enough
    return None
