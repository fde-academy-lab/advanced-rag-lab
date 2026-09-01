# Measurement · Is hybrid fusion worth building on Client Zero?

- **Date** 2026-09-01
- **Command** `python -m labsim check R3`
- **Configuration** structural chunking, n=100 per leg, equal-weight RRF at k=60, cross-encoder
  rerank, top 8 packed
- **Set** 207 answerable questions of 243, a miss being an incomplete reranked top 8

## The table

| | value |
|---|---|
| fused evidence recall @8 | **0.7745** |
| dense leg alone | 0.7690 |
| P(lexical also misses \| dense misses) | **0.9520** |

## What the intervals say

The fused-against-dense difference is small and I would not ship on it. The repository's own
`--compare` run puts the same comparison at `(-0.0101, +0.0109)`, straddling zero.

## What it means

The two legs' failures are heavily **nested**: almost every question the dense leg misses is also
missed by the lexical leg, so there is very little for fusion to add. It is mostly re-finding what
the first leg already had rather than reaching different queries.

The mechanism is the corpus — paraphrase and inference over prose, where term overlap has almost
nothing to score, so the lexical leg contributes only on the small exact-identifier slice.

## What this does not say

It does not generalise. If the dense encoder changes and its failures stop being nested inside
BM25's, fusion starts paying and this note is obsolete. The same happens once identifier traffic
grows past roughly a fifth of queries.
