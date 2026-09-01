# Glossary

Terms as this codebase uses them. Where usage in the wider literature is looser, the entry says
which meaning is intended here.

| Term | Meaning here |
|---|---|
| **Abstention** | The system declining to answer. Measured with its own precision and recall against deliberately unanswerable questions, not folded into accuracy |
| **ACL pre-filter** | Restricting the candidate set to what a user may see *before* retrieval. Contrast post-filter, which retrieves then drops and so collapses k for restricted users |
| **Alias** | A named pointer to an index version (`live → v3`). Swapping it is atomic, which makes a rollback a pointer change rather than a rebuild |
| **ANN** | Approximate nearest neighbour. Trades exactness for speed; the trade is measured as recall against exact search, never assumed |
| **Boundary damage** | Fraction of gold evidence spans split across two chunks. The failure chunking uniquely causes, invisible in aggregate recall |
| **Chunk id** | `doc_id : ordinal : sha1(text)[:10]`. Content-addressed, so an unchanged chunk keeps its id across a rebuild and an upsert is genuinely an upsert |
| **Context precision** | Fraction of the packed context that is gold evidence. Falls as k rises — the counterweight to recall |
| **Cross-encoder** | A reranker scoring a (query, passage) pair jointly. Cannot be precomputed, so it runs only over a candidate list |
| **Evidence recall@k** | Per **piece**: fraction of gold evidence pieces that reached the window |
| **Frozen slice** | 15% of the eval set, touched once at the end. Tuning against it invalidates it for everyone |
| **Full-chain recall** | Per **question**: fraction of questions where *every* required piece reached the window. The one that predicts whether an answer is possible |
| **Fusion (RRF / weighted)** | Combining ranked lists. RRF fuses by rank and is scale-free; weighted fuses by score with a weight α. See finding 1 in [start-here.md](start-here.md) |
| **Gold evidence** | The chunks that genuinely contain a question's answer. True by construction here, since the corpus is generated from a fact graph |
| **Hop** | One step of a multi-part question. Hop-2 evidence resembles the *answer to hop 1*, not the query — which is why widening k does not find it |
| **Index version** | Immutable label for one build (`v3`), including the embedder and analyzer tags. A live index containing more than one is a defect that fails loudly |
| **Late interaction / MaxSim** | Scoring by max similarity between query and passage token vectors, retaining token detail a single vector discards |
| **Noise band** | The paired-bootstrap interval. A delta inside it is reported as inside it, never rounded into a win |
| **NSW / navigable small world** | A k-NN graph augmented with long-range links. Without them it is a lattice and greedy search cannot cross it |
| **Paired bootstrap** | Resampling per-query *differences* to get an interval. Paired because query difficulty swamps between-system variance |
| **Prompt cache** | Provider-side reuse of an identical prompt prefix. Requires **byte-identical** prefixes, so block ordering is a cost decision |
| **Provenance block** | The `[S#]` marker plus doc id, ordinal, date and score attached to each packed chunk, so a citation resolves |
| **Seam** | One of ten interfaces where a new technique plugs in without touching the harness. See [01-architecture/seams.md](../01-architecture/seams.md) |
| **Tombstone** | A deletion marker, so a purge is a filter rather than a rebuild |
| **Trace** | The recorded path of an agent run. Agents are scored on this, not only on the final answer |
| **Volatility ordering** | Arranging context blocks stable-first so the cacheable prefix is as long as possible |
