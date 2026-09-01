# ADR-0010 · Long-range links in the ANN graph

- **Status:** Accepted
- **Date:** 2026-08-26
- **Deciders:** Maintainers
- **Related:** issue #2, ADR-0001 (in-memory SQLite)

## Context

The ANN index was a pure k-NN graph — each node linked to its 12 nearest neighbours, searched
greedily. It worked at 230 chunks. At 2,430 chunks, recall against exact search was **0.00** at
ef=64 and 0.03 at ef=256.

The search loop was correct. Instrumenting the walk showed every query terminating after 4–5
steps with the distance barely moving: greedy search was finding a local minimum immediately and
the true nearest neighbour was nowhere near the entry point.

## The mechanism

A pure k-NN graph is not navigable. Every edge is short, so the graph is a lattice of tight local
neighbourhoods with diameter O(n^(1/d)). Greedy search cannot cross it — it stops at the first
local minimum long before traversing the space.

At 230 chunks the diameter was small enough that this did not show. The failure is **latent in
corpus size**, which is why every test passed: every test ran on a small fixture, and a small
fixture is a regime where the bug cannot appear.

## Options

### A · Add random long-range links (Kleinberg small-world)

Augment each node's short edges with a few random long edges.

### B · Implement full HNSW

Hierarchical layers with exponentially-decaying membership: sparse upper layers for coarse
routing, dense base layer for descent.

### C · Drop ANN, use exact search only

The corpus is small; exact search over 2,430 vectors is fast.

### D · Use a library

faiss, hnswlib, or a hosted vector store.

## Decision

**Option A**, four random long-range links per node.

```python
rng = np.random.RandomState(17)
longr = rng.randint(0, n, size=(n, min(4, max(1, n - 1))))
entry["graph"] = np.concatenate([near, longr], axis=1)
```

Recall at ef=64: 0.00 → **0.94**. At ef=128: 0.98.

**Why not B.** HNSW is the right answer for production and the wrong answer here. It is the same
principle organised rather than randomised, and the organisation obscures the principle. A reader
who understands why four random edges fix this understands HNSW; a reader shown HNSW first learns
a data structure and not the reason for it.

**Why not C.** Exact search would work and would delete the lesson. The ANN recall curve — and
specifically watching it collapse — is one of the few places a reader can see an approximation's
cost rather than being told about it.

**Why not D.** A library fixes the symptom and teaches nothing. This repository exists so the
failure is visible; importing the fix makes it invisible. Seam ① is there for anyone who wants
a real backend, and ADR-0001 covers the general principle.

## Consequences

**Good.** Kleinberg's O(log²n) navigability result becomes something a reader watches happen
rather than reads about. The fix is five lines and the explanation is a paragraph.

**Bad.** Random long-range links are the crude version. Kleinberg's result requires links drawn
with probability proportional to d(u,v)^−α with α equal to the lattice dimension; uniform random
is an approximation that works at this scale and would degrade at larger ones.

**The regression test that matters.** `tests/test_retrieval.py` asserts monotonicity — recall
must not decrease as ef increases, and recall at fixed ef must not collapse as n grows. The
original bug passed every test because no test varied n. That is the real lesson: the test suite
was testing a regime the bug could not appear in.
