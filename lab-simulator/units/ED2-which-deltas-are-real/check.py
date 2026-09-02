#!/usr/bin/env python3
"""ED2 · rows from fusion-rules.md; the key is 'interval excludes zero'."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_answer, run  # noqa: E402

# (delta, lo, hi) — python scripts/run_eval.py --compare
ROWS = {1: (0.0624, 0.0407, 0.0857), 2: (0.0008, -0.0101, 0.0109),
        3: (-0.0535, -0.0776, -0.0295), 4: (0.0048, -0.0024, 0.0145)}
REAL = {n for n, (_d, lo, hi) in ROWS.items() if (lo > 0) == (hi > 0)}


def main(attempt: str) -> int:
    ans = load_answer(attempt, required=("real", "row_3_means_weighted_is"))
    c = Checker()
    raw = ans["real"]
    picked = set()
    for x in (raw if isinstance(raw, list) else [raw]):
        try:
            picked.add(int(x))
        except (TypeError, ValueError):
            pass
    c("rows are numbered 1 to 4", picked <= set(ROWS), f"got {sorted(picked)}")
    c("every real delta is picked", REAL <= picked,
      f"missed {sorted(REAL - picked)} — their intervals exclude zero")
    c("nothing inside the noise band is picked", picked <= REAL,
      f"{sorted(picked - REAL)} straddle zero; a mean alone is not a difference")
    c("row 3 is read as a regression for the weighted rule",
      str(ans["row_3_means_weighted_is"]).strip().lower().startswith("worse"),
      "delta is second minus first; rrf → w0.2 at −0.0535 means the weighted rule scores lower")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
