# ADR-0007: Report findings that contradict the deck rather than tuning them away

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

Three measurements in the notebooks contradict what the source deck's matrices predict:

1. Equal-weight RRF does not beat BM25 alone on this corpus; weighted fusion at α=0.2 does.
2. Comparison-question starvation does not reproduce.
3. No retrieval-score threshold separates answerable from unanswerable questions (best F1 0.38).

Each could have been made to disappear. (1) by picking a corpus where the dense leg is
stronger; (2) by unbalancing the corpus until starvation appears; (3) by using a stratified
subsample where the base rate flatters precision — which we briefly did, and it produced a
curve that undercut the notebook's own conclusion.

## Options considered

### Option A — engineer the corpus until every matrix row confirms
Every lesson lands cleanly. Students see the expected result every time.
**Costs:** it teaches that decision matrices are facts to recite. It also teaches, implicitly,
that when your measurement disagrees with the slide you should change the measurement.

### Option B — report the findings, explain the mechanism, name the condition under which the expected result returns

## Decision

Option B, prominently — the README has a dedicated "Three results that contradict the expected
answer" table, and each notebook explains the mechanism where it occurs.

## Consequences

**Good.** It teaches the thing the curriculum is actually about: **a decision matrix names a
mechanism you should go and test, and the test is allowed to come back negative.** The three
findings are the most-discussed content in the repository and the ones students quote in
interviews, because "two of my four changes were inside the noise band" is a sentence almost no
candidate says. It also forced genuine explanations — the abstention finding produced the
insight that null questions are *lexically closer* to the corpus than paraphrased real ones,
which is worth more than a working threshold would have been.

**Bad.** A student who skims will see "hybrid retrieval did not help" and take the wrong lesson
out of context. We mitigate with the "when the expected result returns" column in every case,
but skimming is real and this is a genuine cost. It also makes the material harder to deliver:
a facilitator has to be comfortable saying "the slide predicts X and our measurement says not
here, and here is why", which is a harder room to hold than a clean confirmation.

**Revisit when:** never, as a policy. Individual findings should be revisited whenever the
corpus, the encoder or the eval set changes — and re-measured rather than assumed to still hold.
