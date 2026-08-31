# Architecture

> **Audience:** anyone about to change `nanorag/`, and anyone who wants to explain this system
> in an interview. Read [the README's architecture section](../../README.md#architecture) first for
> the context and HLD diagrams; this document is the level below that.

## Contents

- [Design principles](#design-principles)
- [Module map](#module-map)
- [Data model](#data-model)
- [Component detail (LLD)](#component-detail-lld)
- [The seams — where to plug things in](#the-seams--where-to-plug-things-in)
- [Local → AWS](#local--aws)
- [Performance notes](#performance-notes)
- [Invariants the tests enforce](#invariants-the-tests-enforce)

---

## Design principles

Five decisions shape everything else. Each has an [ADR](adr/) with the alternative that lost.

| # | Principle | Consequence you will feel |
|---|---|---|
| 1 | **Everything runs offline and deterministically** | Two runs produce identical numbers, so a delta is a real delta. Non-determinism would make the whole measurement curriculum untellable. |
| 2 | **Concepts in notebooks, infrastructure in the package** | You read BM25 in notebook 04, not in a library you are asked to trust. But you do not re-implement SQLite. |
| 3 | **Swapping a backend must not change the harness** | `Hit`, `Embedder`, `Generator` and `Reranker` are the only interfaces that matter. Bedrock plugs into all four. |
| 4 | **Gold labels are true by construction** | The corpus is generated from a fact graph, so there is no annotation-error floor under any number. |
| 5 | **A measurement without an interval is an anecdote** | `paired_bootstrap` is in the critical path of the PR template and the CI gate, not an optional extra. |

---

## Module map

```mermaid
graph TB
    subgraph data["Data layer"]
        CO["corpus.py<br/>fact graph → docs, chunks, eval set"]
        CH["chunking.py<br/>7 strategies, stable ids"]
        EM[embed.py<br/>LSA · Hashing · ST · Bedrock]
    end
    subgraph store["Storage layer"]
        ST["store.py<br/>sqlite :memory: — FTS5, vectors,<br/>NSW graph, ACL, versions, aliases"]
        TR[trace.py<br/>queryable trace store + diff]
    end
    subgraph retrieval["Retrieval layer"]
        RE[retrieve.py<br/>fusion · rerankers · packing]
        CX["context.py<br/>prompt assembly, volatility order"]
        GE[generate.py<br/>extractive · Bedrock · Claude]
    end
    subgraph measure["Measurement layer"]
        ME["metrics.py<br/>recall, nDCG, κ, bootstrap"]
        JU["judge.py<br/>rubrics, calibration, bias probes"]
        PI["pipeline.py<br/>config object + evaluate()"]
        CS["costs.py<br/>tokens, cache, latency, unit economics"]
    end
    subgraph teach["Teaching layer"]
        CA[catalog.py<br/>deck trees + matrices as data]
        TE[trees.py<br/>render · tabulate · execute]
        VI[viz.py]
        TA[tables.py]
    end
    AG[agent.py<br/>decompose → tool → sufficiency → stop]
    BE[bedrock.py<br/>KB retriever + local→AWS map]
    BO[bootstrap.py<br/>one-click env + seeding]

    CO --> CH --> EM --> ST
    ST --> RE --> CX --> GE
    GE --> TR
    RE --> PI
    PI --> ME
    ME --> JU
    PI --> CS
    RE --> AG
    ST -.->|same Hit| BE
    CA --> TE --> VI
    TE --> TA

    classDef d fill:#EAF4F7,stroke:#2F8CA3,color:#101318
    classDef s fill:#EFEDFB,stroke:#6C5CE0,color:#101318
    classDef r fill:#FBF1E2,stroke:#E9A83C,color:#101318
    classDef m fill:#E9F3EE,stroke:#3F8F6E,color:#101318
    classDef t fill:#F6F4EF,stroke:#C9C4B8,color:#3A414B
    class CO,CH,EM d
    class ST,TR s
    class RE,CX,GE,AG r
    class ME,JU,PI,CS m
    class CA,TE,VI,TA,BO,BE t
```

| Module | Lines | Responsibility | Do not put here |
|---|---:|---|---|
| `corpus.py` | 1,220 | Fact graph, document rendering, chunk/eval schemas, MultiHop-RAG loader | Retrieval logic |
| `chunking.py` | 288 | Seven strategies; stable chunk ids; token estimation | Anything that needs an index |
| `embed.py` | 305 | Encoder implementations behind one interface; `EmbedderInfo` version pinning | Similarity search |
| `store.py` | 444 | SQLite schema, FTS5 lexical, exact + ANN vector search, ACL scoping, versions/aliases/tombstones | Ranking policy |
| `retrieve.py` | 617 | Fusion, rerankers, pair features, dedup, ordering, packing | Prompt strings |
| `context.py` | 178 | Prompt assembly, budget slices, provenance blocks | Model calls |
| `generate.py` | 247 | Readers behind one interface + the fault-injection fixture | Scoring |
| `metrics.py` | 283 | Every metric, plus κ and the paired bootstrap | Anything that runs a pipeline |
| `judge.py` | 271 | Rubrics as artefacts, calibration, bias probes | Retrieval metrics |
| `pipeline.py` | 190 | The config object, `run()`, `evaluate()` | New metrics |
| `agent.py` | 279 | Decomposition, tool choice, sufficiency, stop conditions, trace scoring | Single-shot logic |
| `costs.py` | 206 | Token categories, prompt cache, latency model, unit economics | Real provider calls |
| `trace.py` | 142 | Trace record, trace store, `diff_traces` | Analysis |
| `catalog.py` | 640 | The deck's trees and matrices as executable data | Behaviour |
| `bedrock.py` | 249 | KB retriever, preflight, local→AWS mapping | Offline logic |

---

## Data model

```mermaid
erDiagram
    DOCUMENT ||--o{ PASSAGE : contains
    DOCUMENT ||--o{ CHUNK : "chunked into"
    CHUNK ||--o| VECTOR : "embedded as"
    EVAL_QUESTION }o--o{ PASSAGE : "gold evidence anchors"
    TRACE }o--|| EVAL_QUESTION : "answers"
    TRACE ||--o{ PACKED_BLOCK : "packs"
    PACKED_BLOCK }o--|| CHUNK : "references"

    DOCUMENT {
        string doc_id PK
        string title
        string source "newswire|filings|techblog|transcript|support_kb|incident"
        string published "ISO date"
        tuple  acl "groups that may read it"
        string tenant
        string content_hash "drives the incremental path"
    }
    CHUNK {
        string chunk_id PK "doc_id + ordinal + content hash"
        string doc_id FK
        int    ordinal
        string heading "carried from the document's own structure"
        string text
        string embedder_tag "pinned; a mixed index is an outage"
    }
    EVAL_QUESTION {
        string qid PK
        string query
        string answer
        string question_type "inference|comparison|temporal|null"
        tuple  evidence_anchors "gold, true by construction"
        int    hops
        string slice "dev|frozen"
        string persona "drives the ACL scope"
    }
    TRACE {
        string trace_id PK
        json   candidates "id, score, rank, method"
        json   packed "sid, chunk_id, tokens, score"
        json   stage_ms "retrieve|rerank|pack|generate"
        int    k_collapse "post-filter damage, if any"
    }
```

**Why `chunk_id = doc_id + ordinal + content hash.`** An unchanged chunk keeps its id across a
re-chunk and needs no new vector; a changed one gets a new id an upsert can write over.
Delete-then-insert orphans rows; upsert-then-tombstone does not. This single choice is what
makes the incremental freshness path cheap — see [ADR-0004](adr/0004-stable-chunk-ids.md).

---

## Component detail (LLD)

### `store.InMemoryIndex`

```mermaid
classDiagram
    class InMemoryIndex {
        +db: sqlite3.Connection ":memory:"
        -_cache: dict "version → ids, matrix, graph"
        -_acl_cache: dict "(version, acl, filters) → visible ids"
        +upsert(chunks, vectors, version, embedder_tag) int
        +tombstone(chunk_ids, version) int
        +compact(version) int
        +set_alias(alias, version)
        +resolve(alias) str
        +lexical(query, n, acl_groups, filters) List~Hit~
        +exact_vector(qvec, n, acl_groups, filters) List~Hit~
        +ann_vector(qvec, n, ef_search, filter_mode) List~Hit~
        +mixed_version_check(version) dict
        -_allowed_ids(version, acl, filters) set
        -_matrix(version, build_graph) tuple
    }
    class Hit {
        +chunk_id: str
        +score: float
        +rank: int
        +method: str
        +doc_id, text, title, source, published, acl
    }
    InMemoryIndex ..> Hit : returns
```

Three implementation details worth knowing before you change this file:

1. **`tokenchars '_-'` on the FTS5 table is load-bearing.** The default `unicode61` tokenizer
   splits `ERR_CONN_RESET` into `err` / `conn` / `reset`, which appear in every incident
   report — so the one query lexical retrieval should win outright silently becomes its worst
   case. Notebook 04 §4.3 measures it.
2. **The k-NN graph has long-range links.** A pure k-NN graph is a lattice of tight
   neighbourhoods with no shortcuts; greedy search walks into the nearest cluster and cannot
   leave, so recall collapses as the corpus grows even though every edge is correct. Four
   random links per node (Kleinberg's construction, which HNSW's upper layers provide)
   restore the logarithmic hop count.
3. **The ACL set is cached, and the cache is cleared on every write.** Re-deriving the visible
   set per query costs more than the vector search it supports. The `_acl_cache` clear on
   `upsert` / `tombstone` / `compact` is the correctness half of that optimisation.

### `retrieve.ProxyCrossEncoder`

Eight features that only a *pair* can produce, then logistic regression. It is far weaker
than a trained transformer and architecturally the same animal: it scores the pair, nothing is
precomputable, cost is linear in `N`, and batching rather than looping is what keeps latency
in the tens of milliseconds.

| Feature | What it measures | Why a bi-encoder cannot produce it |
|---|---|---|
| `coverage` | Query-term coverage, BM25-style length-normalised | Needs both sides |
| `proximity` | Tightness of the window containing matched terms | Needs the query's terms |
| `phrase` | Longest contiguous query n-gram appearing verbatim | Needs the query |
| `title` | Overlap with title + heading path | Needs the query |
| `maxsim` | Mean over query tokens of best-matching passage token | **The key one** — a bi-encoder compresses the passage before it has seen the query |
| `doc_cosine` | Whole-passage similarity in latent space | This one a bi-encoder *can* produce |
| `exact_id` | An identifier matched literally | Needs the query |
| `length` | Log passage length | Lets the model learn its own length prior |

`fit()` is plain gradient-descent logistic regression, deliberately small enough to read. The
interesting part is not the optimiser — it is that **the training set must come from questions
the frozen slice does not contain**, or the number you report at the end is a memory rather
than a result.

### `pipeline.RagPipeline`

```mermaid
classDiagram
    class RetrievalConfig {
        +n_candidates: int = 100
        +k: int = 8
        +evidence_token_cap: int = 6000
        +fusion: str "rrf|weighted|dense|lexical"
        +rrf_k: int = 60
        +alpha: float "dense share in weighted fusion"
        +rerank: str "none|cross|late"
        +rerank_depth: int = 50
        +ann: bool
        +ef_search: int = 64
        +order: str "score|edges"
        +index_version: str
        +acl_groups: tuple
        +filter_mode: str "pre|post"
    }
    class RagPipeline {
        +index, embedder, cfg, generator, reranker, trace_store
        +variant(name, **cfg_updates) RagPipeline
        +run(query, qid, acl_groups) Trace
    }
    RagPipeline *-- RetrievalConfig
```

`variant()` is the whole ergonomics of the curriculum: *change one thing, re-run, write down
the delta.* It returns a copy with some knobs changed and shares the index, the encoder and
the trace store, so a sweep costs nothing but the evaluation itself.

---

## The seams — where to plug things in

Every extension in [EXTENSION-POINTS.md](../09-research/extension-points.md) attaches at exactly one of
these. If your idea does not fit one, it is probably two ideas.

```mermaid
flowchart LR
    S1(["① Corpus / chunking<br/>chunking.STRATEGIES"]) --> S2
    S2(["② Encoder<br/>BaseEmbedder"]) --> S3
    S3(["③ First-stage retriever<br/>.search(query, cfg) → List[Hit]"]) --> S4
    S4(["④ Fusion<br/>rrf() / weighted_fusion()"]) --> S5
    S5(["⑤ Reranker<br/>.rerank(query, hits, depth)"]) --> S6
    S6(["⑥ Packer<br/>pack_context() / order_for_position()"]) --> S7
    S7(["⑦ Prompt<br/>context.build_prompt()"]) --> S8
    S8(["⑧ Generator<br/>.generate(query, packed) → Answer"]) --> S9
    S9(["⑨ Judge / metrics<br/>judge_all(), metrics.*"])
    S3 -.-> A(["⑩ Agent loop<br/>decompose · choose_tool · sufficiency_check"])
    A -.-> S6
    classDef seam fill:#FBF1E2,stroke:#E9A83C,color:#101318
    class S1,S2,S3,S4,S5,S6,S7,S8,S9,A seam
```

| Seam | Interface to implement | Example already in the repo |
|---|---|---|
| ① Chunking | `fn(documents, **params) -> list[Chunk]`, registered in `STRATEGIES` | `chunking.contextual` |
| ② Encoder | `fit`, `encode_documents`, `encode_queries`, `.info: EmbedderInfo` | `BedrockEmbedder` |
| ③ Retriever | `.search(query, n, cfg) -> list[Hit]` | `GrepRetriever`, `BedrockKnowledgeBaseRetriever` |
| ④ Fusion | `fn(list_of_hit_lists, **kw) -> list[Hit]` | `rrf`, `weighted_fusion` |
| ⑤ Reranker | `.rerank(query, hits, depth) -> list[Hit]` | `LateInteractionReranker`, `BedrockReranker` |
| ⑥ Packer | `fn(hits, k, token_cap, ...) -> (list[Hit], int)` | `pack_context`, notebook 02's `quota_pack` |
| ⑦ Prompt | `build_prompt(...) -> PackedContext` | volatility-ordered default |
| ⑧ Generator | `.generate(query, packed) -> Answer` | `BedrockGenerator`, `UngroundedGenerator` |
| ⑨ Judge | `.judge_all(question, answer, packed) -> dict[str, Verdict]` | `BedrockJudge` |
| ⑩ Agent | `decompose`, `choose_tool`, `sufficiency_check` | rule-based defaults |

---

## Local → AWS

`nanorag.bedrock.LOCAL_TO_AWS` holds this mapping in code so it stays honest.

| Local | Managed equivalent | What changes when you move |
|---|---|---|
| `chunking.*` | Knowledge Base chunking strategy | `FIXED_SIZE` / `HIERARCHICAL` / `SEMANTIC` / `NONE`, set at ingest. `HIERARCHICAL` **is** parent-document retrieval. Changing it is a full re-ingest. |
| SQLite FTS5 | The KB's vector store with `overrideSearchType: HYBRID` | You no longer tune BM25 directly. Measure before assuming equivalence. |
| `InMemoryIndex` vectors | OpenSearch Serverless / Aurora pgvector / Pinecone / Redis | Mostly an ops and residency decision, not a recall one |
| `LsaEmbedder` | `amazon.titan-embed-text-v2:0`, `cohere.embed-*` | Set on the KB at creation; changing it is a full re-ingest |
| `ProxyCrossEncoder` | `amazon.rerank-v1:0`, `cohere.rerank-v3-5:0` | `rerankingConfiguration` on the retrieve call; priced per document |
| `build_prompt` + generator | `retrieve_and_generate`, or `Converse` with your own prompt | **Keep your own packing if citations matter.** You cannot debug a context you did not assemble. |
| `acl_groups` pre-filter | `retrievalConfiguration.filter` | Same rule: pre-filter, never post-filter |
| `HeuristicJudge` | Converse with a judge model, or Bedrock Evaluations | Pin the model and rubric version; do not judge with the generator's family |
| `TraceStore` | CloudWatch + model invocation logging + your own store | Retrieved text in traces inherits the corpus's compliance boundary |

---

## Performance notes

Two optimisations account for most of the speed, and both were found by profiling rather than
by guessing. They are worth reading because the *shape* of both problems recurs constantly.

| Problem | Symptom | Fix | Effect |
|---|---|---|---|
| `resolve_gold` re-normalised all 2,430 chunk texts **per question** | Evaluation dominated by `re.sub` | Memoise normalised chunk text keyed on list identity | Full eval 40 s → **9.7 s** |
| `exact_vector` fetched every row's full record to answer "which are visible?" | The ACL check cost more than the vector search | Cache the visible-id *set* per (version, ACL, filters); fetch only the rows actually returned | ~4.6× on the hot path |

Both are the same mistake in different costumes: **doing per-item work for a question whose
answer only changes on a write.**

---

## Invariants the tests enforce

`tests/` is not decoration. These are the properties a reviewer should not have to re-check.

| Invariant | Test |
|---|---|
| Reranking can never exceed the first-stage ceiling | `test_reranking_can_never_exceed_the_first_stage_ceiling` |
| ANN recall rises monotonically with `efSearch` and reaches ≥0.9 | `test_ann_recall_rises_monotonically_with_ef_search` |
| No persona ever receives a chunk outside its groups | `test_no_persona_ever_receives_a_chunk_outside_its_groups` |
| Post-filtering collapses `k`; pre-filtering does not | `test_post_filtering_collapses_k_and_pre_filtering_does_not` |
| A mixed-encoder index is detected | `test_mixed_version_index_is_detected` |
| RRF ignores score magnitude | `test_rrf_is_rank_based_and_ignores_score_magnitude` |
| Every gold anchor resolves under the shipped chunking | `test_every_gold_anchor_resolves_under_the_shipped_chunking` |
| Chunk ids are stable across rebuilds | `test_chunk_ids_are_stable_across_rebuilds` |
| Full-chain recall is never above evidence recall | `test_full_chain_is_never_above_evidence_recall` |
| κ punishes a judge that always passes | `test_cohens_kappa_punishes_a_judge_that_always_passes` |
| Every citation resolves to a packed chunk | `test_every_citation_resolves_to_a_packed_chunk` |
| Evidence never exceeds the token cap | `test_evidence_never_exceeds_the_token_cap` |
| The pipeline is deterministic | `test_the_pipeline_is_deterministic` |
