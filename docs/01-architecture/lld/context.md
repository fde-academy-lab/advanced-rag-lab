# LLD · `context.py`

Turns a ranked list into a prompt. The module where cost decisions and quality decisions are the
same decision.

## Contract

```python
def pack(hits: list[Hit], budget_tokens: int) -> Context
```

`Context` carries the assembled text plus a provenance block per included chunk, so a citation in
the generated answer resolves back to a `chunk_id`, a `doc_id`, an ordinal and a date.

## The hard cap

The budget is a **hard cap**, not a target. `pack` fills until the next chunk would exceed it,
then stops.

Truncating a chunk to fit is deliberately not supported. A half chunk is a fact with its
qualifier removed — "the rate was raised to 4.5%" without "for accounts opened before March" is
worse than nothing, because it is confidently wrong rather than absent.

## Provenance

Each packed block is prefixed:

```
[S3] doc=acme-q3-incident-0412 · chunk 7 · 2024-08-14 · score 0.71
```

Present so that a citation is checkable and so that a wrong answer can be traced to whether the
evidence was absent, present-and-unused, or present-and-misread. Those three have different fixes
and are indistinguishable without provenance.

## Volatility ordering

Blocks are assembled most-stable-first (ADR-0012):

```
system prompt → instructions → few-shot → retrieved chunks → volatile state → question
```

Everything before the retrieved chunks is cacheable; nothing after is. Prompt caching requires a
**byte-identical** prefix, so this ordering is a cost decision.

Measured: moving a timestamp out of the system prompt took cache hit rate 4% → 71% and cost per
query down 58%. Volatility is measured relative to the cache key, not absolutely — a field stable
per tenant belongs before the barrier if the cache is keyed per tenant.

## Position sensitivity

The lost-in-the-middle effect argues for putting the best chunk first and the second-best last.
That ordering depends on this query's ranking, so it changes the prefix every query and caches
nothing.

Measured on this corpus at an 8-chunk window:

| position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| answer correct | 0.44 | 0.43 | 0.41 | 0.40 | 0.40 | 0.41 | 0.42 | 0.43 |

Right shape, amplitude 0.04, and position 1 vs 5 gives [−0.01, +0.09] — inside the noise band.
So the cache wins here.

**That conclusion is corpus- and window-specific.** At 20+ chunks the position effect grows and
the argument reverses. The place it bites hardest in production is not chunk ordering at all but
long conversation history, where the relevant turn is buried much further from either end.

## Complexity

O(n) over hits, with a token count per chunk. Token counting is the cost — it is called once per
candidate chunk, not once per packed chunk, because the cap has to be checked before inclusion.
Counts are cached on the chunk.

## Failure modes

| Symptom | Cause |
|---|---|
| Answers cite chunks not in the context | Provenance markers renumbered after packing |
| Cache hit rate collapses | Something volatile moved before the barrier |
| Context precision falls while recall rises | Working as intended — this is the k tradeoff, not a bug |
| Generator ignores late evidence | Position sensitivity; check the window size before reordering |

## What would change this design

**Compression at seam ⑧.** Summarising or deduplicating chunks before packing would let a wider
retrieval fit the same budget — retrieve 20, rerank, compress, pack 8. That is the fix for the
recall/precision tension in EX-07, and it is the strongest untried extension in this module.

**A model that handles 200k tokens well.** Then the budget stops binding and the whole module
becomes ordering rather than selection. Worth revisiting rather than assuming; a larger window
does not remove the cost argument, it only removes the quality one.
