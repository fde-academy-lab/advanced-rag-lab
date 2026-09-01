"""R3 · the worked answer."""
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
    if not dense_misses:
        return 0.0
    return len(dense_misses & lexical_misses) / len(dense_misses)
