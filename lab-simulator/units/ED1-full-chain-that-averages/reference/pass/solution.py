from __future__ import annotations


def full_chain_recall(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    window = set(retrieved_ids[:k] if k else retrieved_ids)
    return 1.0 if all(chunk_ids & window for chunk_ids in gold_map.values()) else 0.0
