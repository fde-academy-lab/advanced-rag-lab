"""Decoy · full-chain recall implemented as an average.

"It is a recall, so it averages." What comes out is evidence recall with extra steps, and the
number it produces is *higher* than the truth — so the dashboard looks better and the
answer-correctness gap it was meant to explain stays unexplained.

The all-or-nothing is not a rounding choice. Two thirds of a reasoning chain produces a
confident wrong answer, and the metric has to say zero for that.
"""
from __future__ import annotations

import math


def evidence_recall_at_k(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    return sum(1 for cids in gold_map.values() if cids & got) / len(gold_map)


def full_chain_recall(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    hits = [1.0 if cids & got else 0.0 for cids in gold_map.values()]
    return sum(hits) / len(hits)          # <- the bug


def ndcg_at_k(retrieved_ids, gold_map, k=10):
    if not gold_map:
        return None
    items = list(gold_map.values())
    dcg, seen = 0.0, set()
    for i, cid in enumerate(retrieved_ids[:k], 1):
        for j, cids in enumerate(items):
            if j not in seen and cid in cids:
                dcg += 1.0 / math.log2(i + 1)
                seen.add(j)
                break
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(items), k) + 1))
    return dcg / ideal if ideal else None
