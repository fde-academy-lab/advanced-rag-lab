# Template · ADR-lite

A full Nygard ADR is right for a decision that shapes the system for years. Most decisions are
smaller than that and get made in a thread, which means they get made twice.

An ADR-lite is six lines. It fits in a PR description or a discussion reply, and it captures the
only things that matter six months later: **what you chose, what you rejected, and what would
make you change your mind.**

---

```markdown
### ADR-L<n> · <the decision, as a statement not a question>

**Context.** One or two sentences. The constraint that forces a choice.
**Options.** (a) … (b) … (c) …
**Decision.** The one you took.
**Why.** The reason the others lose. Not the reason this one wins — those are different.
**Consequence.** What you now have to live with. Include the bad one.
**Would change if.** The observation that would make this wrong.
```

---

## The two lines people skip, and why they are the point

**"Why" must name why the alternatives lose.** "We chose a filter because filters are reliable"
is not a reason; it does not engage with the boost. "A boost makes suppression *probable*, and
during an outage a superseded step followed once is worse than a missing result" is a reason,
because it says what the alternative fails to provide.

**"Would change if" is what makes it a belief rather than a preference.** A decision with no
falsifier cannot be revisited on evidence — only re-argued. It is also the line that most often
turns out to have predicted the incident.

## Worked example

> ### ADR-L1 · Supersession is a filter, not a ranking signal
>
> **Context.** Superseded runbook revisions must not be returned as current during an incident.
> **Options.** (a) Boost current revisions in ranking. (b) Filter superseded ones out by default.
> **Decision.** Filter.
> **Why.** A boost makes suppression probable rather than certain. During an outage a superseded
> step followed once is a worse outcome than a missing result.
> **Consequence.** Users wanting history need an explicit affordance, so "show superseded" is a
> v1 feature rather than v2.
> **Would change if.** Supersession metadata proved unreliable — a filter on bad data hides
> correct answers, which is worse than a boost on bad data.

That last line named the failure that happened in week 11. See
[SC-01 Stage 6](../scenarios/SC-01-incident-search.md).

## The rule that follows from that

**A "would change if" clause needs an owner and a check, or it is a note rather than a control.**
When you write one, either attach the test that would detect it, or write down that you are
accepting the risk unmonitored. Both are legitimate. Silence is not.

## When to promote to a full ADR

| Promote when | Stay lite when |
|---|---|
| The decision constrains something else for years | It is reversible in under a week |
| Reversing it means a data migration | Reversing it means a config change |
| Someone will ask "why is it like this" without context to answer from | The code makes it obvious |
| It was contested and the dissent is worth preserving | Nobody disagreed |

The last row matters more than it looks. **A recorded dissent is worth more than a recorded
decision**, because the decision is visible in the code and the dissent is not.

## Where these live

- In the PR that makes the change, so the decision and the diff are together.
- Collected into [`docs/01-architecture/adr/`](../../docs/01-architecture/adr/) once a decision
  turns out to be load-bearing.
- Referenced from the thread where it was argued, so the reasoning survives the summary.
