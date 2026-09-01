# Measurement · Is hybrid fusion worth building on Client Zero?

- **Date** 2026-09-01
- **How it was produced** ran the R3 grader locally against the full corpus and read the metrics
  off the JSON output
- **Configuration** structural chunking, n=100 per leg, equal-weight RRF at k=60, cross-encoder
  rerank, top 8 packed
- **Set** 207 answerable questions of 243, a miss being an incomplete reranked top 8

## The table

| | value |
|---|---|
| fused evidence recall @8 | **0.7709** |
| dense leg alone | 0.7673 |
| P(lexical also misses \| dense misses) | **0.9684** |

## What the intervals say

The repository's own comparison of these two configurations reports `(-0.0101, +0.0109)` on the
fused-against-dense difference, which straddles zero. I am not claiming a gain.

## What it means

The failure sets are nested rather than overlapping: 92 of the dense leg's 95 misses are also
lexical misses, so the second leg reaches almost nothing the first did not. Fusion pays only
when the legs fail on different queries, and these fail together.

## What this does not say

Conditional on this encoder and this question mix. If a different dense model's failures stop
being nested inside BM25's, fusion would start paying and this note would be obsolete.
