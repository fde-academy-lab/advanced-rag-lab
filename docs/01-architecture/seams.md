# The ten seams

A seam is a place where a technique can be replaced without touching the harness, the metrics or
the eval set. They exist so that "does X help?" is answerable by measurement rather than by
argument — and so that the answer is attributable to X rather than to the eight other things
that had to change to accommodate it.

The property that makes a seam real: **swapping the implementation must not change what the
measurement means.** If it does, it is not a seam, it is a rewrite.

| # | Seam | Interface | Swap in | What must not change |
|---|---|---|---|---|
| ① | **Retriever** | `retrieve(query, n) -> list[Hit]` | Real ANN backend, ColBERT, SPLADE, a hosted service | `Hit` carries chunk id and score; the id resolves in the store |
| ② | **Index** | `store.InMemoryIndex` | Postgres + pgvector, OpenSearch, Bedrock KB | Chunk ids stay content-addressed; ACL and version columns survive |
| ③ | **Query transform** | `transform(query) -> list[str]` | HyDE, expansion, decomposition, spelling | Returns queries; anything downstream stays unchanged. Cost is per query and must be reported |
| ④ | **Chunker** | `chunk(doc) -> list[Chunk]` | Semantic, late chunking, layout-aware, LLM-authored | Chunk ids remain stable across a rebuild of unchanged content |
| ⑤ | **Embedder** | `encode_documents(texts) -> ndarray` | Titan, sentence-transformers, a hosted API | Dimension is fixed per index version; the tag is part of the index identity |
| ⑥ | **Fusion** | `fuse(lists, cfg) -> list[Hit]` | Learned weights, per-query α, rank-biased | Consumes ranked lists and emits one. Does not need the scores to be comparable |
| ⑦ | **Reranker** | `rerank(query, hits) -> list[Hit]` | Cross-encoder model, Bedrock rerank, LLM listwise | Reorders only. May not add or invent hits — that is a retrieval change wearing a rerank costume |
| ⑧ | **Packer** | `pack(hits, budget) -> Context` | Compression, summarisation, dedupe, ordering | Emits provenance per block so a citation resolves. Respects the hard token cap |
| ⑨ | **Generator** | `generate(context, query) -> Answer` | Claude, a local model, extractive | Returns citations against the provenance markers it was given |
| ⑩ | **Judge** | `judge(answer, gold) -> Verdict` | Model judge, human, rubric ensemble | Versioned. A judge change is a metric change and must be declared as one |

## Which seam does a technique belong to?

The commonest design error is putting a technique at the wrong seam, where it either cannot see
what it needs or silently changes what a metric means.

| Technique | Seam | Why not elsewhere |
|---|---|---|
| HyDE | ③ query transform | It rewrites the query. Putting it in the retriever hides its per-query generation cost inside a component nobody profiles |
| Contextual chunking | ④ chunker | It changes chunk text, so it changes chunk ids, so it forces a reindex. That is a chunker property |
| Query routing by class | ③ or ⑥ | If it picks a retriever, ⑥. If it rewrites, ③. If it does both it is two changes and must be measured as two |
| Multi-vector / ColBERT | ① retriever | It changes what a hit *is* — token-level rather than chunk-level. Anything downstream that assumes one vector per chunk must be checked |
| Compression | ⑧ packer | It runs after selection. Doing it before means you compressed things you then discarded |
| Self-consistency | ⑨ generator | Multiple samples of the same context. Not a retrieval change, and reporting it as one is how retrieval gets credit for generation gains |

## The rule that keeps seams honest

**A change at one seam is measured with every other seam held fixed.** An experiment that swaps
the chunker and the embedder together produces a number that belongs to neither.

The trap that catches people is subtler than it sounds. Fitting the embedder on *chunks* means
the chunking strategy changes the embedding space, so a comparison between chunking strategies
is measuring two things at once. That is why the embedder here is fitted on whole documents and
chunks are encoded into that fixed space:

```python
emb = embed.LsaEmbedder(dim=dim).fit([d.title + "\n" + d.body for d in bundle.documents])
vecs = emb.encode_documents([c.text for c in chunks])
```

## Adding a technique

1. Identify the seam. If it touches two, it is two changes.
2. Open an issue with a **falsifiable hypothesis** — which metric, which slice, which direction,
   roughly how much.
3. Implement behind the existing interface. Off by default if it costs latency or money.
4. Add a test. An extension that cannot be tested cannot be maintained.
5. Measure on dev, verify on frozen, report both with intervals.
6. If it did not work, submit it anyway with the mechanism. That is full credit here.

Twenty candidate techniques, each already written as a falsifiable hypothesis, are in
[09-research/extension-points.md](../09-research/extension-points.md).
