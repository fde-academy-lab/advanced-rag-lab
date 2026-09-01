# Measurement · Is hybrid fusion worth building on Client Zero?

- **Date** 2026-09-01
- **Command** `python -m labsim check R3 --json`
- **Configuration** structural chunking, n=100 candidates per leg, equal-weight RRF at k=60,
  cross-encoder rerank, top 8 packed
- **Set** 207 answerable questions of 243. A leg "misses" a question when its reranked top 8 does
  not contain all of that question's gold evidence — partial recall on a multi-hop question is a
  failure of the question, not a partial success

## The table

| | value |
|---|---|
| fused evidence recall @8 | **0.7709** |
| dense leg alone, evidence recall @8 | 0.7673 |
| lexical leg alone, evidence recall @8 | 0.7226 |
| P(lexical also misses \| dense misses) | **0.9684** |

Counts behind the last row: dense missed 95 questions, lexical missed 102, both missed 92.

## What the intervals say

I did not compute a paired bootstrap inside this run, so I am not going to imply one. The
comparison that matters — fused against the dense leg alone — is **+0.0036 on 207 questions**,
and the repository's own comparison of the same two configurations through `run_eval.py
--compare` reports `dense -> rrf` at `+0.0008` with an interval of `(-0.0101, +0.0109)`, which
straddles zero.

So the honest statement is: the difference I measured is the same size as the difference already
known to be inside the noise band. I am not claiming a gain and I am not claiming a loss.

The more useful list here is the one that did **not** clear: fusion against the better single
leg, on every metric.

## What it means

The two legs' failures are **nested, not overlapping**. 92 of the 95 questions the dense leg
misses are also missed by BM25 — so the lexical leg reaches three questions out of 207 that the
dense leg cannot. Read the other way it is barely better: dense rescues 10 of BM25's 102 misses.

Fusion combines two signals into a better one only when the legs fail on different queries. Here
there is almost nothing for the second leg to add, because it is mostly re-finding what the first
leg already had. That is why the +0.0036 is not disappointing — it is exactly what a 96.8%
overlap predicts, and a fused system gaining five points here would have meant the overlap
measurement was wrong.

The mechanism behind the nesting is the corpus. These questions are paraphrase and inference over
incident prose, where the question and the passage share meaning and almost no vocabulary. BM25
scores term overlap; there is very little for it to score. Its genuine win is the exact-identifier
slice, and that slice is small enough to round to nothing in the aggregate.

## What this does not say

It does not say hybrid retrieval is a bad idea, and it does not generalise past this corpus.

Two changes would flip it. **A different dense encoder**: LSA is a stand-in, and a modern sentence
model would fail on a different set of questions — if those failures stop being nested inside
BM25's, fusion starts paying and this note is obsolete. **A different question mix**: if
identifier and exact-match traffic grows past roughly a fifth of queries, BM25's real win stops
being invisible in the aggregate and the arithmetic changes.

The measurement to re-run in either case is the overlap, not the aggregate recall — the aggregate
cannot distinguish disjoint failures from nested ones, which is the entire point of this note.
