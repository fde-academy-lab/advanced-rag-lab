# LLD · `store.py`

The index. Everything else in the system reads from it, so its invariants are load-bearing for
correctness in a way nothing else's are.

## Contract

```python
class InMemoryIndex:
    def upsert(chunks, vectors, index_version: str, embedder_tag: str) -> None
    def set_alias(alias: str, index_version: str) -> None
    def bm25(query: str, n: int, acl: str | None) -> list[Hit]
    def exact_vector(vec, n: int, acl: str | None, build_graph: bool = True) -> list[Hit]
    def ann_vector(vec, n: int, ef: int, acl: str | None) -> list[Hit]
```

Every retrieval method returns `list[Hit]`, where a `Hit` carries a `chunk_id` that resolves in
this store. That is the whole interface seam ① depends on.

## Storage

Three representations of the same chunks, kept consistent by `upsert` being the only writer.

| Structure | Purpose | Cost |
|---|---|---|
| `chunks` table | Source of truth: text, ordinal, doc_id, acl_group, index_version | O(n) rows |
| `chunks_fts` (FTS5) | Inverted index for BM25 | ~1.4× text size |
| `vectors` (numpy matrix + id map) | Dense retrieval | n × d float32 |
| NSW graph | ANN traversal, built lazily | n × (k + 4) int32 |

## Invariants

These are asserted in `tests/` because violating any of them produces plausible numbers rather
than an error.

**1 · One embedder tag per live index.** Cosine similarity across two embedding spaces is
meaningless *and silent*. A live index containing more than one `embedder_tag` fails loudly.

**2 · The alias is the only thing readers resolve.** Nothing reads `index_version` directly.
That is what makes a rollback a pointer swap rather than a rebuild.

**3 · `upsert` is idempotent on unchanged content.** Guaranteed by content-addressed chunk ids
(ADR-0004). Re-ingesting an unedited document is a no-op, not a churn.

**4 · ACL filtering happens before scoring, never after.** See ADR-0011 for k-collapse and score
leak.

**5 · The analyzer configuration is part of the index version.** ADR-0013.

## The FTS5 tokenizer

```sql
tokenize = "unicode61 remove_diacritics 2 tokenchars '_-'"
```

Without `tokenchars '_-'`, `ERR_CONN_RESET` becomes `err` / `conn` / `reset`, each of which
appears in nearly every incident report. Identifier-slice recall 0.81 → 0.34 while the aggregate
moves 5 points. Full reasoning in ADR-0013.

## The graph, and the cache bug that hid its failure

`_matrix` was originally cached keyed on `index_version` alone. A call to
`exact_vector(build_graph=False)` stored an entry with `graph=None`, and a later `ann_vector`
found that entry, saw no graph, and silently fell back to exact search.

The symptom was ANN results that were suspiciously good. The cache was returning exact search and
reporting it as approximate — so the ANN path was never actually exercised, and when it finally
was, recall was 0.00 (issue #2, ADR-0010).

**Fix:** matrix and graph cached separately, graph built lazily on first ANN use.

```python
rng = np.random.RandomState(17)
longr = rng.randint(0, n, size=(n, min(4, max(1, n - 1))))
entry["graph"] = np.concatenate([near, longr], axis=1)
```

The seed is fixed so graph construction is reproducible. A different seed changes recall by a
fraction of a point and changes *which* queries fail, which matters when debugging.

## Complexity

| Operation | Cost | Note |
|---|---|---|
| `upsert` n chunks | O(n·L) | Dominated by FTS5 tokenisation, not the insert |
| `bm25(n)` | O(\|q\| · posting length) | Sub-linear in corpus size; that is the point of an inverted index |
| `exact_vector` | O(N·d) | Full scan. Fine at N = 2,430, not at 10⁶ |
| `ann_vector(ef)` | O(ef · log N) expected | Only with long-range links present |
| Graph build | O(N² d) | Brute-force k-NN. The honest scaling limit of this implementation |

Graph build is the wall. At 2,430 chunks it is ~2 s. At 10⁵ it is unusable, and that is where
seam ① exists to be used.

## Failure modes

| Symptom | Cause | Where it shows |
|---|---|---|
| ANN recall exactly 0.00 | Graph has no long-range links | Only at scale; small fixtures pass |
| ANN recall suspiciously high | Cache returning exact results | Nowhere — it looks like success |
| Identifier queries return everything | Analyzer split the identifier | Slice metric only, not aggregate |
| Restricted user gets empty results | Post-filter instead of pre-filter | Only for restricted personas |
| Plausible but degraded results | Mixed embedder versions | Nowhere, until asserted |

Four of those five are invisible in aggregate metrics. That is the argument for slice-level
measurement, stated as a property of the storage layer rather than of the evaluation.

## What would change this design

**Corpus past ~10⁵ chunks.** The brute-force graph build and the full-scan exact path both stop
being viable. Seam ① takes a real backend; the interface does not change.

**Documents that update more often than they are read.** The content-hash upsert assumes reads
dominate. A write-heavy corpus wants a different id scheme and probably a real database.

**More than ~50 ACL groups.** The single filtered index stops being obviously right, and the
partition-versus-filter analysis in ADR-0011 would need redoing with different numbers.
