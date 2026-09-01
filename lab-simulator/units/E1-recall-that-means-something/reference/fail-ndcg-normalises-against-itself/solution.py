"""Decoy · nDCG normalised against the ranking it was handed.

IDCG computed over the gold pieces the retriever actually found, rather than over the ideal
ranking. The result is a metric that cannot go down: find one gold chunk and seven distractors
and it reports 1.0.

It survives casual testing because on easy cases — everything found — the two definitions
coincide exactly. It only diverges when the system is doing badly, which is when you needed the
number.
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
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, len(seen) + 1))   # <- the bug
    return dcg / ideal if ideal else None
