# EX-04 · Measure boundary damage, not recall

**Difficulty** ★★★☆☆ · **Seam** ④ chunker · **Time** 2 h · **Notebook** `01`, `03`
**Thread** Exercises & Submissions → `EX-04`

## Setup

Seven chunking strategies are implemented: `fixed`, `recursive`, `structural`, `semantic`,
`parent_document`, `contextual`, `late_chunking`. Comparing them on evidence recall gives
differences that are mostly inside the noise band, which is the uncomfortable result most
chunking comparisons quietly produce.

## Task

Define and measure **boundary damage**: the fraction of gold evidence spans that are split
across two chunks by a given strategy. Then check whether it predicts anything.

1. For each strategy, compute boundary damage over the eval set's gold spans.
2. Compute evidence recall and full-chain recall for the same strategies.
3. Test whether boundary damage correlates with either.

## Acceptance

- Boundary damage per strategy, with the definition you used written out. There is more than
  one reasonable definition and yours must be stated.
- A correlation, with an interval, or an honest statement that n = 7 is too small to establish
  one.
- One sentence on which strategy you would choose and what you are trading away.

## The trap

`n = 7` strategies is not enough points to establish a correlation, and computing Pearson's r on
seven points and reporting it as a finding is the error this exercise is built to catch. If you
want a correlation you need more configurations — vary chunk size within a strategy, which gives
you thirty points instead of seven.

The other trap: **fit the embedder on documents, not chunks.** If you fit on chunks, the
chunking strategy changes the embedding space, and your comparison is measuring two things and
attributing the result to one.

## What good looks like

A submission that reports boundary damage ranging widely across strategies, evidence recall
ranging narrowly, and concludes that the two are only weakly connected *on this corpus* — while
naming the corpus property that would make them connect strongly (gold spans that are long
relative to chunk size).

## Extension

Boundary damage assumes you know where the gold span is. In production you do not. Propose a
proxy that could be computed without labels, and say how you would validate it.
