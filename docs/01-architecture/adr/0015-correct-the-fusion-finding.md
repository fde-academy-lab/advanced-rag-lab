# ADR-0015: Correct the fusion finding, and say publicly that we got it wrong

- **Status:** Accepted
- **Date:** 2026-09-01
- **Deciders:** Maintainers
- **Amends:** ADR-0003, ADR-0007

## Context

ADR-0007 published three findings that contradict the source deck. The first was:

> Equal-weight RRF does not beat BM25 alone on this corpus; weighted fusion at α=0.2 does.

ADR-0003 built a mechanism on top of it: LSA is weaker than BM25 here, so fusing a strong leg
with a weak one at equal weight moves you toward the weak one. The claim propagated into the
README, the CHANGELOG, `start-here`, the retrieval LLD, the RRF paper note, four interview-prep
banks, the session-02 facilitator script, the exercise rubrics, a case study, the Pages site,
the seeded discussion threads and notebook 04.

Re-measured with the current harness — `python scripts/run_eval.py --compare`, 243 questions,
paired bootstrap — **it does not reproduce, and neither does the mechanism it rests on.**

| | Claimed | Measured |
|---|---|---|
| Equal-weight RRF vs BM25 alone | RRF loses | RRF **wins** by +0.0624 evidence recall, ci (+0.0407, +0.0857), at every k from 5 to 20, with and without the reranker |
| The dense (LSA) leg | weaker than BM25 | **stronger** than BM25: +0.0616 evidence recall, +0.2416 nDCG |
| Weighted α=0.2 | wins | ties RRF on evidence recall (noise band), **loses** to it on nDCG (−0.0535), and is not even the best α — 0.5 is |

The full table and every interval is in
[`docs/09-research/measurements/fusion-rules.md`](../../09-research/measurements/fusion-rules.md).

We do not know exactly when it diverged. The most likely origin is a label slip: `0.7645` is the
tuned configuration's evidence recall and appears in at least one document attributed to "BM25
alone", whose real number is `0.7118`. Once that attribution was in circulation the mechanism
story was constructed around it and never re-run — which is the failure mode the eval gate exists
to prevent and did not, because the gate compares one configuration against its own past self and
never compares configurations against each other.

## Options considered

### Option A — quietly correct the numbers
Edit the affected files, update the table, move on. Cheapest, and it leaves no trace of the
error. Every student who quoted the old finding in an interview learns nothing about how it was
caught.

### Option B — retract the finding and replace it with what is actually true, in the open
Correct every occurrence, keep a record of what was claimed and what was measured, and add the
`--compare` command so the claim is re-runnable in one line by anyone who doubts it.

**Cost:** the repository's most-quoted result changes, and material that students have already
learned and used is now wrong. The Pages site, the seeded discussions and notebook 04 all carry
it. That is a real cost and it is paid in public.

## Decision

Option B. ADR-0007's own revisit clause is *"individual findings should be revisited whenever the
corpus, the encoder or the eval set changes — and re-measured rather than assumed to still
hold"*. Applying that policy to itself is the only version of it that means anything.

The three corrected findings replacing the fusion claim:

1. **BM25 is the weak leg on this corpus, not the dense one.** The questions are paraphrase and
   inference over prose; term overlap has little to score. BM25's win is confined to the exact
   identifier slice, which is real and small.
2. **Fusion does not separate from its better single leg.** `dense → rrf` is +0.0008 evidence
   recall with an interval straddling zero, and the unfused dense leg wins nDCG outright. The
   second index, second pipeline, fusion rule and per-corpus α buy nothing measurable.
3. **No retrieval configuration moves answer correctness.** Evidence recall spans 0.7118 → 0.7790
   — real, 9.4% relative — while `answer_correct` stays inside the noise band across every arm,
   and the numerically best answers come from the numerically worst retriever. The system is
   generation-limited.

Finding 3 is stronger teaching material than the claim it replaces, and it was sitting in the
0.4686 → 0.4115 gap the whole time.

## Consequences

**Good.** The findings are now reproducible in one command (`--compare`), which is what the
originals should have been. The gap that made this possible — an eval gate that compares a
configuration against its own history and never against alternatives — is named, and `--compare`
closes it. Finding 3 redirects the roadmap: retrieval work on this corpus is close to exhausted
as a lever on the metric a user feels.

**Bad.** `raglab.TUNED` keeps α=0.2 even though α=0.5 measures better on evidence recall and
nDCG, and `.github/eval-baseline.json` is cut from it. Changing the default would move every
headline number in the repository in the same commit as a correction, and conflating those two
edits would make both harder to review. The honest statement is: **α=0.2 is retained because the
baseline is cut from it and the alternatives are inside the noise band on the metrics that
matter, not because it is optimal.** Moving the default is its own change, with its own
re-baseline. Tracked as EX-16.

Material already in circulation carries the old claim: the seeded discussion threads, the
published Pages site and any notebook a student has already run. Those are corrected by this
change but copies are not recallable, and some students learned a wrong result from us.

**Revisit when:** the corpus, the encoder or the question mix changes. Run `--compare`, not the
last ADR.
