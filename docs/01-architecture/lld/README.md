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
