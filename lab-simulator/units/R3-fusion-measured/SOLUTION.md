# R3 · How we did it

```python
def rrf(legs, k=60):
    agg, keep = {}, {}
    for leg in legs:
        for rank, hit in enumerate(leg, start=1):
            agg[hit.chunk_id] = agg.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
            keep.setdefault(hit.chunk_id, hit)
    return [keep[cid] for cid, _ in sorted(agg.items(), key=lambda kv: -kv[1])]


def failure_overlap(dense_misses, lexical_misses):
    if not dense_misses:
        return 0.0
    return len(dense_misses & lexical_misses) / len(dense_misses)
```

Nine lines and three lines. Then the run:

```
207 answerable questions · dense missed 95 · lexical missed 102 · both missed 92

evidence_recall   0.7709      (bar 0.7700)
failure_overlap   0.9684      (bar 0.9000)
```

## The number

**96.8% of the questions the dense leg misses are also missed by BM25.**

Ninety-two of ninety-five. The lexical leg reaches *three* questions the dense leg cannot, out of
207. Read the other direction it is barely better: dense rescues 10 of BM25's 102 misses.

The failure sets are not two overlapping circles. They are one circle with a fringe.

That is the whole fusion argument, settled, in a run that takes seven seconds and a function
that takes three lines. In R2 you read a table, weighed a mechanism, and reasoned about voting
rules — and the entire debate was decidable in advance by a quantity nobody computed.

This is worth sitting with, because it is not an argument for skipping the reasoning. The
reasoning in R2 is what tells you *this* is the quantity to compute. Someone without it measures
aggregate recall in nine configurations and still cannot say whether to fuse. The reasoning
chooses the measurement; the measurement ends the argument. Neither one alone gets there.

## Why the two numbers are consistent

Fused evidence recall is 0.7709 against the dense leg's 0.7673 — **+0.0036**, on 207 questions,
with a failure overlap of 0.968.

Those facts are the same fact. If BM25 rescues 3 questions out of 95 dense misses, the ceiling on
what fusion can add is about `3/207 ≈ 0.014` of full-question recall, and per-piece recall moves
less than that because most of the rescued questions are partially recovered rather than
completed. +0.0036 is what a 96.8% overlap *predicts*. A fused system that gained 5 points here
would mean the overlap measurement was wrong.

That consistency check is the habit to keep: when you have two numbers about the same system,
one of them should be predictable from the other, and checking that they are is the cheapest bug
detector available. It is also how the wrong fusion finding in this repository would have been
caught years earlier — "RRF loses to BM25" is not consistent with any failure-overlap value.

## Conditional, not Jaccard

The graded decoy computes

$$J = \frac{|D \cap L|}{|D \cup L|} = \frac{92}{105} = 0.876$$

against the correct

$$P(L \mid D) = \frac{|D \cap L|}{|D|} = \frac{92}{95} = 0.968$$

Nine points apart, and the smaller one is the more comfortable. Jaccard answers *"how similar are
these two failure sets?"*, which is a question about the sets. The decision needs *"given that
the leg I am going to ship missed this question, is the other leg any help?"*, which is a
question about **one** of them, and is asymmetric on purpose: `P(L|D) = 0.968` and
`P(D|L) = 0.902` are both true and they mean different things. Which one you want depends on
which leg you are about to ship alone.

If you find yourself reaching for a symmetric measure when the decision is asymmetric, that is
usually the tell that you have swapped the question for a nearby one that has a library function.

## The `enumerate(leg, start=1)` bug, and why the check pins it with `k=0`

Starting at 0 makes the top hit score `1/k` and the second `1/(k+1)`. At `k=60` those are
`0.016667` and `0.016393` — a 1.7% difference, on two legs of equal length, shifting both legs
identically. The aggregate metric moves by a rounding error. Every test anyone writes by hand
passes.

It becomes real when the legs are different lengths, or when a pre-filter truncates one, because
then the shift is no longer symmetric and the fusion acquires a bias toward the shorter list. The
symptom is an unexplained regression six weeks downstream of the commit that caused it.

So the check does not compare floats at `k=60`. It calls your `rrf` with **`k=0`**, where a
`start=1` implementation scores rank 1 at `1/1` and rank 2 at `1/2`, and a `start=0`
implementation divides by zero. An exact, unmistakable discriminator instead of a tolerance —
and generally the better move: when a bug is invisible at the default parameter, find the
parameter value where it is not.

## Why the fusion uses the position, not `hit.rank`

`hit.rank` was computed by whatever produced the leg. The ACL pre-filter
([ADR-0011](../../../docs/01-architecture/adr/0011-prefilter-acl.md)) drops chunks a persona may
not see, and if it drops them *after* ranking, the surviving `rank` values have gaps. Fusion
scores then shift for a reason that is invisible in the fusion's own diff.

The general rule: **a function that computes a score should derive its inputs from data it can
see, not from a field it is trusting somebody else to maintain.** The one-word fix is
`enumerate`, and it makes the function correct under every upstream change.

## What we got wrong first

**We measured the overlap on the un-reranked legs.** The first-stage candidate sets are 100 deep
and both legs contain almost everything, so the overlap came out near 1.0 and looked like a
degenerate measurement rather than a finding. The misses that matter are the ones that survive
reranking into the top 8 — which is where the question is actually decided. Measure the failure
at the stage the user experiences it, not at the stage that is convenient to instrument.

**We used `evidence_recall == 0` as the definition of a miss.** That counts a three-hop question
with two hops found as a success for the leg. It is not: the answer will be wrong. `< 1.0` is
the right threshold and it is the same argument as full-chain recall in E1, which is why E1 is a
prerequisite for this unit.

## Where this lives in the real system

`raglab/retrieve.py:rrf` is this function with one addition — an optional `weights` list, so
`rrf(legs, weights=[1.0, 0.4])` can down-weight a leg without leaving the rank-based family.
Worth knowing it exists; not worth reaching for until the failure-overlap measurement says the
legs are complementary enough that weighting them is a question at all.

The full comparison across every rule is `python scripts/run_eval.py --compare`, and the note it
produces is [`docs/09-research/measurements/fusion-rules.md`](../../../docs/09-research/measurements/fusion-rules.md).

## What this unlocks

**P1** turns this run into the artefact you would hand a stakeholder: a measurement note carrying
the command that regenerates it. The reason that matters is
[ADR-0015](../../../docs/01-architecture/adr/0015-correct-the-fusion-finding.md) — a wrong fusion
finding stood in this repository for months, and what let it stand was that re-running the
comparison took reading three files and writing a script.
