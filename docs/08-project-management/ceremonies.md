# Ceremonies

Four, each producing an artefact. A ceremony that produces only a shared feeling is a meeting,
and this document is about the ones that leave something behind.

| Ceremony | Cadence | Duration | Artefact |
|---|---|---|---|
| Standup | Weekly, async | — | A thread in **Weekly Standup & Retro** |
| Design review | On demand | 45 min | A thread in **Design Reviews**, sometimes an ADR |
| Eval review | Weekly | 30 min | The scorecard delta, and a decision about it |
| Retro | Per phase | 60 min | A dated note in `docs/08-project-management/retros/` |

## Standup — written, not spoken

Posted as a thread, one per week, three lines per person:

```markdown
**Moved.** EX-14 submitted; reranker semantic features merged (+8 pts evidence recall,
[+0.03, +0.12], holds on frozen).

**Blocked.** Waiting on a decision about whether the frozen slice can be regenerated
when the corpus grows. Needs an ADR — I'll draft it if nobody objects.

**Wrong about.** I said last week the ANN recall drop was a cache bug. It was a cache
bug *and* a graph bug, and the cache bug was hiding the graph bug.
```

The third line is the one that matters and it is the one people drop. A standup where nobody was
ever wrong is a status report, and status reports do not surface the thing that is about to cost
somebody a week.

## Design review — before the build, not after

Post the design **before** implementing. The point is to get the objection now rather than in
week three.

A reviewable post contains: the constraint, the design, **what your own design costs**, and the
alternative you rejected with the reason. A design without a named cost has not been thought
through, and reviewers should say so rather than reviewing it.

Outcomes: proceed · proceed with a named change · needs an ADR · do not build this yet, measure
X first. That last one is the most valuable and the least used.

## Eval review — thirty minutes, one question

Look at the scorecard delta since last week and answer: **did anything move, and do we know
why?**

Three cases:

| Case | Response |
|---|---|
| Nothing moved | Fine. Say so and stop. Thirty minutes returned |
| Something moved and we know why | Record it against the change |
| Something moved and we do **not** know why | This is the whole reason the meeting exists. Bisect before doing anything else |

An unexplained *improvement* gets the same treatment as an unexplained regression. It usually
means the eval set changed, or a metric is now computed over a different denominator.

## Retro — per phase, not per sprint

Four questions, in this order:

1. **What did we learn that changed a later phase?** If nothing, the phases were not real.
2. **What did we measure that came out against us?** Name it. These are the most valuable
   outputs and they evaporate if not written down.
3. **What did we skip?** Every phase skips something. Say what, so the next phase knows.
4. **What rule should change?** Rules here are load-bearing; if one is being routinely violated
   it is either wrong or unenforced, and both need fixing.

Written up as a dated note, committed. The commit matters: a retro whose output lives in
someone's notebook did not happen.

## What is deliberately absent

- **Daily synchronous standup.** The written weekly one carries more information and costs
  ninety minutes a week less.
- **Estimation in points.** Effort is a coarse field on the board (S / M / L / XL) because that
  is as precise as anyone can honestly be, and a false precision invites planning against it.
- **Sprint commitment.** Phases end on criteria, not on dates. Committing to a date for work
  whose outcome is a measurement is committing to a result you have not measured yet.
