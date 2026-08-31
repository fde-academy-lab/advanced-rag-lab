# ADR-0006: Draw notebook diagrams with matplotlib, not Mermaid

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

The teaching format is: a flowchart of what the code is about to do, then the code, then a
summary diagram and a decision tree. That means ~45 diagrams inside notebooks, and they have to
render wherever a student opens them.

## Options considered

### Option A — Mermaid in markdown cells
Concise source, renders on GitHub and in recent JupyterLab.
**Costs:** renders in *some* environments and shows raw text in others — older JupyterLab, some
VS Code configurations, PDF export, nbconvert without a plugin. A diagram that silently
degrades to source text is worse than no diagram, and a student cannot tell whether they are
seeing a bug.

### Option B — pre-rendered PNGs
Renders everywhere.
**Costs:** binary assets in git, a build step, and diagrams that cannot use the numbers the
notebook just computed.

### Option C — matplotlib, drawn by a small diagram DSL

## Decision

Option C for notebooks (`nanorag/viz.py`), **and Mermaid for the markdown docs** — where
GitHub is the only rendering target and it renders reliably.

## Consequences

**Good.** Diagrams are ordinary cell outputs: they survive nbconvert, PDF export and every
Jupyter frontend. They can be *data-driven* — the fault-isolation tree renders with the branch
a real failing query actually took highlighted, which is the single most useful diagram in the
curriculum and is impossible with static Mermaid. One definition in `catalog.py` produces the
figure, the table and the executable predicate, so they cannot drift apart.

**Bad.** `viz.py` is 623 lines, which is 623 lines of diagram code we own. Layout is manual:
we compute text wrapping and box heights from font metrics, and got it wrong the first time —
text overflowed its boxes until measuring and drawing were unified into one function. Changing
a diagram means changing Python, not a two-line diff.

**Revisit when:** Mermaid rendering becomes universal across Jupyter frontends and export
paths. Even then, the data-driven diagrams stay in matplotlib.
