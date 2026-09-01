# Template · Product requirements for an AI feature

A PRD for a deterministic feature can specify behaviour. A PRD for a retrieval or generation
feature cannot — the behaviour is a distribution — so it has to specify **measurements** instead.

That is the whole difference, and it is why generic PRD templates produce unbuildable documents
here.

---

```markdown
# <Feature> — Product requirements

**Status** draft | in review | approved     **Owner**     **Date**

## Problem
What is broken today, for whom, and how you know. One paragraph. If you cannot name who is
harmed, you do not have a problem yet.

## Users
Primary, secondary. For each: when they use it, and what they do instead today.
The "instead today" is the baseline you will be compared against, whether or not you measure it.

## In scope
## Out of scope for v1
Each with the reason it was deferred, not just the fact. A deferral without a reason gets
re-litigated every fortnight.

## Acceptance criteria
| # | Criterion | How it is measured | Threshold |
Every row measurable by someone who did not write it.

## Explicit non-goals
The things it will not do, that a reader would otherwise assume it does.

## Failure behaviour
What it does when it cannot answer. This is a requirement, not an implementation detail.

## Cost envelope
Per query, and at expected volume. A feature without one is not costed.

## Open questions
With an owner and a date each.
```

---

## The four sections a generic template omits

### Acceptance criteria that are measurable

The test: **could someone who did not write the PRD run it?**

| Not measurable | Measurable |
|---|---|
| "Answers are accurate" | "Version-correctness ≥ 0.90 on a 60-query slice built from real revisions" |
| "Fast enough" | "p95 end-to-end under 3s at 5× expected peak" |
| "Cites sources" | "100% of responses carry a source and revision date, checked automatically" |
| "Handles unknowns gracefully" | "Abstention precision ≥ 0.80 on 30 deliberately unanswerable queries" |

Each right-hand row names a number, a population and a method. Each left-hand row is an
aspiration that will be declared met by whoever is most tired.

### Failure behaviour, as a requirement

An AI feature will be asked questions it cannot answer. What it does then is a **product
decision**, and leaving it to the implementation means the answer is "guess confidently".

Specify: when it declines, what it says, whether it offers a next step, and — the part that is
always missed — **whether declining counts as a failure in your metrics.** If your accuracy metric
scores an abstention as wrong, you have built a mechanism the metric punishes.

### A cost envelope

Per query, and at volume. Two numbers, and they change the design:

- If generation is 70–85% of cost, "make it cheaper" means output tokens or model size — not the
  vector store.
- If the envelope is tight, prompt-cache-friendly context ordering stops being an optimisation and
  becomes an architectural constraint.

Retrofitting either is painful. Both are free on day one.

### Out of scope, **with reasons**

"Chat interface — out of scope" gets asked again next month. "Chat interface — out of scope for
v1 because the on-call use case is single-shot lookup under time pressure, and a conversational
interface adds turns to the slowest possible moment" does not.

## The section to delete

**Success metrics that are not acceptance criteria.** If a number matters, it belongs in the
acceptance table with a threshold and a method. A separate list of aspirational metrics is where
unowned numbers go to be quoted later without their context.

## Worked example

[SC-01 Stage 2](../scenarios/SC-01-incident-search.md) has an abridged PRD with five acceptance
criteria, an explicit non-goal, and three deferrals each carrying its reason.
