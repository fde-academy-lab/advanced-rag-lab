# LLD · `retrieve.py`

Candidate generation, fusion, and the reranker. The module where the most measured-and-wrong
decisions live.

## Contract

```python
@dataclass
class RetrievalConfig:
    n_candidates: int = 100
    k: int = 8
    fusion: str = "rrf"          # bm25 | dense | rrf | weighted
    rerank: str | None = "cross"  # None | lexical | cross
    alpha: float = 0.5            # weighted fusion only: share given to the dense leg


def retrieve(query: str, cfg: RetrievalConfig) -> list[Hit]
```

`n_candidates` is what the first stage returns; `k` is what survives to the context. Conflating
them is the most common configuration error, because widening `n` is nearly free and widening
`k` costs context budget.

## Fusion

**RRF.** `score = Σ 1/(60 + rank)`. Scale-free, so it can fuse a BM25 score with a cosine
without normalising anything. `k = 60` dampens the top rank's authority: the gap between ranks 1
and 2 is ~2%, so agreement across systems outranks confidence within one.

**Weighted.** `score = (1 - α)·norm(bm25) + α·norm(dense)`, min-max normalised per query.

### The measured result

`python scripts/run_eval.py --compare`, 243 questions, `k = 8` after the cross-encoder, paired
bootstrap over questions:

| Configuration | Evidence recall@8 | nDCG@8 | Answer correct |
|---|---|---|---|
| BM25 alone | 0.7118 | 0.3639 | **0.4156** |
| Dense (LSA) alone | 0.7733 | **0.6055** | 0.3992 |
| Equal-weight RRF | 0.7742 | 0.5302 | 0.4033 |
| Weighted α = 0.2 | 0.7645 | 0.4767 | 0.4115 |
| Weighted α = 0.5 | **0.7790** | 0.5967 | 0.3992 |

Both fusion rules beat BM25 alone decisively — `bm25 → rrf` is +0.0624 evidence recall,
ci (+0.0407, +0.0857). **Neither beats the dense leg on its own.** `dense → rrf` is +0.0008 with
an interval of (−0.0101, +0.0109), and on nDCG the unfused dense leg wins by 0.075.

The mechanism is complementarity, not weighting. Fusion combines two signals into a better one
only when the legs fail on different queries; two retrievers that fail together carry one signal
between them. On this corpus BM25 is the weak leg — the questions are paraphrase and inference
over incident prose, where term overlap has almost nothing to score — and it adds little the
dense leg had not already found. Its genuine win is the exact-identifier slice (`PagerDuty-4471`,
`ap-southeast-2`), which is real and small, and which the aggregate hides.

**α = 0.2 is fitted to this corpus and this encoder, and it is not even the argmax** — α = 0.5
measures better on both evidence recall (+0.0145, real) and nDCG (+0.1200, real). It is retained
because `.github/eval-baseline.json` is cut from it and the alternatives are inside the noise
band on the metrics that matter. It is not a recommendation.

> **Corrected 2026-09-01.** This section previously stated that equal-weight RRF *loses* to BM25
> alone and that weighted α = 0.2 wins. Neither reproduces. See
> [ADR-0015](../adr/0015-correct-the-fusion-finding.md) and
> [the measurement note](../../09-research/measurements/fusion-rules.md).

## The reranker

Eight pair features, weights fitted by logistic regression on the dev slice.

```python
PAIR_FEATURES = ("coverage", "proximity", "phrase", "title", "maxsim",
                 "doc_cosine", "exact_id", "length")
```

### Why it is learned and not hand-tuned

The first version had six lexical features and hand-tuned weights. It made retrieval **worse at
every k** — evidence recall 0.773 → 0.630 at k=5.

Uniformly-worse is diagnostic. A wiring bug is catastrophic; a weak reranker is roughly neutral.
Systematically slightly worse means the reranker is working correctly and preferring the wrong
thing.

The cause: the first stage was a *fused* list that had used dense signal. The reranker's features
were all lexical. So it was applying a strictly less-informed ordering on top of a
better-informed one — it could only discard information. No weight vector fixes that; a grid
search over 400 combinations never beat the baseline.

**Fix:** add genuinely pairwise semantic features (`maxsim`, `doc_cosine`) so the reranker sees
what the dense leg saw, then fit rather than guess. +8 points of evidence recall, holding on
frozen. ADR-0005.

### The weights, and why they must not be quoted

```python
DEFAULT_CROSS_WEIGHTS = {
    "coverage": 1.1148, "proximity": 0.1382, "phrase": -0.5067, "title": 0.5836,
    "maxsim": -0.0590, "doc_cosine": 1.2589, "exact_id": 0.6051, "length": -0.7266,
    "bias": -0.7722,
}
```

**These are point estimates with no uncertainty attached, and that is a real limitation.** The
fit reports coefficients only — no standard errors, no intervals. A coefficient printed to four
decimal places reads as a precise finding whether or not it is one, and at least one of these
almost certainly is not: `maxsim` at −0.0590 is small enough that it would very likely not
separate from zero given an interval, which would make it a coefficient that did nothing rather
than a small negative effect.

Adding bootstrap intervals to the coefficients is tracked; until they exist, read the two large
ones as findings and the small ones as noise. Two are worth noticing:

- **`phrase` is negative.** Exact phrase matches in this corpus are more often boilerplate than
  evidence — every incident report repeats the same stock sentences.
- **`maxsim` is near zero** while `doc_cosine` is the largest positive weight. The honest reading
  is that document-level semantic similarity carries the dense signal here and token-level MaxSim
  adds nothing measurable once `doc_cosine` is present — *not* that MaxSim hurts. The sign on a
  coefficient this small is not information. That is a statement about this encoder, not about
  late interaction.

Neither generalises. Quoting these numbers anywhere else would be citing an artefact.

## Complexity

| Stage | Cost |
|---|---|
| BM25 candidates | O(\|q\| · posting length) |
| Dense candidates | O(N·d) exact, O(ef·log N) approximate |
| Fusion | O(n log n) |
| Rerank | O(n · F) with F = 8 features; cheap because the features are, not because reranking is |

A neural cross-encoder at seam ⑦ replaces that last row with n forward passes and dominates
everything. The interface does not change; the latency budget does.

## Failure modes

| Symptom | Likely cause |
|---|---|
| Rerank worse at every k | Feature set less informed than the first stage |
| Rerank worse only at small k | Genuinely weak reranker; may still help at large k |
| Fusion worse than either leg | Equal weight over legs of unequal strength |
| Recall flat as `n_candidates` grows | First stage already returns everything relevant; widen k or fix the query, not n |

## What would change this design

**A real cross-encoder.** Then the learned linear model is a baseline to beat rather than the
mechanism, and the interesting question becomes when to *route* to it — running it only where the
first-stage score gap is small, which is where reranking changes the outcome.

**Per-query α.** A global fusion weight tuned on average behaviour is wrong on every individual
query. Routing α by query class is issue #11 and is written as a falsifiable hypothesis.
