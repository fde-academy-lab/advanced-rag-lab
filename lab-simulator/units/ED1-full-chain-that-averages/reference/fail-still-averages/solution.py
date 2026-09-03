"""Decoy · the starter, untouched. Somebody 'fixed' it by renaming a variable."""
from __future__ import annotations


def full_chain_recall(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    window = set(retrieved_ids[:k] if k else retrieved_ids)
    hits = sum(1 for chunk_ids in gold_map.values() if chunk_ids & window)
    return hits / len(gold_map)
