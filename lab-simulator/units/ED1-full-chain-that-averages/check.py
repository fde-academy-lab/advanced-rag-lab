#!/usr/bin/env python3
"""ED1 · the same fixtures E1 uses for full-chain recall, and only those."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

THREE = {"a": {"a1"}, "b": {"b1"}, "c": {"c1"}}
INTERCHANGEABLE = {"hop_a": {"c1", "c2", "c3"}, "hop_b": {"c9"}}


def close(got, want) -> bool:
    return got is not None and abs(float(got) - want) < 1e-6


def main(attempt: str) -> int:
    fc = load_solution(attempt, required=("full_chain_recall",)).full_chain_recall
    c = Checker()
    c("no gold returns None, not zero", fc([], {}) is None,
      "an unanswerable question scored 0.0 drags the mean down")
    c("every piece found is 1.0", close(fc(["a1", "b1", "c1"], THREE), 1.0))
    c("full-chain recall is all or nothing", close(fc(["a1", "b1", "zz"], THREE), 0.0),
      f"two of three found scored {fc(['a1', 'b1', 'zz'], THREE)}; the question cannot be "
      "answered, so the metric has to say 0")
    c("full-chain recall respects k", close(fc(["a1", "b1", "c1"], THREE, k=2), 0.0),
      "the third piece is at rank 3 and the window is 2")
    c("a piece is satisfied by any satisfying chunk",
      close(fc(["c3", "c9"], INTERCHANGEABLE), 1.0),
      "c3 satisfies hop_a and c9 satisfies hop_b — the chain is complete")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
