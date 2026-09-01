"""Decoy · `enumerate(leg)` without `start=1`.

The most-shipped bug in every RRF implementation on the internet, and it is nearly invisible:
on two legs of equal length every rank shifts by one together, so the fused ordering barely
changes and the aggregate metric moves by a rounding error.

It becomes visible when someone adds a third leg of a different length, or when one leg is
truncated by a pre-filter — at which point the fusion has an unexplained bias toward the shorter
list and the regression is six weeks downstream of the commit that caused it.
"""
from __future__ import annotations


def rrf(legs, k: int = 60):
    agg: dict[str, float] = {}
    keep: dict[str, object] = {}
    for leg in legs:
        for rank, hit in enumerate(leg):          # <- the bug
            agg[hit.chunk_id] = agg.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(agg.items(), key=lambda kv: -kv[1])]


def failure_overlap(dense_misses: set[str], lexical_misses: set[str]) -> float:
    if not dense_misses:
        return 0.0
    return len(dense_misses & lexical_misses) / len(dense_misses)
