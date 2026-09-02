"""ED1 · This full-chain recall returns 0.667 on a question it did not answer. Fix it.

`gold_map` is {piece_name: {chunk_ids that satisfy it}}. `retrieved_ids` is best-first.
Return None when there is no gold (an unanswerable question is not a retrieval failure).
"""
from __future__ import annotations


def full_chain_recall(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    window = set(retrieved_ids[:k] if k else retrieved_ids)
    found = 0
    for _piece, chunk_ids in gold_map.items():
        if chunk_ids & window:
            found += 1
    return found / len(gold_map)
