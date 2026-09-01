# Low-level design

One document per module that carries a decision. Modules that are plumbing — thin wrappers,
dataclasses, glue — are not documented here, because an LLD for a file with no invariants is
noise that makes the real ones harder to find.

| Module | LLD | Carries |
|---|---|---|
| `store.py` | [store.md](store.md) | The index: FTS5, vectors, the NSW graph, ACLs, versions, aliases |
| `retrieve.py` | [retrieve.md](retrieve.md) | Fusion, the learned reranker, candidate generation |
| `metrics.py` | [metrics.md](metrics.md) | Recall variants, the bootstrap, κ, and the memoisation that made evaluation 4× faster |
| `chunking.py` | [chunking.md](chunking.md) | Seven strategies and the id scheme that makes upserts possible |
| `context.py` | [context.md](context.md) | Token budgets, provenance, volatility ordering |
| `agent.py` | [agent.md](agent.md) | The loop, its stop conditions, and trace scoring |

Each follows the same shape: **contract · invariants · complexity · failure modes · what would
change this**. The last section is the one worth reading if you are here to extend something.

`overview.md` is the HLD and is assumed. These do not re-explain the four planes.

## Failure-mode index

Someone debugging does not yet know which module they are in — that is why they are debugging.
This aggregates the failure tables from all six LLDs, with the column that decides how you will
find it.

| Symptom | Module | Visible in aggregate metrics? |
|---|---|---|
| ANN recall exactly 0.00 | [store](store.md) | Yes, dramatically — but only at scale |
| ANN recall suspiciously *high* | [store](store.md) | **No** — it looks like success |
| Identifier queries return everything | [store](store.md) | **No** — 5-point aggregate move, slice collapses |
| Restricted user gets empty results | [store](store.md) | **No** — only for restricted personas |
| Plausible but degraded results everywhere | [store](store.md) | **No** — mixed embedder versions, silent |
| Rerank worse at every k | [retrieve](retrieve.md) | Yes |
| Fusion worse than either leg | [retrieve](retrieve.md) | Yes |
| Recall flat as `n_candidates` grows | [retrieve](retrieve.md) | Yes |
| Recall improves after an unrelated refactor | [metrics](metrics.md) | **No** — gold resolution loosened |
| Interval suspiciously narrow | [metrics](metrics.md) | **No** — resampled documents, not queries |
| κ near zero with high agreement | [metrics](metrics.md) | n/a — working as intended, report marginals |
| Every chunking strategy scores the same | [chunking](chunking.md) | Yes |
| Recall drops after a chunker change | [chunking](chunking.md) | Yes — ids changed, index holds orphans |
| Cache hit rate collapses | [context](context.md) | **No** — right answers, larger bill |
| Answers cite chunks not in context | [context](context.md) | **No** — provenance renumbered |
| Loops until budget on easy questions | [agent](agent.md) | Cost only |
| Answers confidently on unanswerable | [agent](agent.md) | Only if abstention is measured separately |

**Eleven of seventeen are invisible in an aggregate metric.** That is the argument for
slice-level measurement, stated as a property of the system rather than of the evaluation — and
it is why `abstention_recall` and `cost_usd` are on the scorecard despite not being gated.

## Modules without an LLD

Not an oversight. Each is plumbing with no invariant worth stating.

| Module | Why not |
|---|---|
| `pipeline.py` | Config object and a loop over the other modules |
| `trace.py` | Append-only record plus a diff; no decisions |
| `viz.py`, `tables.py` | Rendering |
| `catalog.py` | Static data |
| `bootstrap.py` | Environment setup |
