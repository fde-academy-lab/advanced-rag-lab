# ED1 · solution

```python
return 1.0 if all(chunk_ids & window for chunk_ids in gold_map.values()) else 0.0
```

The starter computed `found / len(gold_map)`, which is **evidence recall** — the per-piece
metric. Full-chain recall is per question and has two values.

The reason the distinction is worth a drill: the two metrics disagree by thirty points on this
repository's committed baseline (0.7645 against 0.4686), and a system can improve the first
while the second falls. Gating on the one that can rise while the product gets worse is how a
regression ships behind a green dashboard. E1 builds both from scratch and measures the gap.
