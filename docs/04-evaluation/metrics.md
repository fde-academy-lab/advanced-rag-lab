# Metrics

What each number measures, what it misses, and the specific way it lies. A metric you cannot
describe the failure mode of is a metric you will eventually be fooled by.

## The scorecard

Produced by `python scripts/run_eval.py` over 243 questions.

| Metric | Current | Gated | What it answers |
|---|---|---|---|
| `evidence_recall` | 0.7645 | ±0.02 | Of all gold evidence **pieces**, what fraction reached the window |
| `full_chain_recall` | 0.4686 | ±0.03 | Of all **questions**, what fraction had *every* required piece |
| `context_precision` | 0.2433 | — | Of the packed context, what fraction is gold evidence |
| `answer_correct` | 0.4115 | ±0.03 | Judged against gold, abstentions included |
| `abstention_recall` | 0.0000 | — | Of genuinely unanswerable questions, what fraction were declined |
| `cost_usd` | 0.0039 | — | Whole run |

## The two recalls, and why both are reported

This is the most important thing on the page.

**Evidence recall** is per piece. **Full-chain recall** is per question. If pieces were
retrieved independently with probability *p*, a question needing *k* pieces would fully resolve
with *p^k*, and the prediction is that weighted over the real distribution of *k*.

Two things about that *k*. It is the number of **gold evidence pieces**, not the number of hops
— a two-hop question routinely carries four pieces, and `full_chain_recall` requires all four.
And the distribution is not what anybody guesses:

```
python scripts/independence.py

  pieces of gold evidence   questions
       1                      21
       2                      59
       3                      21
       4                     100
       6                       6
```

**Half the answerable set needs four or more pieces.** At *p* = 0.7645 that predicts
**0.4603**. We measure **0.4686** — `+0.0083`, which is to say *at* independence.

So there is no shortfall, and that is the finding. Below independence would mean failures
cluster inside a question: some questions structurally hard, most fine, and the work is to find
what the hard ones share. At independence means there is nothing to find — the 0.7645 → 0.4686
gap is entirely the arithmetic of needing several pieces, and a hunt for a hidden cause would be
a hunt for something that is not there.

> **Corrected 2026-09-01.** This section previously reported a mixture of "128 single-hop, 61
> two-hop, 18 three-or-more", a prediction of 0.6838, and a 21-point shortfall attributed to
> correlated failure. The mixture matches nothing this repository produces, the exponent was
> hops rather than pieces, and the corrected comparison points the other way. See
> [the measurement note](../09-research/measurements/multi-hop-independence.md).

Measured directly across an N sweep from 20 to 200 candidates:

| | N = 20 | N = 200 |
|---|---|---|
| hop-1 recall | 0.88 | 0.94 |
| hop-2 recall | 0.54 | 0.55 |

The average was being carried entirely by the hop the retriever was already good at.

**Consequence for gating:** gate on full-chain, keep evidence recall as a diagnostic. Gating on
a metric that can improve while the product degrades is how a regression ships with a green
dashboard.

## How each metric lies

| Metric | The lie | The countermeasure |
|---|---|---|
| `evidence_recall` | Rises trivially with k, and rises by returning more of the evidence you already had | Always report k; report `context_precision` beside it, which falls |
| `full_chain_recall` | Brutal on questions needing many pieces — one miss is a zero | Report the distribution of pieces-per-question so the reader knows what they are looking at |
| `context_precision` | Punishes a system that retrieves useful non-gold context | Read as a budget-efficiency number, never as quality alone |
| `answer_correct` | Depends on a judge, which is a model that drifts | Version the judge and its prompt; re-run the frozen human slice on a schedule |
| `abstention_recall` | Currently 0.0000 — the system almost never abstains | This is a real finding, not a bug. See below |
| `nDCG` | Computed against the judgements you have, so surfacing correct-but-unjudged documents is punished (pooling bias) | Never compare nDCG across differently-annotated corpora |
| `MRR` | Only sees the first hit. Blind to everything after it | Use where there genuinely is one right answer. Floor is $H_N/N$ ≈ 0.0075 at N = 1000 |
| Any mean | Hides the slice that generates every complaint | Slice by query class, hop count and length. Report per-slice **n**, not just per-slice score |

## The abstention result

`abstention_recall` sits at zero, and that is the honest reporting of a real negative finding
rather than an unfixed bug.

We could not find a retrieval-score threshold separating answerable from unanswerable questions.
Best F1 **0.38** across four signals: top-1 score, score gap between ranks 1 and 2, mean of top-k,
and score entropy.

The mechanism is counter-intuitive and worth internalising. The null questions **name real
entities using the corpus's own vocabulary**; the genuine questions paraphrase. So the
unanswerable questions are lexically *closer* to the corpus than the answerable ones. Any
threshold on retrieval score is reading a feature with the wrong sign, and no amount of tuning
repairs a feature whose sign is wrong.

What would work — untested here, and tracked as issue #10 — is a signal about *sufficiency*
rather than *similarity*: asking whether the retrieved evidence entails an answer, rather than
whether it looks like the question.

## Reading the report

```
evidence_recall        0.7645 → 0.7645  (-0.0000)   ok
full_chain_recall      0.4686 → 0.4686  (+0.0000)   ok
```

Left is the committed baseline in `.github/eval-baseline.json`, right is this run. The gate
fails on a regression beyond tolerance and does **not** fail on an improvement — but an
unexplained improvement should be investigated with the same suspicion as a regression. See
[release-gate.md](release-gate.md).

Every metric is implemented in `raglab/metrics.py` with the failure it is guarding against in
the docstring. If a number looks wrong, read the docstring before reading the formula.
