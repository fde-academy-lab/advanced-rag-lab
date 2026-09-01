# Template · Solution dissection

A postmortem asks what went wrong. A dissection asks a harder question about a system that is
*working*: **which parts are actually carrying it, and which are there because somebody read a
blog post?**

Run one after a build ships and before the next one starts. It is the cheapest way to stop a
system accumulating components nobody can justify.

---

```markdown
# Dissection · <system>, <date>

## What it does, in one sentence

## The component table
| Component | What it fixes | What it costs | Measured against removing it? | Verdict |

## Decisions that were right, and why
## Decisions that were wrong, and why
## Decisions we cannot evaluate, and what would settle them

## The root cause behind the wrong ones
Usually one thing, not several.

## What we would do differently with the same information
Not with hindsight. With what was actually known at the time.
```

---

## The column that does the work

**"Measured against removing it?"**

Most components are measured against their own previous version, which answers "is it getting
better" and not "is it earning its place". Those are different questions and the second one is the
one that finds dead weight.

This is not hypothetical. A reranker in this repository improved steadily against earlier versions
of itself while being **worse than not having a reranker at all** — evidence recall 0.773 without,
0.630 with, at k=5. Every comparison run was against another reranker, so the comparison that
mattered was never run.

## Three verdicts, not two

| Verdict | Means | What to do |
|---|---|---|
| **Right** | Measured, earns its cost | Nothing. Write down why, so it is not re-litigated |
| **Wrong** | Measured, does not earn its cost, or caused a failure | Remove it, or fix the root cause |
| **Cannot evaluate** | Never measured against its absence | Name the experiment that would settle it |

The third is the honest one and the one people skip. A dissection where every component is "right"
is a dissection that did not look. In SC-01, structural chunking sits in this bucket — it probably
made no difference, and nobody measured, which is a small failure worth recording as one.

## Separating the decision from the outcome

A decision can be right and still produce a bad outcome, and the reverse. Judge the decision on
what was knowable **at the time**.

In SC-01 the filter-not-boost decision was correct and the system still broke — the failure was in
the data mapping, not the strategy. Recording that as a wrong decision would have taught the team
to prefer boosts, which is the opposite of the lesson.

Conversely, the ten-engineer pilot was a wrong decision *with information available at the time*:
the team knew the corpus had three source systems and did not stratify.

## Look for the single root cause

Wrong decisions usually share one. In SC-01 both the unstratified pilot and the aggregate-only
alerting came from the same assumption — that the population was uniform, when the corpus had
three sub-corpora with different schemas.

**Fixing the root cause fixes both. Fixing them separately fixes neither**, because the assumption
survives and produces a third instance next quarter.

## Worked example

[SC-01 Stage 7](../scenarios/SC-01-incident-search.md) dissects six decisions and lands on the one
assumption behind both failures.
