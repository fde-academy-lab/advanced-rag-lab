# ADR-0012 · Order prompt blocks by volatility

- **Status:** Accepted
- **Date:** 2026-08-29
- **Deciders:** Maintainers
- **Related:** Debugging Clinic thread (prompt cache), notebook `07`

## Context

Prompt caching reuses a previously-processed prefix and charges a fraction of the input rate for
it. The requirement is that the prefix is **byte-identical** — not semantically equivalent, not
structurally the same, identical.

A cache hit rate of 4% was traced to a timestamp at byte 58 of the system prompt. Five characters
differed between consecutive requests, and every token after them was uncacheable, which was the
entire prompt. The timestamp had been added three weeks earlier for a good reason ("as of"
questions), the feature worked correctly, and the only symptom was a bill roughly triple the
model.

## Decision

**Context blocks are assembled in order of volatility, most stable first.**

```
1. system prompt            never changes
2. instructions / rubric    changes on deploy
3. few-shot examples        changes on deploy
4. retrieved chunks         changes every query   ← hard cache barrier
5. current time, user state changes every request
6. the question             changes every request
```

Everything before block 4 is cacheable. Nothing after it is. Therefore anything volatile that
could have been placed early must be placed after the barrier, and the ordering of blocks 1–3 is
a cost decision rather than a formatting preference.

Measured effect of moving the timestamp from block 1 to block 5: cache hit rate 4% → **71%**,
cost per query down 58%.

## Consequences

**Good.** The rule is mechanical and reviewable. "Does this new field change per request, and is
it before the barrier?" is a question a reviewer can answer from the diff.

**Bad.** It constrains prompt design for a reason unrelated to prompt quality. A rubric that
would read better interleaved with examples has to stay contiguous and early. That is a genuine
cost and it is worth paying at scale and not worth paying at ten queries a day.

**It conflicts with position-optimal ordering.** The lost-in-the-middle effect argues for placing
the best chunk first and second-best last. That ordering depends on this query's ranking, so it
changes the prefix every query and caches nothing. On our corpus the position effect at an
8-chunk window is 0.04 with an interval spanning zero — inside the noise band — so the cache
wins. **That is a corpus-specific and window-specific conclusion**, and at 20+ chunks the
position effect grows while the argument reverses.

## Enforcement

A test asserts that the first N tokens of the assembled prompt are identical across two different
queries. It would have caught the timestamp on the day it was introduced.

Cache hit rate belongs on the dashboard next to latency and cost. This failure is completely
silent — right answers, working feature, larger bill — and the only way to see it is to look at
it directly. Alert on a drop of more than 10 points week over week.
