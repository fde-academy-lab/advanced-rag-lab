# FDE scenarios

Full engagements inside Client Zero, walked from the sentence the client said to the postmortem.
Every artefact appears in the order it is actually produced.

| # | Scenario | Business unit | Covers |
|---|---|---|---|
| [SC-01](SC-01-incident-search.md) | The incident search that worked in the pilot | Logistics | Discovery, PRD, architecture, three ADR-lites, the full PDLC, a production failure, and the dissection |

## Why a scenario rather than a case study

A case study tells you what somebody else decided. A scenario puts you at the point where the
decision has not been made yet and the information is incomplete — which is the actual job.

Each one is written so you can stop at any stage and decide for yourself before reading on. The
stages are marked, and the useful way to work them is to close the file at the end of each stage
and write down what you would do next.

## What every scenario contains

| Stage | Artefact |
|---|---|
| 0 · The sentence | What the client actually said, and the three assumptions inside it |
| 1 · Discovery | Six questions and the answers that changed the design |
| 2 · Definition | A PRD with measurable acceptance criteria |
| 3 · Architecture | Index-time and query-time as separate timelines |
| 4 · Decisions | ADR-lites, including the ones that later turned out to matter |
| 5 · PDLC | What was planned against what actually happened |
| 6 · The failure | Something breaks. It always does |
| 7 · Dissection | Which decisions were right, which were wrong, and the single assumption behind the wrong ones |
| 8 · Takeaways | Transferable, not scenario-specific |

## The rule these follow

**The system fails in the middle.** A scenario where everything works is a demonstration, and it
teaches the reader that competent execution produces success — which is not true and is a bad
thing to internalise before your first engagement.

The failures here are real ones, in the sense that each is a defect that genuinely occurs: a
three-valued-logic filter silently dropping six years of data, a pilot cohort that was not
representative, a recorded risk with no owner attached.

## Client Zero is fictional

Meridian Group and its business units are generated from a fact graph. No real client, no real
data, no NDA. That is what makes it possible to write the failure down in this much detail — see
[client-zero.md](../../docs/00-orientation/client-zero.md).
