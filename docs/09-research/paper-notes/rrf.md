# Reciprocal Rank Fusion — Cormack et al., 2009

**Paper:** *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods*,
SIGIR 2009.

## Claim

Fusing ranked lists by `Σ 1/(k + rank)`, with k ≈ 60, outperforms both the individual systems and
more elaborate fusion methods — without any training or score normalisation.

## Method

Fusion over TREC runs: multiple mature retrieval systems of **broadly comparable quality**,
evaluated on standard collections. That last property is doing more work than it appears to.

## What we tested

BM25 and an LSA dense retriever, fused with equal-weight RRF, against each leg alone and against
weighted score fusion. Evidence Recall@8, paired bootstrap, verified on the frozen slice.

## Result

**Equal-weight RRF loses to BM25 alone.** Weighted fusion at α = 0.2 wins:

| configuration | evidence_recall@8 |
|---|---|
| BM25 alone | 0.7645 |
| equal-weight RRF | below BM25 at every k |
| weighted, α = 0.2 | **0.7891**, [+0.008, +0.041], holds on frozen |

## Why it did not transfer

The precondition is comparable leg strength, and it is absent here.

RRF is a **voting rule that treats every voter as equally credible.** Fuse a strong leg with a
weak one at equal weight and the result moves toward the weak one. Scale-invariance — the property
that makes RRF work without normalisation — is exactly what discards the score distribution that
would have told you to down-weight the weak leg.

The LSA dense leg on this corpus is materially weaker than BM25. Rank-parity is therefore the
wrong prior, and no value of k fixes it, because k controls how much a single voter's *first
preference* counts, not how much a *voter* counts.

## What would change the answer

**A stronger dense leg.** A modern sentence embedder would likely bring the legs to comparable
strength, and the paper's result should return. That is a testable prediction and it is one of
the extension points.

**Non-stationary score distributions.** Where BM25's scale shifts per query but its ordering
stays sound — mixed languages, wildly varying document lengths — a globally-tuned α is wrong on
every individual query and rank-based fusion is robust to exactly that. RRF should win there.

## What we did with it

Weighted fusion is the default; α is a tuned parameter rather than an assumption. The result is
one of the three headline findings, and it is reported with the condition attached — a negative
result without the condition under which the expected outcome returns is an anecdote.
