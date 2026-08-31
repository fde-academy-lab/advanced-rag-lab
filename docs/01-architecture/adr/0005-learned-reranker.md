# ADR-0005: Make the reranker a fitted model rather than hand-tuned weights

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

The deck teaches that a cross-encoder is the default stage-2 choice and the highest quality per
unit of engineering effort. A teaching toolkit has to demonstrate that, offline, without a
trained transformer.

The first attempt was a hand-weighted feature scorer. **It made retrieval worse** — measurably,
consistently, at every value of k. That is a defect, not a nuance: shipping it would have
taught the opposite of the lesson.

## Options considered

### Option A — keep hand-tuned weights and explain the negative result
Honest, but it teaches "rerankers do not help", which is false in general and false for the
reason the deck gives.

### Option B — grid-search the hand-tuned weights
Tried. The best grid point still lost to the fusion it was reranking, because the scorer was
lexical-only and discarded the dense signal entirely.

### Option C — make it a *learned* model
Eight pair features, logistic regression, fitted on the dev slice with class weighting.

## Decision

Option C, with `DEFAULT_CROSS_WEIGHTS` fitted once and committed, and `fit()` exposed so
notebook 04 re-derives them in front of the student.

## Consequences

**Good.** It works: +8 points of evidence recall over the fusion it reranks, and the gain holds
on the frozen slice. Architecturally it is the same animal as a real cross-encoder — it scores
the pair, nothing is precomputable, cost is linear in N. And it made the toolkit *more* honest
about something the deck only implies: **a reranker is a model.** It has training data, it can
overfit, and its gain has to survive on a slice it never saw. That is now a lesson (notebook 04
§4.10) rather than an assumption.

**Bad.** The committed weights are fitted to this corpus and this encoder. They are not a
universal constant and the docstring says so twice. There is a mild circularity to be aware of:
the reranker is fitted on dev questions and the headline numbers are reported over the full set
including dev — notebook 04 reports the frozen slice separately for exactly this reason, and a
student who does not read that far could over-read the headline.

**Revisit when:** someone swaps in a real cross-encoder (EX-14). The weights become irrelevant
and the lesson about fit-then-verify becomes more important, not less.
