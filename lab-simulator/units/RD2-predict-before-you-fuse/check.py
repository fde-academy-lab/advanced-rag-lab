#!/usr/bin/env python3
"""RD2 · the measured values, and how far off the prediction was.

The three numbers are the k=8 row of `python scripts/run_eval.py --compare`, published in
docs/09-research/measurements/fusion-rules.md. They are pinned here rather than regenerated
because a drill has to grade in seconds; tests/test_measurements.py checks that this file and
the note still agree, so a drift in either fails CI rather than teaching a stale number.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_answer, run  # noqa: E402

# python scripts/run_eval.py --compare  ·  evidence_recall at k=8, cross-encoder
MEASURED = {"bm25": 0.7118, "dense": 0.7733, "rrf": 0.7742}
TOLERANCE = 0.03
NOISE_BAND = 0.0109          # upper end of the dense→rrf interval, (−0.0101, +0.0109)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main(attempt: str) -> int:
    ans = load_answer(attempt, required=("evidence_recall", "strongest_single_leg",
                                         "fusion_beats_its_better_leg", "because"))
    c = Checker()
    pred = ans["evidence_recall"] or {}
    c("all three arms have a number between 0 and 1",
      all(_num(pred.get(a)) is not None and 0 <= _num(pred.get(a)) <= 1 for a in MEASURED),
      f"got {pred}")
    if not c.ok:
        return emit({}, c)

    worst = 0.0
    for arm, truth in MEASURED.items():
        off = abs(_num(pred[arm]) - truth)
        worst = max(worst, off)
        c.note(f"{arm:<6} predicted {_num(pred[arm]):.4f}   measured {truth:.4f}   "
               f"off by {off:+.4f}")
    c(f"every prediction within {TOLERANCE} of the measured value", worst <= TOLERANCE,
      f"worst miss {worst:.4f}; the numbers are in fusion-rules.md, and so is why")

    strongest = str(ans["strongest_single_leg"]).strip().lower()
    c("the strongest single leg is the dense one", strongest == "dense",
      f"you said {strongest!r}; dense scores {MEASURED['dense']:.4f} against BM25's "
      f"{MEASURED['bm25']:.4f} — the opposite of what this repository once published")

    beats = str(ans["fusion_beats_its_better_leg"]).strip().lower() in ("no", "false", "n")
    c("fusion against its better leg is inside the noise band", beats,
      f"rrf − dense is {MEASURED['rrf'] - MEASURED['dense']:+.4f}, ci (−0.0101, +0.0109). "
      "That is not a win; it is a tie you paid a second index for")
    c("the reason is a sentence", len(str(ans["because"]).split()) >= 6)
    return emit({"worst_miss": round(worst, 4)}, c)


if __name__ == "__main__":
    sys.exit(run(main))
