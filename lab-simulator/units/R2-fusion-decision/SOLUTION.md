# R2 · How we did it

There is no single right answer here, and the grader does not look for one. It looks for whether
your reasoning is about the **mechanism** or about the table. Below is the decision we shipped on
Client Zero, then the two answers that are also defensible, then the one that isn't — and then the
history, which is the part that matters most and which we got wrong in public.

## What we wrote

```yaml
decision: >-
  Ship the dense leg alone at k=8. No fusion, no second index, no alpha. Keep the BM25 index
  built and unwired behind a flag so the identifier slice can be re-tested cheaply.

why: >-
  The fused configurations lose because they do not win. Equal-weight RRF scores 0.7742 against
  the dense leg's 0.7733 — +0.0008 with an interval of (−0.0101, +0.0109) — and on nDCG the
  unfused leg beats it outright by 0.075. Fusion only pays when the legs fail on different
  queries, and here they do not.

rejected: >-
  Weighted fusion at α=0.5, which would have been right if the per-query overlap of the two
  legs' failures were low, or once the identifier slice grows enough that BM25's real win stops
  being invisible in the aggregate.

would_change_if: >-
  I plot the per-query failure overlap between the legs and find BM25 succeeding on a meaningful
  share of the questions the dense leg misses, rather than a subset of them.
```

## The sentence the unit is about

> Fusion turns two signals into a better one only when the legs fail on **different** queries.

Not "when the legs are comparably strong" — that is the folk version and it is the one we
ourselves published and had to retract. Two retrievers of identical strength that fail on the
same queries carry one signal between them, and combining a signal with itself returns the
signal. Two retrievers of *very different* strength that fail on disjoint queries fuse
beautifully.

Cormack's RRF paper fuses **TREC runs**: mature systems of broadly comparable quality, which is
to say systems that are good in *different ways*. That second property is doing more work in the
paper than the equal weighting is, and it is the one nobody quotes.

The diagnostic that follows is concrete, and it is the thing to take away:

```python
# Which questions does each leg miss, and do the misses overlap?
dense_miss = {q for q, r in dense_rows.items() if r["evidence_recall"] < 1.0}
bm25_miss  = {q for q, r in bm25_rows.items()  if r["evidence_recall"] < 1.0}

len(dense_miss & bm25_miss) / len(dense_miss)   # ≈ 1.0 → fusion buys nothing
                                                # ≈ 0.5 → fusion buys a lot
```

One line of set arithmetic, and it answers the question the aggregate table cannot. Nobody ran
it before choosing — on either side of the correction below.

## Two other defensible answers

**Ship equal-weight RRF.** Argued well, this is stronger than ours. The dense leg is LSA, which
is a stand-in; the moment it is replaced with a real sentence encoder the legs' failure profiles
change and you would rather already have the fusion path built than be adding one under
deadline. RRF costs nothing to keep — no α, no normalisation, nothing to re-tune — so the price
of the option is the second index alone. What makes this answer good is that it prices the
option explicitly instead of appealing to "hybrid is best practice".

**Ship weighted at α=0.5.** Highest evidence recall in the table (0.7790), and `w0.2 → w0.5` is
+0.0145 with an interval excluding zero, so that part is real. This is only a good answer if it
says out loud that it does **not** clear the dense leg alone, and gives a reason to pay for a
tuned constant anyway — for instance that you expect the corpus to acquire identifier traffic and
want the lexical leg already weighted in when it does. Picking it because it tops the table is
the decoy, not the answer.

Notice that all three share the same `why`. They differ on what to do about it. That is what a
decision looks like when the reasoning is real.

## The answer that isn't

> "Weighted fusion at α=0.5 reaches 0.7790, ahead of RRF at 0.7742, dense at 0.7733 and BM25 at
> 0.7118. The highest measured configuration is the one that should ship."

