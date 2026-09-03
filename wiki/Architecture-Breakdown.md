# Architecture breakdown

**Takeaways**

1. Four planes, two SLAs: index-time work is paid once, query-time work is paid on every call.
   Most "make it faster" wins are moves from the second plane to the first.
2. Nothing downstream can recover a document the first stage never returned. Recall at the
   first stage bounds everything after it.
3. The seams are where the curriculum plugs in. Every extension in the research list names the
   seam it uses.

## The four planes

| Plane | What runs there | Paid | Lives in |
|---|---|---|---|
| Ingest | Chunking with stable ids, the analyzer, the encoder, the ANN graph build | Once per document | `raglab/corpus.py`, `raglab/index/` |
| Retrieve | BM25 over FTS5, dense over the encoder, fusion, the reranker | Every query | `raglab/retrieval/` |
| Compose | Packing with position-aware ordering, the permission filter | Every query | `raglab/context/` |
| Judge | The metrics, the judge, the release gate | Every pull request, and on a schedule | `raglab/metrics.py`, `scripts/run_eval.py` |

The full diagrams are in the
[README](https://github.com/fde-academy-lab/advanced-rag-lab#architecture) and the
[overview](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/overview.md).

## The query path, call by call

1. The question is analysed with the **same analyzer the index used**. ADR-0013 makes the
   analyzer part of the index identity because `tokenchars '_-'` changed identifier-slice
   recall from 0.34 to 0.81, and a mismatch between index-time and query-time analysis is a
   silent recall bug.
2. Two legs run: lexical (BM25 over SQLite FTS5) and dense (the LSA encoder by default,
   ADR-0003, swappable at the seam). Each returns ranked chunk ids.
3. Fusion combines them. The repository measured RRF, weighted sums and a learned per-class
   variant; the finding is that on this corpus the legs fail on the same questions, so fusion
   sits inside the dense leg's noise band. The measurement, and the retraction of the earlier
   claim, are in ADR-0015.
4. The reranker re-scores the top k. It is fitted here and verified against a no-reranker
   baseline, because an earlier version was uniformly slightly worse at every k, which is the
   signature of correct code with wrong features.
5. The packer orders chunks position-aware (ADR-0012) because the model reads the middle of the
   window worst. The permission filter runs **before** packing, not after (ADR-0011), because
   post-filtering leaks: a chunk the user may not see has already shaped what was retrieved.
6. Citations are emitted with chunk ids that are stable across re-indexing (ADR-0004), so a
   citation from last month still resolves.

## The index lifecycle

A state machine, not a script: building, ready, serving, draining, retired. The classic outage
it prevents is serving from an index that is half-built or half-torn-down. The ANN graph in
particular needs long-range links (ADR-0010): without them, recall against exact search at
2,430 chunks was 0.00 at the default `ef`, and 0.94 after.

## The seams, and what to change first

| Seam | Swap it for | Watch this number |
|---|---|---|
| Encoder | A sentence-transformer, an API embedding | evidence recall on the dense arm; cost per 1k queries |
| Fusion rule | Learned weights per query class (extension 3) | the paired interval against the dense leg alone |
| Reranker | A cross-encoder, distilled (extension 4) | nDCG at k=8, and latency |
| Packer | A different ordering, a compressor | full-chain recall against evidence recall |
| Judge | A calibrated real judge (extension 13) | agreement with the frozen human slice |

Start with the fusion rule. It is the seam where this repository was wrong, and the measurement
that catches a wrong claim already exists: `python scripts/run_eval.py --compare`.

## Where the ADRs are

[docs/01-architecture/adr](https://github.com/fde-academy-lab/advanced-rag-lab/tree/main/docs/01-architecture/adr):
fifteen decisions, each with a "what would change this" section. Read 0010, 0011, 0013 and
0015 first; they are the four with a number attached to the mistake.
