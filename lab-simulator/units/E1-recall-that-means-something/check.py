#!/usr/bin/env python3
"""Checks for E1 · Build the two recalls that disagree by thirty points.

Two of these checks are the unit.

`a piece of evidence is satisfied by any one of its chunks` distinguishes a metric that counts
*evidence* from one that counts *chunks*. The fixture gives one hop three interchangeable
chunks; a flattened implementation scores 2/4 where the correct one scores 1/2.

`nDCG is normalised against the ideal ranking` uses a case where the retriever finds exactly one
of three gold pieces, at rank 1. Self-normalising nDCG reports 1.0 there. The correct answer is
0.4693, and the difference is the whole reason nDCG is worth computing.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

TOL = 1e-9

# Two hops. The first has three interchangeable chunks, the second has one.
INTERCHANGEABLE = {"hop_a": {"c1", "c2", "c3"}, "hop_b": {"c9"}}
THREE_HOPS = {"a": {"a1"}, "b": {"b1"}, "c": {"c1"}}


def close(got, want) -> bool:
    return got is not None and abs(float(got) - want) < 1e-4


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("evidence_recall_at_k", "full_chain_recall",
                                           "ndcg_at_k"))
    c = Checker()
    er, fc, nd = mod.evidence_recall_at_k, mod.full_chain_recall, mod.ndcg_at_k

    # ------------------------------------------------------------- evidence recall
    c("no gold evidence returns None, not zero",
      er([], {}, k=8) is None and fc([], {}, k=8) is None and nd([], {}, k=8) is None,
      "an unanswerable question scored 0.0 drags every mean down and makes correct "
      "abstention look like failure")

    c("evidence recall, everything found", close(er(["a1", "b1", "c1"], THREE_HOPS), 1.0))
    c("evidence recall, two of three found",
      close(er(["a1", "b1", "zz"], THREE_HOPS), 2 / 3))
    c("evidence recall respects k",
      close(er(["a1", "b1", "c1"], THREE_HOPS, k=2), 2 / 3),
      "k truncates the retrieved list, not the gold map")

    # The check that separates counting evidence from counting chunks.
    # Three chunks of one hop, not two: at two, a flattening implementation scores 2/4 = 0.5
    # and so does a correct one, so the check the unit names as its discriminator agreed with
    # the decoy it was written to catch. At three the correct answer is still 1 of 2 pieces
    # and the flattened one is 3/4.
    c("a piece of evidence is satisfied by any one of its chunks",
      close(er(["c1", "c2", "c3"], INTERCHANGEABLE), 0.5),
      "c1, c2 and c3 all satisfy hop_a and hop_b was not found, so this is 1 of 2 pieces. "
      "An implementation that flattens the gold map scores 3/4 here")

    # ------------------------------------------------------------- full chain
    c("full-chain recall is 1.0 only when every piece is found",
      close(fc(["a1", "b1", "c1"], THREE_HOPS), 1.0))

    c("full-chain recall is all or nothing",
      close(fc(["a1", "b1", "zz"], THREE_HOPS), 0.0),
      "two of three hops found scored above zero. Two thirds of a reasoning chain produces a "
      "confident wrong answer; the metric has to say 0")

    c("full-chain recall respects k",
      close(fc(["a1", "b1", "c1"], THREE_HOPS, k=2), 0.0))

    c("full-chain recall accepts any satisfying chunk",
      close(fc(["c3", "c9"], INTERCHANGEABLE), 1.0),
      "c3 satisfies hop_a and c9 satisfies hop_b, so the chain is complete")

    # ------------------------------------------------------------- nDCG
    c("nDCG is 1.0 for a perfect ranking", close(nd(["a1", "b1", "c1"], THREE_HOPS, k=8), 1.0))

    perfect3 = sum(1 / math.log2(i + 1) for i in (1, 2, 3))
    c("nDCG penalises rank, not just presence",
      close(nd(["zz", "a1", "b1", "c1"], THREE_HOPS, k=8),
            sum(1 / math.log2(i + 1) for i in (2, 3, 4)) / perfect3),
      "the same three gold chunks one position lower must score lower")

    c("nDCG is normalised against the ideal ranking",
      close(nd(["a1", "zz", "yy"], THREE_HOPS, k=8), (1 / math.log2(2)) / perfect3),
      "one of three pieces at rank 1 is 0.4693, not 1.0. Normalising against what was "
      "found gives a metric that cannot go down")

    c("nDCG credits a gold piece once",
      close(nd(["c1", "c2", "c3"], INTERCHANGEABLE, k=8),
            (1 / math.log2(2)) / sum(1 / math.log2(i + 1) for i in (1, 2))),
      "c1, c2 and c3 all satisfy hop_a. Three near-duplicates of one hop must not score "
      "like two different hops")

    ideal_capped = sum(1 / math.log2(i + 1) for i in (1, 2))
    c("nDCG caps the ideal at k",
      close(nd(["a1", "b1"], THREE_HOPS, k=2), ideal_capped / ideal_capped),
      "with 3 gold pieces and k=2, a perfect run must score 1.0 — dividing by all 3 "
      "makes a perfect retriever look like a 0.7")

    # ------------------------------------------------------------- the reason the unit exists
    if all(close(x, y) for x, y in [(er(["a1", "b1", "zz"], THREE_HOPS), 2 / 3),
                                    (fc(["a1", "b1", "zz"], THREE_HOPS), 0.0)]):
        c.note("On one three-hop question with two of three pieces found, your two metrics "
               "now report 0.667 and 0.000. That 0.667 is the number that goes in the deck.")

    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
