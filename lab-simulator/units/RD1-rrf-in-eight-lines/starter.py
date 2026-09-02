# ruff: noqa: F821  — the blanks are the exercise
"""RD1 · Reciprocal rank fusion, with the two blanks everyone fills in wrong.

Fill the two blanks marked ___ and run `labsim check RD1`. Each leg is a list of hits ordered
best-first; a hit has a `.chunk_id`. Return the fused hits, best-first.
"""
from __future__ import annotations


def rrf(legs, k: int = 60):
    scores: dict[str, float] = {}
    keep: dict[str, object] = {}
    for leg in legs:
        for rank, hit in enumerate(leg, start=___):          # blank 1
            scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + ___   # blank 2
            keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(scores.items(), key=lambda kv: -kv[1])]
