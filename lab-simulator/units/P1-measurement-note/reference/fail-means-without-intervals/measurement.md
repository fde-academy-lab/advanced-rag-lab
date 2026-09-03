# Measurement · Is hybrid fusion worth building on Client Zero?

- **Date** 2026-09-01
- **Command** `python -m labsim check R3 --json`
- **Configuration** structural chunking, n=100 per leg, equal-weight RRF at k=60, cross-encoder
  rerank, top 8 packed
- **Set** 207 answerable questions of 243, a miss being an incomplete reranked top 8

## The table

| | value |
|---|---|
| fused evidence recall @8 | **0.7709** |
| dense leg alone | 0.7673 |
| lexical leg alone | 0.7226 |
| P(lexical also misses \| dense misses) | **0.9684** |

## What the intervals say

Fusion comes out ahead of the dense leg alone, 0.7709 against 0.7673. It is a small lead but it
is consistent, and fusion also comfortably beats the lexical leg. On that basis the fused
configuration is the better of the three.

## What it means

The failure sets are heavily nested — 92 of the dense leg's 95 misses are also lexical misses —
so the lexical leg is largely re-finding what the dense leg already had rather than reaching
different queries. Fusion needs complementary legs to pay, and these are not complementary.

## What this does not say

This is conditional on the encoder. If the dense leg is replaced and its failures stop being
nested inside BM25's, the answer would change.
