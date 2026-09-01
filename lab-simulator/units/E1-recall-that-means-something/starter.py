"""E1 · Build the two recalls that disagree by thirty points.

Implement all three. Run `labsim check E1` when you want them graded.

`gold_map` maps a piece of evidence to the set of chunk ids that satisfy it:

    {"hop_a": {"doc-3:1", "doc-3:2"}, "hop_b": {"doc-9:0"}}

Two chunks in one set means either would do. Two *keys* means you need both.
"""
from __future__ import annotations

import math  # noqa: F401  - you will want it


def evidence_recall_at_k(retrieved_ids, gold_map, k=None):
    """Share of gold evidence pieces satisfied by the top k. None if there is no gold."""
    # TODO 1 — no gold means unanswerable, which is not the same as a score of zero
    # TODO 2 — truncate the retrieved list, once
    # TODO 3 — a piece is satisfied if ANY of its chunk ids was retrieved
    return None


def full_chain_recall(retrieved_ids, gold_map, k=None):
    """1.0 only when every gold piece is satisfied. All or nothing, per question."""
    # TODO 4
    return None


def ndcg_at_k(retrieved_ids, gold_map, k=10):
    """Graded, de-duplicated nDCG. Each distinct gold piece is worth 1, earned once.

    DCG = sum over ranks i (from 1) of 1/log2(i+1), crediting a chunk only for the first
    uncredited gold piece it satisfies. IDCG is the same sum over the ideal ranking.
    """
    # TODO 5 — walk the retrieved list in rank order, crediting each gold piece at most once
    # TODO 6 — the ideal is min(len(gold_map), k) pieces in the top positions, not len(gold_map)
    return None
