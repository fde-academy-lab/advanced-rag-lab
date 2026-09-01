# E1 · How we did it

```python
def evidence_recall_at_k(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    return sum(1 for cids in gold_map.values() if cids & got) / len(gold_map)


def full_chain_recall(retrieved_ids, gold_map, k=None):
    if not gold_map:
        return None
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    return 1.0 if all(cids & got for cids in gold_map.values()) else 0.0


def ndcg_at_k(retrieved_ids, gold_map, k=10):
    if not gold_map:
        return None
    items = list(gold_map.values())
    dcg, seen = 0.0, set()
    for i, cid in enumerate(retrieved_ids[:k], 1):
        for j, cids in enumerate(items):
            if j not in seen and cid in cids:
                dcg += 1.0 / math.log2(i + 1)
                seen.add(j)
                break
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(items), k) + 1))
    return dcg / ideal if ideal else None
```

## Why `dict[str, set[str]]` and not a flat set

This is the decision the whole unit rests on, and it is a *modelling* decision that happens to
live in a type signature.

A flat set of gold chunk ids conflates two different things: **the evidence you need** and **the
chunks that could supply it**. Once they are the same object, a retriever that returns three
near-duplicates of hop A looks identical to one that found hop A and hop B. Those systems have
completely different failure profiles and one of them can answer the question.

The nesting says: *keys are conjunctive, values are disjunctive.* You need every key. Any member
of a value will do. That is the shape of multi-hop evidence, and every metric here is one line
once the shape is right.

It is also the shape that makes the empty case meaningful. `gold_map == {}` is not "we found
nothing"; it is "there is nothing to find", which is a different question and needs a different
answer. Returning `None` and excluding it from the mean is the whole reason abstention can be
evaluated at all — see `raglab/metrics.py:abstention_scores`.

## Self-normalising nDCG, in one example

Three gold pieces. The retriever returns `["a1", "zz", "yy"]` — one hit at rank 1, then noise.

| | DCG | IDCG | nDCG |
|---|---|---|---|
| Correct | `1/log₂2` = 1.000 | `1/log₂2 + 1/log₂3 + 1/log₂4` = 2.131 | **0.469** |
| Normalised against what was found | 1.000 | `1/log₂2` = 1.000 | **1.000** |

The second row is a metric that reports a perfect score for a system that found one third of the
evidence. It cannot go down, because the denominator moves with the numerator.

What makes it dangerous rather than merely wrong: **the two definitions agree exactly whenever
the system is doing well.** Every case anybody checks by hand is a case where everything was
found, and there the ideal ranking *is* what was found. It diverges only when retrieval is
struggling, which is precisely the regime the number was commissioned to monitor.

The general rule worth taking: a metric whose denominator depends on the system's own output is
not a metric, it is a self-assessment. Check every normalisation you write for this.

## The gap, and what it licenses you to say

```
evidence_recall@8     0.7645        pieces found
full_chain_recall@8   0.4686        questions fully resolved
answer_correct        0.4115        answers actually right
```

**0.7645 → 0.4686.** If pieces were retrieved independently, a question needing `k` of them
resolves with `p^k`. The exponent is the count of **gold evidence pieces** — `len(gold_map)` —
not the hop count, because that is exactly what `full_chain_recall` requires. Over Client Zero's
real distribution:

```
python scripts/independence.py

  pieces   questions          p^k
      1          21        0.7645
      2          59        0.5845
      3          21        0.4469
      4         100        0.3416
      6           6        0.1997

  weighted prediction  0.4603
  measured             0.4686      +0.0083
```

Measured is **at** independence. There is no shortfall.

That is the finding, and it is a negative one with a decision attached. Below independence would
mean failures cluster inside a question — some structurally hard, most fine — and the work is to
find what the hard ones share. At independence means there is nothing to find: the whole gap
between 0.7645 and 0.4686 is the arithmetic of needing four pieces at 76% each, and a quarter
spent hunting the hidden cause is a quarter spent on something that does not exist.

Worth stating what it does *not* say. Correlated failure is common and real; on a corpus whose
evidence clusters by document you would expect it. It is not happening here, and the likely
reason is visible in the corpus generator: the fact graph spreads a question's evidence across
documents by construction, so a retriever that fails a document does not thereby fail the whole
chain.

**0.4686 → 0.4115.** The remaining six points are generation: the evidence was all present and
the answer was still wrong. That is the ceiling on what retrieval work can buy you, and knowing
it is what stops a quarter being spent in the wrong place.

If you take one habit from this unit, take that decomposition. Three numbers, two gaps, and each
gap points at a different team.

## What we got wrong first

**We reported evidence recall for two months.** It was the friendliest of the three and nobody
was being dishonest — it is the standard IR metric and the one every paper prints. The customer's
experience tracked `answer_correct`, thirty-five points lower, and every conversation about
quality started with the two sides describing different systems.

The fix was not a better metric. It was reporting **all three, always, in that order**, so the
gaps are visible and someone has to explain them. `raglab/tables.py:scorecard` is that table, and
`scripts/run_eval.py` cannot print one number without the other two.

**We computed it over hops, against a mixture that did not exist.** The published version read
*"128 single-hop, 61 two-hop, 18 three-plus → predicts 0.6838 → measured 0.4686 → 21 points
below independence → failures are correlated"*. Every step after the first is downstream of the
first, and the first was wrong twice: the corpus reports no such mixture (the `hops` field says
77 and 130), and `full_chain_recall` does not exponentiate hops — it exponentiates **pieces**.

Corrected, the prediction is 0.4603 and measured is *above* it. The finding did not shrink; it
reversed.

Two things came out of checking it. **Exponentiate the quantity the metric actually requires** —
`len(gold_map)`, which you can print in one line, rather than a field that sounds like it means
the same thing. And: a derived number needs a command that regenerates it. `p^k` weighted over a
distribution is four lines of arithmetic that nobody re-does, so it became
`scripts/independence.py`, and `tests/test_measurements.py` fails if the documentation drifts
from what that command prints.

## Where this lives in the real system

`raglab/metrics.py` — these three plus `mrr`, `context_precision`, `citation_accuracy`,
`abstention_scores`, `cohens_kappa` and `paired_bootstrap`.

The last one is what stops you shipping noise. A 2-point recall delta on 243 questions is inside
the bootstrap interval, so it is not a result — [ADR-0008](../../../docs/01-architecture/adr/0008-eval-gate-in-ci.md)
is the policy that makes the eval gate enforce that, and
[ADR-0007](../../../docs/01-architecture/adr/0007-report-negative-results.md) is why the
independence finding is published rather than filed.

## What this unlocks

**R3** implements the fusion rule you committed to in R2 and measures it with these functions
against a bar on the real corpus. **D1** hands you a reranker that improves one of these numbers
while making the system worse, and asks which one is lying.
