from __future__ import annotations


def rrf(legs, k: int = 60):
    scores: dict[str, float] = {}
    keep: dict[str, object] = {}
    for leg in legs:
        for rank, hit in enumerate(leg, start=1):
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(scores.items(), key=lambda kv: -kv[1])]
