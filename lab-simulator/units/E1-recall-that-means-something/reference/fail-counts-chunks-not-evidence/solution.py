"""Decoy · flattens the gold map into a set of chunk ids.

The signature simplification everyone reaches for, because `dict[str, set[str]]` looks
over-engineered until you know why it is that shape. Once flattened, two chunks satisfying the
*same* hop count as two hits, so a retriever that returns near-duplicates of one piece of
evidence scores the same as one that found two different pieces.

That is the exact failure a multi-hop system cannot afford, and this metric cannot see it.
"""
from __future__ import annotations

import math


def _flat(gold_map):
    return {cid for cids in gold_map.values() for cid in cids}


def evidence_recall_at_k(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    gold = _flat(gold_map)
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    return len(gold & got) / len(gold)


def full_chain_recall(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    gold = _flat(gold_map)
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    return 1.0 if gold <= got else 0.0


def ndcg_at_k(retrieved_ids, gold_map, k=10):
    if not gold_map:
        return None
    gold = _flat(gold_map)
    dcg = sum(1.0 / math.log2(i + 1)
              for i, cid in enumerate(retrieved_ids[:k], 1) if cid in gold)
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(gold), k) + 1))
    return dcg / ideal if ideal else None
