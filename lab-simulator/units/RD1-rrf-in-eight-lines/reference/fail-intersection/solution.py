"""Decoy · keeps only chunks present in every leg. Precision looks great."""
from __future__ import annotations


def rrf(legs, k: int = 60):
    if not legs:
        return []
    common = set.intersection(*[{h.chunk_id for h in leg} for leg in legs])
    scores: dict[str, float] = {}
    keep: dict[str, object] = {}
    for leg in legs:
        for rank, hit in enumerate(leg, start=1):
            if hit.chunk_id in common:
                scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
                keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(scores.items(), key=lambda kv: -kv[1])]
