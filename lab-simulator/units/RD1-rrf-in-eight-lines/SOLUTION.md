# RD1 · solution

```python
for rank, hit in enumerate(leg, start=1):
    scores[hit.chunk_id] = scores.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
```

**Blank 1 is `start=1`.** `enumerate` counts from zero and rank zero is not a rank. With the
default `k=60` the damage is small — rank 1 scores `1/60` instead of `1/61` — and the fused
order is nearly right, which is exactly why this version gets shipped and stays shipped until a
third leg of a different length exposes it.

**Blank 2 is `1.0 / (k + rank)`.** The other plausible fill is `max(scores.get(...), 1/(k+rank))`
— keep each chunk's best single-leg score — and it throws away the one thing RRF rewards, which
is a chunk that *several* retrievers agree on.

The intersection decoy is the third common mistake and it is not a blank: it is a `set` line
somebody adds "for precision". It removes every chunk that only one leg found, which is the
entire reason for having two legs. R3 measures what that costs on the real corpus.
