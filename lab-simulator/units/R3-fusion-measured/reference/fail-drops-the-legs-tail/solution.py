"""Decoy · fuses only the chunks both legs found.

Reads as a sensible guard — "only trust what both retrievers agree on" — and it is an
intersection wearing a fusion rule's name. Precision at the top goes up, which is what anyone
eyeballing the first few results would notice, and every chunk that exactly one retriever found
is gone.

Those chunks are the entire reason for running two retrievers.
"""
from __future__ import annotations


def rrf(legs, k: int = 60):
    agg: dict[str, float] = {}
    keep: dict[str, object] = {}
    common = None
    for leg in legs:
        ids = {h.chunk_id for h in leg}
        common = ids if common is None else (common & ids)     # <- the bug
    for leg in legs:
        for rank, hit in enumerate(leg, start=1):
            if hit.chunk_id not in (common or set()):
                continue
            agg[hit.chunk_id] = agg.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(agg.items(), key=lambda kv: -kv[1])]


def failure_overlap(dense_misses: set[str], lexical_misses: set[str]) -> float:
    if not dense_misses:
        return 0.0
    return len(dense_misses & lexical_misses) / len(dense_misses)
