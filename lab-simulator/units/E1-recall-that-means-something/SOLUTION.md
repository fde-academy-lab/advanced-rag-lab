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

**0.7645 → 0.4686.** If pieces failed independently, a question with `h` hops resolves with
`p^h`. Over Client Zero's answerable mix — 128 single-hop, 61 two-hop, 18 three-plus —
independence predicts:

```
(128·0.7645 + 61·0.7645² + 18·0.7645³) / 207 = 0.6838
```

Measured is 0.4686, which is **21 points below** the independence prediction. Failures are
positively correlated within a question: when one hop is missed, the others are more likely to be
missed too.

That single number changes the roadmap. Uncorrelated failures would mean "retrieval is uniformly
a bit weak" and the fix is a uniformly better retriever — more candidates, better embeddings,
budget. Correlated failures mean **some questions are hard in a structural way and most are
fine**, and the fix is to find what those questions share. On Client Zero it was two things:
questions whose entities appear only in the document *title* (which the structural chunker
strips into metadata), and questions requiring a hop through an acronym never expanded in the
same chunk as its expansion.

Neither is a retriever problem. Both are indexing problems, and both are cheap to fix once
named.

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

**We computed the independence prediction with `p²` for everything.** Off by half. The corpus is
62% single-hop, so `p²` describes a minority of it. The prediction came out 0.5845 against a
measured 0.4686 — a 12-point gap — and we concluded the correlation was mild. With the real
mixture the gap is 21 points and the conclusion is the opposite.

Two things came out of checking it. First: **weight by the actual distribution, always.** Second,
and worse — reconciling the hop counts exposed that the slice table summed to 270 against 243
questions, because `identifier`, `temporal` and `acl` are cross-cutting *attributes* rather than
mutually exclusive types. A slice table whose rows do not partition anything cannot be read as
percentages, and everyone had been reading it as percentages.

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
