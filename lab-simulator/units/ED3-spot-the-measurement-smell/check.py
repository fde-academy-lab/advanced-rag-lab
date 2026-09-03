#!/usr/bin/env python3
"""ED3 · the key is the shape of each claim, and it is stated in the brief."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_answer, run  # noqa: E402

# Claim 2: every pairwise delta on answer_correct is inside the noise band (fusion-rules.md).
# Claim 3: context precision divides by k; a fall with k is arithmetic, not retrieval.
# Claim 4: an alpha chosen on the frozen slice and reported on it — and 0.35 / 0.7801 appear in
#          no measurement note, which is the second smell on the same claim.
SMELLS = {2: {"no-interval"}, 3: {"denominator"}, 4: {"tuned-on-frozen", "no-command"}}
SOUND = {1, 5}


def main(attempt: str) -> int:
    ans = load_answer(attempt, required=("smells", "shapes"))
    c = Checker()
    raw = ans["smells"]
    picked = set()
    for x in (raw if isinstance(raw, list) else [raw]):
        try:
            picked.add(int(x))
        except (TypeError, ValueError):
            pass
    c("claims are numbered 1 to 5", picked <= set(range(1, 6)), f"got {sorted(picked)}")
    c("every smell is caught", set(SMELLS) <= picked,
      f"missed {sorted(set(SMELLS) - picked)}")
    c("no sound claim is accused", not (picked & SOUND),
      f"{sorted(picked & SOUND)} carry a command or a committed file and an interval")

    shapes = ans.get("shapes") or {}
    if not isinstance(shapes, dict):
        shapes = {}
    named = 0
    for n, allowed in SMELLS.items():
        got = str(shapes.get(n, shapes.get(str(n), ""))).strip().lower()
        if got in allowed:
            named += 1
        elif n in picked:
            c.note(f"claim {n}: you named {got!r}; its shape is {' or '.join(sorted(allowed))}")
    c("each smell is named by its shape", named == len(SMELLS),
      f"{named} of {len(SMELLS)} shapes right — the brief's table has the vocabulary")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
