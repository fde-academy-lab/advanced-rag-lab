# ADR-0001: Run the entire retrieval stack in in-memory SQLite

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

The curriculum has to run in a training room, on hotel wifi, on whatever laptop a student
brought, in the ninety seconds before attention is lost. It also has to be *credible* to
engineers who ship retrieval systems for a living — a toy that mocks its retrieval teaches
nothing about retrieval.

Those two requirements pull hard against each other. Every serious vector database is a
service; every serious lexical index is a service.

## Options considered

### Option A — a real vector database in Docker
Qdrant, Weaviate or OpenSearch via docker-compose. Genuinely production-shaped.
**Costs:** Docker on every student laptop, an image pull over conference wifi, a service that
can be in a bad state at 9am, and a full class period lost to environment debugging. It also
teaches the *operation* of a specific product rather than the mechanics of retrieval.

### Option B — pure Python data structures
Dictionaries and NumPy arrays. Trivially portable.
**Costs:** it stops being a database. No SQL, no real BM25, no filters, no transactions —
and the moment a student asks "how would the ACL filter work here", the honest answer is
"differently from anywhere you will ever work".

### Option C — SQLite in memory
`sqlite3.connect(":memory:")` with FTS5 for the lexical index, a table for vectors, and an
ACL column. Ships with Python.

## Decision

Option C. The whole retrieval stack — lexical index, vector table, ANN graph, ACL scoping,
versioned indexes with an alias, tombstones — lives in one in-memory SQLite database.

## Consequences

**Good.** Zero install. BM25 is SQLite's own implementation over a genuine inverted index, so
the lexical leg is real rather than simulated. Filters and ACLs are SQL predicates, which is
exactly the shape they take in production. Blue/green index versions and alias swaps are
natural. The whole thing disappears on kernel shutdown, so no student ever has a stale index.

**Bad.** It does not scale, and cannot demonstrate distributed-index concerns like sharding
or replica lag. We built the ANN layer ourselves, which means the graph is ours to get right
— and we got it wrong first (see ADR-0004's sibling problem: a k-NN graph without long-range
links is not navigable, and recall collapsed as the corpus grew). The FTS5 tokenizer needed
`tokenchars '_-'` before identifiers were searchable at all, which is a real bug we had to
find rather than a lesson we planned.

**Revisit when:** the curriculum needs to teach sharding, replication or multi-region
residency. Those are genuinely not teachable here, and `docs/09-research/extension-points.md` #18 is the
migration path.
