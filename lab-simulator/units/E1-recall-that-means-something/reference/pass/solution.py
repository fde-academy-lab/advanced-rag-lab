"""E1 · the worked answer."""
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
    return 1.0 if all(cids & got for cids in gold_map.values()) else 0.0


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
