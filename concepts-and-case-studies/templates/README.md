# Templates

Four artefacts an FDE produces repeatedly. Each is short on purpose — a template nobody fills in
is worse than no template, because it creates the appearance of a process.

| Template | Use it when | The part people skip |
|---|---|---|
| [prd.md](prd.md) | Defining an AI feature | Failure behaviour, and a cost envelope |
| [adr-lite.md](adr-lite.md) | A decision was contested | "Would change if" — the falsifier |
| [pdlc.md](pdlc.md) | Planning an engagement | The eval set precedes the build |
| [solution-dissection.md](solution-dissection.md) | A build shipped and works | "Measured against removing it?" |

Each has a worked example drawn from [SC-01](../scenarios/SC-01-incident-search.md), so you can
see the filled-in version rather than only the blank.

## Why these four

They cover the points where an engagement most often goes wrong quietly:

- A **PRD** without measurable acceptance criteria means sign-off is an opinion.
- A decision without an **ADR-lite** gets made twice, and the second time the argument that
  settled it is gone.
- A **PDLC** that builds before it measures produces improvements nobody can verify.
- A build without a **dissection** accumulates components nobody can justify, and one of them is
  making things worse.

That last one is not hypothetical: a reranker in this repository improved against every previous
version of itself while being worse than having no reranker at all.
