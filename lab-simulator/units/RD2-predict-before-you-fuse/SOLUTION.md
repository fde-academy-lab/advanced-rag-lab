# RD2 · solution

| arm | evidence recall, k=8 |
|---|---|
| BM25 alone | 0.7118 |
| dense (LSA) alone | 0.7733 |
| equal-weight RRF | 0.7742 |

**The dense leg is the stronger one**, by +0.0616 evidence recall and +0.2416 nDCG. **Fusion
does not separate from it**: rrf − dense is +0.0008, ci (−0.0101, +0.0109), and on nDCG fusion is
a real regression against the unfused dense leg.

The mechanism is the corpus. Client Zero's questions are paraphrase and inference over incident
prose; BM25 has almost nothing to score. And the two legs fail on the same questions — of the
207 answerable, dense misses 95, lexical misses 102, and 92 of those are the same. There is
nothing for a merge to recover.

If you predicted BM25 ahead, you learned it from this repository's own deck, ADR-0003 or
ADR-0007 as originally written — all retracted on 2026-09-01. That is not embarrassing. It is
the point of a prediction drill: it finds the stale model you did not know you were carrying.

Command: `python scripts/run_eval.py --compare` · note: `docs/09-research/measurements/fusion-rules.md`