Correct arithmetic. Nothing learned. It cannot be applied to a corpus you have not measured yet,
which is every corpus after this one — and measuring first is not always available, because the
measurement is often what you are trying to justify the budget for.

It also misreads the table. `0.7790` against `0.7733` is +0.0057 on a set of 207 questions; the
interval on the comparison it *does* clear (`w0.2 → w0.5`) is (+0.0048, +0.0254), and the one
against the dense leg is not clear at all.

This is `reference/fail-summarises-the-table/`, and the checks that reject it are the three
`engages with:` lines.

## Falsifiers, and why the gate is strict

The three most common first attempts, all rejected:

| What people write | Why it is not a falsifier |
|---|---|
| "If it turns out to be the wrong choice" | True of every decision ever made. Names the conclusion |
| "If fusion stops beating the single leg" | Restates the decision with a negation on it |
| "If the numbers change" | Which numbers, by how much, measured how? |

A falsifier is a **standing instruction to your future self**, and it has to be specific enough
that someone who was not in the room can execute it. Ours is: *plot the per-query failure overlap
between the legs; if BM25 is succeeding on questions dense misses rather than a subset of them,
revisit.* Somebody can run that without asking what you meant.

## Where this went wrong for us, in public

Everything above replaced the opposite claim.

Until 2026-09-01 this unit — and the README, two ADRs, four interview-prep banks, a case study,
the facilitator script for session 02, the published site and the seeded discussion threads —
said:

> Equal-weight RRF loses to BM25 alone here, because fusing a strong retriever with a weak one at
> equal weight moves you toward the weak one.

Re-measured, none of it holds:

| Claimed | Measured |
|---|---|
| RRF loses to BM25 alone | RRF **wins** by +0.0624, ci (+0.0407, +0.0857), at every k from 5 to 20, with and without the reranker |
| The dense (LSA) leg is the weak one | It is the **strong** one: +0.0616 evidence recall and +0.2416 nDCG over BM25 |
| Weighted α=0.2 wins | It ties RRF on recall, loses on nDCG, and is not even the best α |

It stood for months and was quoted in about twenty places. Some of it was quoted in interviews by
people who learned it here.

**The interesting part is why nothing caught it.** The eval gate compares one configuration
against its own history and blocks a merge on a regression. It was working perfectly. It has no
concept of comparing configurations *against each other*, so a claim about which configuration
wins sat entirely outside what CI was capable of checking — and the more the gate was trusted,
the less anyone re-ran the comparison by hand.

The likely origin is mundane: `0.7645` is the tuned configuration's evidence recall, it appears
in at least one document attributed to "BM25 alone" (whose real number is `0.7118`), and once
that attribution was in circulation the mechanism story was built around it and never re-run.

Two things went in as a result. `python scripts/run_eval.py --compare` produces the whole table
with intervals in one command — because *a claim you cannot re-run in one command is a claim
nobody will re-run*. And [ADR-0015](../../../docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
records what was claimed, what was measured, and this paragraph.

If you take one habit from this unit, take that one: when you publish a comparison, ask what
would have to break for you to find out you were wrong. If the answer is "somebody re-runs it by
hand", you have not published a finding. You have published a belief.

## Where this lives in the real system

`raglab/retrieve.py` implements every rule; `scripts/run_eval.py --compare` measures them; the
full table with all four metrics and every interval is
[`docs/09-research/measurements/fusion-rules.md`](../../../docs/09-research/measurements/fusion-rules.md).

`raglab.TUNED` still ships α=0.2 even though α=0.5 measures better, and the honest reason is
administrative: `.github/eval-baseline.json` is cut from it, every headline number in the
repository is that configuration, and moving the default in the same commit as a correction
would make both harder to review. ADR-0015 says that rather than inventing a justification.

## What comes next

**R3** implements whichever configuration you chose and puts it against a bar on the real corpus.
If your decision was wrong, R3 is where you find out — which is the correct order for that to
happen.
