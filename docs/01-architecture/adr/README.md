# Architecture decision records

Short records of the decisions that were genuinely hard, each with **the alternative that
lost and why**. Written in the [MADR](https://adr.github.io/madr/) shape.

An ADR is not documentation of what the code does — the code does that. It is a record of
*what else we could have done*, so that when someone asks "why not just use X?" in six months,
the answer is a link rather than an argument.

| # | Decision | Status |
|---|---|---|
| [0001](0001-in-memory-sqlite.md) | Run the entire retrieval stack in in-memory SQLite | Accepted |
| [0002](0002-synthetic-corpus.md) | Generate the corpus from a fact graph rather than download MultiHop-RAG | Accepted |
| [0003](0003-lsa-default-encoder.md) | Ship LSA as the default encoder, not a neural model | Accepted |
| [0004](0004-stable-chunk-ids.md) | Derive chunk ids from doc_id + ordinal + content hash | Accepted |
| [0005](0005-learned-reranker.md) | Make the reranker a fitted model rather than hand-tuned weights | Accepted |
| [0006](0006-matplotlib-diagrams.md) | Draw notebook diagrams with matplotlib, not Mermaid | Accepted |
| [0007](0007-report-negative-results.md) | Report findings that contradict the deck rather than tuning them away | Accepted |
| [0008](0008-eval-gate-in-ci.md) | Block merges on metric regressions with a CI gate | Accepted |

## Writing a new one

Copy [`template.md`](template.md). Number it sequentially. Open it as a PR — an ADR that was
never argued with is not an ADR.
