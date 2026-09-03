"""Decoy · Jaccard where a conditional probability was asked for.

Correct fusion, correct metric bar on evidence recall, and the diagnostic answers a question
nobody asked. Jaccard measures how *similar* the two failure sets are; the decision needs
"given that dense missed this, is bm25 any help?", which is conditional and asymmetric.

Here it reports 0.8762 against a true 0.9684 — close enough to look right, far enough to change
what you would conclude about whether the legs are complementary.
"""
from __future__ import annotations


def rrf(legs, k: int = 60):
    agg: dict[str, float] = {}
    keep: dict[str, object] = {}
    for leg in legs:
        for rank, hit in enumerate(leg, start=1):
            agg[hit.chunk_id] = agg.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(agg.items(), key=lambda kv: -kv[1])]


def failure_overlap(dense_misses: set[str], lexical_misses: set[str]) -> float:
    union = dense_misses | lexical_misses
    if not union:
        return 0.0
    return len(dense_misses & lexical_misses) / len(union)      # <- the bug
