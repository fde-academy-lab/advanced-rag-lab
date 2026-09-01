# Evaluation protocol

The rules a measurement follows here. They exist because each one has been violated at least
once in this repository's history, and each violation produced a number somebody believed.

## The dataset

243 questions over 484 documents and 2,430 chunks, generated from a fact graph.

| Slice | n | Why it exists |
|---|---|---|
| Single-hop factoid | 96 | The baseline case |
| Multi-hop (2 pieces) | 61 | Where full-chain recall separates from evidence recall |
| Multi-hop (3+) | 18 | Where single-shot retrieval structurally cannot win |
| Identifier / error code | 24 | Where tokenisation decides the outcome |
| Temporal ("as of Q3") | 20 | Where the right document is the wrong version |
| Unanswerable (null) | 36 | Where abstention is the correct answer |
| ACL-restricted | 15 | Where the right document exists and must not be returned |

**Gold evidence is true by construction.** The generator knows which documents carry each fact,
so there is no annotator and therefore no annotation-error floor. When a metric moves, the
system changed.

## The split

| Portion | Size | Rule |
|---|---|---|
| Dev | 85% | Tune freely. Fit reranker weights here |
| **Frozen** | **15%** | **Touched once, at the end.** Never used for tuning, thresholds, or model selection |

The frozen slice exists because of a specific failure: fit twenty variants against a dev set at
95% confidence and one clears by chance. The frozen slice is the only defence, and it works
exactly once — the first time you look at it. Looking twice makes it a second dev set.

**If you look at it, say so.** A number from a peeked slice is a dev number, and reporting it as
frozen is the one form of dishonesty this protocol cannot detect automatically.

## The rules

**1 · Any change that could move a number ships with the number.**
Before, after, delta, and a 95% interval from `metrics.paired_bootstrap`.

**2 · A delta inside the noise band is reported as inside the noise band.**
Not rounded into a win, not described as "a trend", not shipped with "directionally positive".

**3 · One change per comparison.**
A run that alters chunking *and* reranking cannot attribute either. Two runs.

**4 · The eval set and the system never change in the same commit.**
If they do, the delta is uninterpretable and no statistics repair it. This is the reason for the
rule, not a style preference.

**5 · Report n, always.**
A metric without its denominator is not reportable. A per-slice score without a per-slice count
is worse — it invites conclusions from six questions.

**6 · State k.**
Recall rises with k trivially. A recall number without k is not a number.

## Significance

Paired bootstrap over queries, 1,000 resamples, percentile interval.

**Paired**, because query difficulty varies enormously and that variance swamps the
between-system variance you care about. Resampling differences removes it — a query both
systems ace contributes zero.

**Over queries, not documents**, because the query is the unit of independence. Documents within
one result list were selected by the same retriever; resampling them understates variance and
produces intervals that are too narrow, which is the more dangerous error.

Three things it does not cover, and they should be stated whenever the interval is:

- **Annotation error.** Not applicable here — gold is constructed — but it is the usual ceiling
  elsewhere.
- **Multiple comparisons.** Twenty variants at 95%, one clears by chance. Correct for it or use
  the frozen slice.
- **Non-stationarity.** The interval assumes the query sample represents the traffic you care
  about. On a synthetic corpus it represents the generator.

## What invalidates a run

| Condition | Why |
|---|---|
| Eval set changed in the same commit as the system | Delta is uninterpretable |
| Frozen slice used for any tuning decision | It is now a dev set, permanently |
| Judge or judge prompt changed without a version bump | The metric changed, not the system |
| Index contains more than one embedder version | Cosine across two embedding spaces is meaningless *and silent* |
| Reranker weights refitted on the comparison set | Fitting and evaluating on the same data |
| k differs between arms | You compared two things at once |

The last four are checked automatically — see `tests/` and `scripts/run_eval.py`. The first two
cannot be, which is why they are written down.

## Reproducing a number

```bash
make eval                      # the scorecard
python scripts/run_eval.py --baseline   # rewrite the committed baseline (deliberate act)
```

Every number in the README and in the notebooks comes from this path. If one disagrees with the
docs, the number is right and the docs have drifted — open an issue, that is a real defect.
