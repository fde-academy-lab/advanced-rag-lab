#!/usr/bin/env python3
"""XD1 · the k=5 and k=10 rows of the BM25 arm, from `python scripts/run_eval.py --ksweep`.

Published in docs/04-evaluation/metrics.md; tests/test_measurements.py holds this file and the
grid to the same numbers.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_answer, run  # noqa: E402

# python scripts/run_eval.py --ksweep  ·  bm25 arm, cross-encoder
K5 = {"evidence_recall": 0.6329, "context_precision": 0.3029}
K10 = {"evidence_recall": 0.7279, "context_precision": 0.1948}
TOLERANCE = 0.05


def _dir(x) -> str:
    return str(x or "").strip().lower()


def main(attempt: str) -> int:
    ans = load_answer(attempt, required=("context_precision_direction",
                                         "evidence_recall_direction",
                                         "context_precision_at_k10",
                                         "gate_can_be_cleared_by"))
    c = Checker()
    c("direction of context precision is down", _dir(ans["context_precision_direction"]) == "down",
      f"you said {_dir(ans['context_precision_direction'])!r}; it goes "
      f"{K5['context_precision']:.4f} → {K10['context_precision']:.4f}")
    c("direction of evidence recall is up", _dir(ans["evidence_recall_direction"]) == "up",
      f"you said {_dir(ans['evidence_recall_direction'])!r}; it goes "
      f"{K5['evidence_recall']:.4f} → {K10['evidence_recall']:.4f}")
    try:
        got = float(ans["context_precision_at_k10"])
    except (TypeError, ValueError):
        got = None
    off = abs(got - K10["context_precision"]) if got is not None else None
    if off is not None:
        c.note(f"predicted {got:.4f}, measured {K10['context_precision']:.4f}, off by {off:+.4f}")
    c(f"precision at k=10 within {TOLERANCE}", off is not None and off <= TOLERANCE,
      "the k grid in metrics.md has the row")
    words = str(ans["gate_can_be_cleared_by"]).lower()
    c("the gate is cleared by lowering k, and you said so",
      any(w in words for w in ("lower", "reduce", "smaller", "cut", "drop", "decrease", "k=")),
      "the gate reads a number whose denominator is a config flag")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
