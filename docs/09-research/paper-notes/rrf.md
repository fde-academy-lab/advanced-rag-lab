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

**Transfers as a fusion rule. Does not transfer as a reason to fuse.**

`python scripts/run_eval.py --compare` — 243 questions, k=8 after the cross-encoder, paired
bootstrap:

| configuration | evidence_recall@8 | nDCG@8 |
|---|---|---|
| BM25 alone | 0.7118 | 0.3639 |
| Dense (LSA) alone | 0.7733 | **0.6055** |
| equal-weight RRF | **0.7742** | 0.5302 |
| weighted, α = 0.2 | 0.7645 | 0.4767 |
| weighted, α = 0.5 | **0.7790** | 0.5967 |

Two readings, and the second is the interesting one.

**RRF beats every alternative fusion rule and both individual systems on recall**, which is the
paper's claim, and it does it with no training and no normalisation, which is the paper's point.
`bm25 → rrf` is +0.0624 evidence recall, ci (+0.0407, +0.0857). Weighted fusion at the tuned
α = 0.2 does *not* beat it — it loses on nDCG by 0.0535, ci excluding zero. The parameter-free
rule wins against the parameterised one, exactly as advertised.

**And none of that was worth doing.** `dense → rrf` is +0.0008 evidence recall,
ci (−0.0101, +0.0109), and on nDCG the unfused dense leg beats RRF by 0.0753. The fused system
is inside the noise band of one of its own legs.

## Why the second reading is the real one

The paper's setup is fusion over **TREC runs**: multiple mature systems of broadly comparable
quality, which is to say systems that are *good in different ways*. That is the precondition, and
it is not "comparable strength" — it is **complementarity**. Two systems of identical strength
that fail on the same queries have one signal between them, and combining a signal with itself
returns the signal.

On Client Zero the legs are not complementary. The questions are paraphrase and inference over
incident prose; the dense leg handles nearly all of it and BM25 contributes on the exact-identifier
slice, which is real and small. RRF duly finds what the dense leg found, plus a little, minus some
ranking quality — because giving an equal ballot to a leg that is right less often costs
precision at the top even when it does not cost recall.

**k does not help.** At k=60 the gap between ranks 1 and 2 is about 2%, so k dampens how much a
single voter's *first preference* counts. It does not change how much a *voter* counts, and it
does it to both legs at once.

> **Corrected 2026-09-01.** This note previously reported that equal-weight RRF *loses* to BM25
> alone and that the LSA leg was materially weaker than BM25. Both are false — RRF beats BM25 by
> +0.0624 and LSA beats it by +0.0616. See
> [ADR-0015](../../01-architecture/adr/0015-correct-the-fusion-finding.md).

## What would change the answer

**A complementary pair of legs.** A modern sentence embedder alongside BM25 on a corpus with real
identifier traffic would give two systems that are good in different ways, which is the paper's
actual precondition. Then fusion should beat both legs rather than tying the better one. That is
a testable prediction and it is `EX-15`.

The measurement that decides it is not the aggregate table — it is the **per-query overlap of
failures** between the two legs. Disjoint failures mean fusion is worth a lot; nested failures
mean it is worth nothing. Nobody ran it before choosing, on either side of this correction.

**Non-stationary score distributions.** Where BM25's scale shifts per query but its ordering
stays sound — mixed languages, wildly varying document lengths — a globally-tuned α is wrong on
every individual query and rank-based fusion is robust to exactly that. RRF should win there.

## What we did with it

Weighted fusion at α = 0.2 remains the default, and the honest reason is administrative rather
than technical: `.github/eval-baseline.json` is cut from it, every headline number in the
repository is that configuration, and the alternatives are inside the noise band on the metrics
that matter. It is not the argmax — α = 0.5 measures better on both recall and nDCG — and
[ADR-0015](../../01-architecture/adr/0015-correct-the-fusion-finding.md) says so rather than
inventing a justification.

The finding we report is *"fusion does not separate from its better single leg here"*, with the
condition attached: it returns when the legs are complementary. A negative result without the
condition under which the expected outcome returns is an anecdote.
