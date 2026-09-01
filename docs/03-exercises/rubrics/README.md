# Rubrics

One grading scale, applied to every exercise. It is deliberately short: a rubric with fourteen
criteria is a rubric nobody applies consistently.

| Band | Criteria |
|---|---|
| **Exemplary** | Correct, measured with intervals, cost named — **and** it surfaced something the brief did not anticipate |
| **Full credit** | Correct and properly measured. **Or:** a clean negative result with a mechanism and the condition under which the expected result would return |
| **Partial** | Right direction, measurement incomplete — no interval, no named slice, or two changes at once |
| **Not yet** | A claim without a number, or a number without provenance |

## What moves a submission between bands

**Partial → Full credit** is almost always one of three things:

1. **An interval.** `metrics.paired_bootstrap` takes one line and converts an observation into a
   result.
2. **A named slice.** "Overall" is a slice and must be said out loud. A number without a slice
   invites the reader to assume it is uniform, and it never is.
3. **One change.** A submission that alters chunking *and* reranking cannot attribute either.
   Split it.

**Full credit → Exemplary** cannot be achieved by following the brief. It requires noticing
something the brief did not ask about — a slice that behaves differently, a methodology problem
in the exercise itself, a result that is true for a reason other than the one proposed.

Several exercises exist *because* a previous submission did this.

## Why a negative result is full credit

Not a consolation prize. Three of the most valuable findings in this repository are negative,
and each changed what got built next:

| Finding | What it changed |
|---|---|
| Equal-weight RRF loses to BM25 alone | Weighted fusion became the default; α is now a tuned parameter rather than an assumption |
| Comparison starvation does not reproduce | Produced issue #14 — an adversarial eval slice with deliberate prevalence imbalance |
| No score threshold separates answerable from unanswerable | Produced issue #10, and stopped a week of threshold tuning that could not have worked |

A negative result *without* a mechanism is **Partial**, not full credit. "It didn't work" is not
a finding; "it didn't work because the feature has the wrong sign, and here is the distribution
that shows it" is.

## Peer review

You owe one review before you ask for one. Review in this order, and stop at the first failure —
there is no point discussing the conclusion of a submission that changed two things:

1. Is the measurement present, with intervals, and honest about deltas inside the noise band?
2. Is it **one** change?
3. Is the cost named — latency, tokens, storage, or one more system to maintain?
4. Was the frozen slice respected?
5. Only then: is the conclusion supported by the numbers?

Review the work, not the person. Most people posting here are learning in public, which takes
more courage than posting something finished.
