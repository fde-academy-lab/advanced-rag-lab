# Lost in the Middle — Liu et al., 2023

**Paper:** *Lost in the Middle: How Language Models Use Long Contexts*, TACL 2024, arXiv 2307.03172.

## Claim

Model performance at retrieving a fact from its context is highest when the fact appears at the
beginning or end of the context, and degrades in the middle — a U-shaped curve over position.

## Method

Multi-document QA with a controlled number of distractor documents, position of the gold document
varied systematically. Context lengths well beyond what an 8-chunk window produces.

## What we tested

Fixed the retrieved set, permuted gold evidence position across all 8 slots, measured answer
correctness at each position. n = 243, so every position gets the full eval set.

Holding the set fixed and permuting is the design that matters. The wrong design — comparing
naturally-occurring positions — has position correlated with retrieval score, so you measure
score rather than position.

## Result

| position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| answer correct | 0.44 | 0.43 | 0.41 | 0.40 | 0.40 | 0.41 | 0.42 | 0.43 |

The curve has the right shape — ends above middle. Amplitude **0.04**. Paired interval on
position 1 versus position 5: **[−0.01, +0.09]**, which spans zero.

**Verdict: consistent in direction, not established at this scale.** n = 243 across 8 positions is
underpowered for a 4-point effect. We can neither confirm nor refute it here, and saying so is the
honest outcome rather than the disappointing one.

## Why it did not transfer cleanly

Mechanically sensible: the middle of an 8-item list is not far from either end in attention terms.
The paper's effect is large at 20+ documents and shrinks as the context shortens.

## What would change the answer

**A longer window.** At 20+ chunks the effect grows and would likely clear the noise band.

**Conversation history rather than chunks.** This is where it bites hardest in production — the
relevant turn buried mid-transcript, at much larger distances than any chunk window produces.

## What we did with it

Nothing, deliberately. Position-optimal ordering depends on this query's ranking, so it changes
the prompt prefix every query and defeats prompt caching. At an amplitude of 0.04 inside the noise
band, the cache is worth more. See ADR-0012 — and note that conclusion is corpus- and
window-specific, and reverses at longer contexts.
