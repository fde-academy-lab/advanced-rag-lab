# R2 · How we did it

There is no single right answer here, and the grader does not look for one. It looks for whether
your reasoning is about the **mechanism** or about the table. Below is the decision we shipped on
Client Zero, then the two answers that are also defensible, then the one that isn't.

## What we wrote

```yaml
decision: >-
  Ship weighted score fusion with alpha near 0.2 on the dense leg, min-max normalised per
  query, and keep BM25 alone as the fallback if normalisation ever has to be dropped.

why: >-
  Equal-weight RRF loses here because it is a voting rule and a voting rule assumes its voters
  are comparably credible. Scale-invariance is what lets RRF skip normalisation, and it is the
  same mechanism that throws away the only signal saying the LSA leg is the weaker voter.

rejected: >-
  RRF, which would have been the right call if the two legs were close in strength, or if
  scores were unstable enough per query that any normalisation I picked would be noise.

would_change_if: >-
  The per-query win rate between the legs moves toward even — each leg best on 40 to 60 percent
  of queries instead of the current lopsided split — or the tuned alpha lands near 0.5 with an
  interval that crosses it.
```

Measured: `0.7891` evidence recall@8 against the `0.7645` BM25 baseline, paired bootstrap
`[+0.008, +0.041]`. Real, and small.

## The sentence the unit is about

> Scale-invariance is what lets RRF work without normalisation. It is also what discards the one
> signal that would have told you the legs are unequal.

The virtue and the failure are the same mechanism. That is why this is a **condition** and not a
rule — and why "RRF lost, so use weighted" is worth nothing on the next corpus. On a corpus where
the dense leg is a real sentence embedder rather than a truncated SVD, the condition flips and so
does the answer.

RRF is a **Borda-like voting rule**. Each retriever casts a ranked ballot; the fused score
`Σ 1/(k + rank)` counts votes with a decaying weight. Ask what a voting rule assumes about its
voters and the failure becomes obvious: it assumes they are comparably informed. Ours are not.
The LSA leg gets a full ballot on every query, including the many where it has nothing useful to
say, and its votes are enough to push the BM25 leg's genuinely-correct top hit from rank 1 to
rank 3 — which, at `k = 8`, is survivable, and at `k = 3` is not.

`k = 60` does not save you. It flattens the gap between *ranks* — at `k = 0`, rank 1 scores twice
rank 2; at `k = 60`, about 2% more. So `k` dampens how much any single system's top hit counts,
which is the opposite of what you need when one system's top hit is the reliable one. Turning `k`
down sharpens rank 1 for **both** legs, including the weak one.

## Two other defensible answers

**Ship RRF anyway, and fix the dense leg first.** Argued well, this is stronger than ours: α is a
hyperparameter fitted on 243 questions, the confidence interval is `[+0.008, +0.041]`, and the
lower bound is inside the range where a corpus refresh could erase it. Buying 2.5 points of recall
with a tuned constant that has to be re-tuned per corpus is a maintenance liability, and the
honest fix is a better second retriever rather than a better weighting of a bad one. What makes
this answer *good* is that it names the condition under which it changes: fix the dense leg, and
if the legs become comparable, RRF's scale-invariance stops costing anything and starts being
free robustness.

**Ship BM25 alone.** Also defensible, and the one most teams should hear more often. Neither
fusion rule clears BM25 by enough to justify a second index, a second embedding pipeline, and the
operational surface both bring — for a *2.5 point* gain at k=8. This answer is only good if it
says what would make the second leg worth it, and there is a specific answer available: the
lexical leg's failures are concentrated in the paraphrase slice, so a dense leg that measurably
wins *there* is worth adding even if the aggregate barely moves.

Notice that all three answers share the same `why`. They differ on what to do about it. That is
what a decision looks like when the reasoning is real.

## The answer that isn't

> "The evidence table shows equal-weight RRF scoring below BM25 at every value of k, while the
> weighted configuration scored 0.7891 against the 0.7645 baseline. The measured result is what
> should decide this."

Correct conclusion. Nothing learned. It cannot be applied to a corpus you have not measured yet,
which is every corpus you will meet after this one — and measuring first is not always available,
because the measurement is what you are trying to justify the budget for.

This is `reference/fail-summarises-the-table/`, and the check that rejects it is
`engages with: what rank-based fusion discards`.

## Falsifiers, and why the gate is strict

The three most common first attempts, all rejected:

| What people write | Why it is not a falsifier |
|---|---|
| "If it turns out to be the wrong choice" | True of every decision ever made. Names the conclusion |
| "If weighted fusion stops beating BM25" | Restates the decision with a negation on it |
| "If the numbers change" | Which numbers, by how much, measured how? |

A falsifier is a **standing instruction to your future self**, and it has to be specific enough
that someone who was not in the room can execute it. Ours is: *plot per-query win rate between
the legs; if it lands between 40 and 60 percent, revisit.* Somebody can run that without asking
what you meant.

This is the thing `decide` mode exists to train, and it is why the gate rejects the tautology
before it runs a single test. An engineer who writes the decision after the implementation has
learned to rationalise — the reasoning arrives already knowing the answer, so it cannot be wrong,
so it teaches nothing. The habit is invisible in the diff afterwards. Forcing the artefact first
is the only intervention that works.

## Where this lives in the real system

`raglab/retrieve.py` implements both rules and `scripts/run_eval.py` measures them. The
architecture note is [`docs/01-architecture/lld/retrieve.md`](../../../docs/01-architecture/lld/retrieve.md).

Two decision records are the grown-up version of what you just wrote:
[ADR-0003](../../../docs/01-architecture/adr/0003-lsa-default-encoder.md), which is where the
"fusing a strong retriever with a weak one under equal weight" argument is made in anger, and
[ADR-0007](../../../docs/01-architecture/adr/0007-report-negative-results.md), which is the
policy that let the RRF result be published as a finding instead of quietly dropped.

That second one is the part worth stealing. The equal-weight RRF result is a *negative* result:
the obvious thing did not work. It is also the most useful sentence in this whole track, and on
most teams it would never have left somebody's notebook.

## What comes next

**R3** implements what you just decided and puts it against a bar on the real corpus. If your
decision was wrong, R3 is where you find out — which is the correct order for that to happen.
