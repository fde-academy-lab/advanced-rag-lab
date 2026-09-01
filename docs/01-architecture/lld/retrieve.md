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

Equal-weight RRF **loses to BM25 alone** here. Weighted at α = 0.2 wins:
evidence recall 0.7645 → 0.7891, [+0.008, +0.041], holding on frozen.

The mechanism: RRF is a voting rule that treats both voters as equally credible. Fusing a strong
leg with a weak one at equal weight moves the result toward the weak one. Scale-invariance is a
virtue when the legs are comparable and a liability when they are not, because it discards the
score distribution — the one signal that would have told you to down-weight the weak leg.

**α = 0.2 is fitted to this corpus and this encoder.** It is not a recommendation.

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

Fitted to this corpus with this encoder. Two of them are worth noticing, because they are
counter-intuitive and both are real:

- **`phrase` is negative.** Exact phrase matches in this corpus are more often boilerplate than
  evidence — every incident report repeats the same stock sentences.
- **`maxsim` is near zero and slightly negative** while `doc_cosine` is the largest positive
  weight. Document-level semantic similarity carries the dense signal here; token-level MaxSim
  adds almost nothing on top of it once `doc_cosine` is present. That is a statement about this
  encoder, not about late interaction.

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
