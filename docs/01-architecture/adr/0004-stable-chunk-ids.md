# ADR-0004: Derive chunk ids from doc_id + ordinal + content hash

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

The freshness lesson — keeping an index current without a nightly full rebuild — only works if
an incremental update is genuinely cheaper than a rebuild. That depends entirely on the chunk
identifier.

## Options considered

### Option A — sequential integers
`chunk_0`, `chunk_1`, …
**Costs:** re-chunking a document shifts every subsequent id, so a one-paragraph edit
invalidates the whole document's vectors. It also makes an upsert impossible: you cannot tell
whether `chunk_7` is the same chunk it was yesterday.

### Option B — a hash of the content alone
**Costs:** loses provenance — you cannot tell which document or which position a chunk came
from without a lookup, and two identical boilerplate paragraphs in different documents collide.

### Option C — `doc_id : ordinal : sha1(text)[:10]`

## Decision

Option C.

## Consequences

**Good.** An unchanged chunk keeps its id across a re-chunk, so it needs no new vector — which
is what makes the content-hash diff worth doing at all. A changed chunk gets a new id that an
upsert writes over, and the old one is tombstoned rather than deleted, so in-flight queries
stay consistent. Provenance is readable straight off the id, which is why a packed evidence
block can carry `doc_id: nw-8842 · chunk: 3/11` and a trace can be diffed between two runs.

**Bad.** Ids are long and appear in traces, which makes trace output wide. Ordinal is
chunking-strategy-dependent, so the *same* text chunked two ways gets two ids — correct, but it
surprises people the first time. And a pure metadata edit that touches the body normalisation
will churn ids unnecessarily if the normaliser is not stable, which makes the normaliser a
load-bearing component nobody thinks about.

**Revisit when:** chunks need to be addressable across chunking strategies — for example if a
future extension wants to compare two strategies' retrieval of "the same" passage. That would
need a separate content-addressed identity alongside this one.
