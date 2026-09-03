# Measurement · Are multi-hop failures correlated, or just multiplied?

- **Date** 2026-09-01
- **Command** `python scripts/independence.py` (add `--measure` for the micro rate)
- **Set** 207 answerable questions of 243; `p` taken from `.github/eval-baseline.json`
- **Supersedes** the "independence predicts 0.6838" claim in ADR-adjacent docs and in E1. See
  the retraction at the bottom.

---

## The question, and why it decides a roadmap

`full_chain_recall` scores 1.0 only when **every** gold evidence piece for a question was
retrieved. So under independence, a question needing `k` pieces resolves with probability `p^k`,
and the prediction is that weighted over the real distribution of `k`.

If measured full-chain recall sits **well below** that prediction, failures are correlated
inside a question: some questions are hard in a structural way, most are fine, and the work is
to find what the hard ones share. If it sits **at** the prediction, there is no structure to
find — the multi-hop gap is the arithmetic of needing several pieces, and looking for a hidden
cause is looking for something that is not there.

Those are different quarters of work.

## The distribution

```
207 answerable questions

  pieces of gold evidence   questions
       1                      21
       2                      59
       3                      21
       4                     100
       6                       6
```

Note what this is **not**: it is not the `hops` field, which reports 77 one-hop and 130 two-hop.
A two-hop question routinely carries four pieces of evidence, and `full_chain_recall` requires
all four. The exponent is `len(gold_map)`, not `hops`.

## The answer

| | value |
|---|---|
| `evidence_recall` (macro — the number the scorecard reports) | 0.7645 |
| `evidence_recall` (micro — pieces found / pieces total) | 0.7257 |
| `full_chain_recall`, measured | **0.4686** |
| independence prediction at the macro rate | **0.4603** (measured is **+0.0083**) |
| independence prediction at the micro rate | 0.4007 (measured is +0.0679) |

**Measured full-chain recall is at or slightly above independence.** Not below it. Under either
choice of `p` there is no shortfall to explain.

So: on this corpus, evidence pieces within a question are retrieved about as independently as
the model assumes. The 0.7645 → 0.4686 gap is fully accounted for by `0.7645^k` weighted over a
distribution where **half the questions need four or more pieces**. There is no hidden class of
structurally hard question, because there is no residual to attribute to one.

## What this does not say

It does not say correlated failure never happens — it is common, and on a corpus whose evidence
clusters by document you would expect it. It says it is not happening *here*, at this `k`, with
this retriever.

Two changes would move it. A retriever whose failures cluster by document, when a question's
pieces also cluster by document, correlates them — this corpus's fact graph spreads evidence
across documents by construction, which is likely why they do not. And a much smaller `k` would
push the per-piece rate down into a regime where the approximation of a single `p` for every
piece stops holding.

## The retraction

Until 2026-09-01 this repository said:

> The 207 answerable questions split 128 single-hop, 61 two-hop, 18 three-or-more. At
> `p = 0.7645`, that predicts **0.6838**. We measure **0.4686** — 21 points below independence,
> so the pieces are not independently retrievable and they fail together.

Wrong three times over.

**The mixture is not real.** The corpus reports `{1: 21, 2: 59, 3: 21, 4: 100, 6: 6}` gold
pieces per question. It does not report 128/61/18, and neither does the `hops` field (77/130).
No configuration of this repository produces those numbers.

**The exponent was the wrong quantity.** `p^h` over hops, where the metric requires all
*pieces*. Even with a correct hop mixture this predicts the wrong thing.

**The conclusion inverts.** Corrected, measured is `+0.0083` from the prediction rather than
`-0.2152`. The finding was not "smaller than we said" — it was pointing the other way.

It survived for the same structural reason the fusion finding did: **it was a number nobody
could re-derive in one command.** So there is now a command, `scripts/independence.py`, and
`tests/test_measurements.py` recomputes the distribution from the corpus and fails if the figures
quoted in the documentation drift from it.
