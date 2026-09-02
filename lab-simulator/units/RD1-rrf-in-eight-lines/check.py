#!/usr/bin/env python3
"""RD1 · synthetic legs only. No corpus — this drill is about the formula meeting Python."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    score: float = 0.0


def leg(*ids):
    return [Hit(i) for i in ids]


def ids_of(hits):
    return [h.chunk_id for h in hits]


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("rrf",))
    rrf = mod.rrf
    c = Checker()

    # rank starts at one: with k=0, rank 1 alone scores 1.0 and rank 2 alone scores 0.5. An
    # implementation enumerating from 0 divides by zero on the first hit and says so loudly;
    # one that quietly uses 1/k for rank 1 gets the order between "a" and "b" wrong here.
    try:
        fused = rrf([leg("a", "b")], k=0)
        c("rank 1 is 1/(k+1), so rank starts at one", ids_of(fused) == ["a", "b"],
          f"got {ids_of(fused)}")
    except ZeroDivisionError:
        c("rank 1 is 1/(k+1), so rank starts at one", False,
          "1/(0+rank) divided by zero: your first rank is 0")

    c("k=0 makes rank 1 worth twice rank 2", ids_of(rrf([leg("x", "y")], k=0)) == ["x", "y"])

    fused = rrf([leg("a", "b"), leg("c")], k=60)
    c("a chunk in only one leg survives", set(ids_of(fused)) == {"a", "b", "c"},
      f"got {ids_of(fused)} — the chunk that only one retriever found is the reason for two")

    fused = rrf([leg("a", "b"), leg("b", "c")], k=60)
    c("a chunk in both legs outranks a chunk in one", ids_of(fused)[0] == "b",
      f"got {ids_of(fused)}; b is rank 2 in both legs and should sum past a, rank 1 in one")

    c("no legs at all returns nothing", rrf([], k=60) == [])
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
