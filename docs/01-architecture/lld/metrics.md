# LLD · `metrics.py`

Every number the project publishes comes from here, so a bug in this module is worse than a bug
anywhere else: it does not break the system, it changes what the system is believed to do.

## Contract

```python
def evidence_recall(results, gold, k) -> float          # per piece
def full_chain_recall(results, gold, k) -> float        # per question
def context_precision(results, gold, k) -> float
def ndcg(results, gold, k) -> float
def mrr(results, gold) -> float
def cohens_kappa(a: list[int], b: list[int]) -> float
def paired_bootstrap(a: list[float], b: list[float], n: int = 1000) -> tuple[float, float]
```

Each carries the failure it guards against in its docstring. If a number looks wrong, read the
docstring before the formula — the formula is usually right and the assumption is usually the
problem.

## The two recalls

The distinction the whole evaluation rests on.

```python
found = set(retrieved[:k]) & needed
evidence = len(found) / len(needed)          # per piece
chain    = 1.0 if needed <= set(retrieved[:k]) else 0.0   # per question
```

If retrieval events were independent with probability *p*, a question needing *j* pieces would
clear full-chain with probability *pʲ*. The eval set is a mixture, so the comparison has to be
too — using *p²* alone assumes every question is two-piece and understates the expected value:

| pieces | n | *pʲ* at *p* = 0.7645 |
|---|---|---|
| 1 | 128 | 0.7645 |
| 2 | 61 | 0.5845 |
| 3 | 18 | 0.4468 |

Weighted over the 207 answerable questions, independence predicts **0.6838**. Measured:
**0.4686** — a shortfall of 0.215, not the 0.116 that the naive *p²* comparison implies.

The shortfall is the diagnosis. Hop-1 evidence resembles the query; hop-2 evidence resembles the
*answer to hop 1*. Widening k returns more hop-1 and leaves hop-2 flat:

| | N = 20 | N = 200 |
|---|---|---|
| hop-1 recall | 0.88 | 0.94 |
| hop-2 recall | 0.54 | 0.55 |

## `paired_bootstrap`

```python
d = [a_i - b_i for a_i, b_i in zip(a, b)]
samples = [mean(random.choices(d, k=len(d))) for _ in range(n)]
return percentile(samples, 2.5), percentile(samples, 97.5)
```

**Paired**, because query difficulty varies enormously and swamps the between-system variance
that is being measured. Resampling the differences removes it — a query both systems ace
contributes zero and adds no noise. Unpaired comparison on the same query set gives intervals
several times wider, which is how a real improvement gets called insignificant.

**Over queries, not documents.** The query is the unit of independence. Documents within one
result list were selected by the same retriever; resampling them understates variance and
produces intervals that are too narrow — the more dangerous error.

**1,000 resamples** is where the percentile bounds stop moving in the third decimal *on this
dataset, for a 95% interval*. Both qualifiers matter. Required B scales with how extreme a
quantile you want: at 99% the tail is estimated from a tenth as many samples and 1,000 is not
enough. Change the confidence level and B has to be revisited.

## `cohens_kappa`

Reports κ, and callers are expected to report the marginals alongside it. On a skewed label
distribution κ is brutal for reasons unrelated to rater quality: at 90/10 marginals, 85%
agreement gives κ = 0.167.

The module deliberately does **not** hide this behind a "corrected" variant. A statistic that
looks reassuring on skewed data is worse than one that looks alarming, because the alarm is
correct — the raters genuinely have not demonstrated much beyond following the base rate.

## The memoisation that made evaluation 4× faster

Profiling showed `resolve_gold` re-normalising all 2,430 chunks for every question — 60,898
`re.sub` calls per run.

```python
_NORM_CACHE = {}


def _normed_chunks(chunks):
    key = id(chunks)
    entry = _NORM_CACHE.get(key)
    if entry is not None and entry[0] is chunks and len(entry[1]) == len(chunks):
        return entry[1]
    normed = [(c.chunk_id, _norm(c.text)) for c in chunks]
    if len(_NORM_CACHE) > 4:
        _NORM_CACHE.clear()
    _NORM_CACHE[key] = (chunks, normed)
    return normed
```

Three details, each deliberate:

**Keyed on `id(chunks)` and validated by identity.** `id()` is reused after garbage collection,
so the key alone is unsafe. The `entry[0] is chunks` check makes a stale key a miss rather than
a wrong answer.

**Length checked too.** Catches in-place mutation of a list whose identity has not changed.

**Cleared past four entries** rather than evicted by LRU. Evaluation holds at most two or three
chunk lists at a time; a real cache here would be more code guarding against a case that does
not occur.

Result: 40 s → 9.7 s, **byte-identical metrics**. That last part is the acceptance criterion —
an optimisation that changes a published number is not an optimisation.

## Failure modes

| Symptom | Cause |
|---|---|
| Recall improves after an unrelated refactor | Gold resolution loosened. Assert byte-identical metrics on any change here |
| Interval suspiciously narrow | Resampled documents rather than queries |
| Interval suspiciously wide | Unpaired comparison |
| κ near zero with high agreement | Skewed marginals. Working as intended; report both |
| Metrics move between runs | Something is unseeded. Every random path here takes an explicit seed |

## What would change this design

**Graded relevance.** Everything here is binary — a chunk is gold or it is not. Graded judgements
would change nDCG's numerator to `2^rel − 1` and make the gold structure heavier.

**More than a few thousand chunks.** The memoisation assumes the whole normalised list fits in
memory comfortably. At 10⁶ chunks, gold resolution wants an index rather than a scan.
