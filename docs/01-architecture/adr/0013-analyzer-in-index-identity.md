# ADR-0013 · The analyzer configuration is part of the index identity

- **Status:** Accepted
- **Date:** 2026-08-25
- **Deciders:** Maintainers
- **Related:** issue #1, ADR-0004 (stable chunk ids)

## Context

The FTS5 table was created with the default `unicode61` tokenizer. That splits
`ERR_CONN_RESET` into `err` / `conn` / `reset`, all three of which appear in nearly every
incident report in this corpus.

The identifier does not merely fail to match — it matches *everything*, and BM25's IDF rates all
three components as low-information. A high-precision query becomes a high-recall one.

| slice | `tokenchars '_-'` | default | Δ |
|---|---|---|---|
| identifier queries | 0.81 | 0.34 | **−0.47** |
| everything else | 0.76 | 0.76 | −0.00 |
| **overall average** | 0.7645 | 0.7104 | −0.054 |

The five-point aggregate drop is the kind of number that passes review. The user-visible symptom
is "search is broken for error codes", which is the highest-urgency query class, and no aggregate
metric would have paged anyone.

## Decision

Two things, and the second is the general one.

**1 · The tokenizer keeps `tokenchars '_-'`.**

```sql
tokenize = "unicode61 remove_diacritics 2 tokenchars '_-'"
```

The comment above this line in `store.py` is deliberately long. It documents the *reason*, not
the syntax, so the next person to touch it knows what they are choosing between.

**2 · The analyzer configuration is part of the index version string.**

Any change to the analyzer chain — tokenisation, stemming, case folding, diacritic handling —
silently invalidates every document indexed before it. Documents indexed under two analyzers in
one live index produce a corpus that is half one scheme and half another, with no error anywhere.

Putting the analyzer in the index identity means such a change *forces a reindex* rather than
producing a mixed index. This mirrors what ADR-0004 does for the embedder tag, and for the same
reason: an index is defined by how its contents were processed, not only by what they were.

## Consequences

**Good.** An analyzer change becomes a deliberate, visible operation with a rebuild attached. A
mixed-analyzer index becomes detectable rather than silent.

**Bad.** Reindexing 2,430 chunks is trivial; reindexing 1.2M documents to change a tokenizer is
a real operation with a real cost, and the design forces you to pay it rather than letting you
avoid it. That is intended.

**The wider lesson, which is about measurement rather than tokenisation.** This bug was found by
a user, not by monitoring, because the aggregate never moved enough to alert. **Slice-level
alerting is not a refinement of aggregate alerting; it is the only kind that would have worked
here.** A metric averaged over query classes is blind to a class collapsing, and query classes
are exactly how users experience a search system.
