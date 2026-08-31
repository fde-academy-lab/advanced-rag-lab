# Extension points

Twenty techniques you can add, each with a falsifiable hypothesis, the seam it plugs into, what
it costs, and how you would know it worked. **Open items are labelled `type: extension` and
`good first issue` in the tracker** — claim one by commenting on its issue.

The [seams](../01-architecture/overview.md#the-seams--where-to-plug-things-in) are numbered ①–⑩. If your idea
does not fit exactly one, it is probably two ideas.

> **Every entry here is written as a hypothesis, not a feature.** "Improves quality" is not a
> hypothesis. "Full-chain recall on the comparison slice rises ≥5 points at unchanged k,
> because both hops become retrievable from a single decomposed query" is.

---

## Tier 1 — high value, well understood, S/M effort

### 1. HyDE — hypothetical document embeddings
**Seam ③** · effort M · *Gao et al., 2022*

Generate a hypothetical answer to the query, embed *that* instead of the query, and search.
The generated answer lives in document-space rather than question-space, which closes part of
the asymmetry a bi-encoder has to bridge.

- **Hypothesis:** dense-leg evidence recall on the descriptor/paraphrase slice rises ≥8 points;
  no change on the identifier slice.
- **Costs:** one generation per query on the critical path (~300–800 ms, real money). Fails
  loudly when the model hallucinates a plausible answer in the wrong domain.
- **Measure:** slice by query class — this should help exactly one class and it is a red flag
  if it helps all of them equally.
- **Offline path:** template-generated pseudo-answers from the fact graph, clearly labelled.

### 2. Query decomposition that actually pays
**Seam ⑩** · effort M

Notebook 09 finds routed decomposition adds candidates that never win a slot — because at
N=100 the pool already contained them. Make it pay by *narrowing* N and decomposing, so each
sub-question gets its own small pool.

- **Hypothesis:** at N=30 per sub-question (90 total), full-chain recall beats N=100 single-query
  at equal total candidates.
- **Costs:** more retrieval calls; a router you must evaluate separately.
- **Measure:** hold total candidates constant. That is the only fair comparison.

### 3. Reciprocal rank fusion with learned per-class weights
**Seam ④** · effort S · builds on EX-13

Notebook 04 shows a single global α is a compromise. Learn α per query class from the dev set.

- **Hypothesis:** routed α beats the best global α by ≥3 points evidence recall, and the gain
  holds on frozen.
- **Costs:** a classifier that is a second system with its own precision/recall.
- **Watch for:** the router's errors concentrating on exactly the queries that needed help.

### 4. Cross-encoder distillation
**Seam ⑤** · effort M

Use the (expensive) reranker to label pairs, then train a cheaper model — or better features
for the existing one — on those labels.

- **Hypothesis:** matches cross-encoder nDCG within 2 points at <20% of the latency.
- **Costs:** an offline labelling run; a model that inherits the teacher's biases.

### 5. Semantic answer caching
**Seam ⑧** · effort S

Cache full answers keyed on a query embedding, serve on a near-match.

- **Hypothesis:** ≥25% hit rate on a realistic traffic mix at a similarity threshold that keeps
  false-hit rate under 1%.
- **Costs:** *"varies wildly"* in the deck's cost table, and for a reason — a near-miss cache hit
  serves a confidently wrong answer. **This is the one extension that can make quality worse
  while every dashboard improves.**
- **Measure:** you must measure the false-hit rate, not just the hit rate. Most implementations
  do not.

### 6. Query rewriting with conversation state
**Seam ③** · effort M

Resolve pronouns and ellipsis against conversation history before retrieving.

- **Hypothesis:** on a multi-turn variant of the eval set, evidence recall on follow-up turns
  rises ≥15 points.
- **Costs:** requires building the multi-turn eval set first — which is most of the work, and
  the more valuable half.

---

## Tier 2 — structural changes worth a cohort project

### 7. GraphRAG / knowledge-graph retrieval
**Seams ①③** · effort L · *the LinkedIn case study in notebook 03*

Parse documents into entities and relations; retrieve over sub-graphs so the unit returned is a
coherent case rather than a fragment.

- **Hypothesis:** on the incident+KB question class, full-chain recall rises ≥10 points because
  both halves of a case arrive together.
- **Costs:** a parser per source system, a graph store to operate, a schema to maintain as
  templates change. Worth it for highly structured, high-volume corpora and rarely otherwise.
- **Start from:** notebook 03's crude case-level pairing, which already moves the number.

### 8. RAPTOR — recursive summarisation trees
**Seam ①** · effort L · *Sarthi et al., 2024*

Cluster chunks, summarise clusters, recurse. Retrieve at whichever level of abstraction the
query needs.

- **Hypothesis:** on "what changed across the quarter" style questions, evidence recall rises
  where flat chunking cannot help at all.
- **Costs:** index-time model calls that must be re-paid on every corpus refresh; a tree to
  keep fresh.
- **Watch for:** summaries that are retrievable but not *citable* — provenance gets harder.

### 9. ColBERT / true late interaction
**Seam ⑤** · effort L

The toolkit has MaxSim over LSA term vectors. Do it properly with a trained late-interaction
model.

- **Hypothesis:** within 3 points of cross-encoder quality at ~⅕ the latency.
- **Costs:** 10–100× storage for token-level vectors. Measure the storage, not just the latency.

### 10. Self-RAG / corrective RAG
**Seams ⑧⑩** · effort L · *Asai et al., 2023; Yan et al., 2024*

The model critiques its own retrieval and decides to re-retrieve, use the evidence, or abstain.

- **Hypothesis:** **abstention F1 rises above 0.38** — the open problem in this repo (EX-18).
- **Costs:** extra model calls per query; a critique step that is itself a component that can
  regress.
- **This is the highest-value open item in the repo.** See EX-18.

### 11. Multi-vector document representation
**Seam ②** · effort M

Represent a document by several vectors (per section, per claim) rather than one per chunk.

- **Hypothesis:** on documents where the answer is a small part of a long text, evidence recall
  rises without shrinking chunks.
- **Costs:** index size; a merge rule for per-document scores.

### 12. Learned sparse retrieval (SPLADE-style)
**Seam ③** · effort L

Term-weighted sparse vectors learned by a model — lexical matching with learned expansion.

- **Hypothesis:** closes most of the gap between BM25 and dense on the paraphrase slice while
  keeping identifier performance.
- **Costs:** a model at index time; an inverted index that no longer holds the original terms,
  which makes debugging harder.

---

## Tier 3 — evaluation and operations

### 13. A real judge, calibrated
**Seam ⑨** · effort M

Replace `HeuristicJudge` with `BedrockJudge` and run the full calibration loop against human
labels (EX-19).

- **Hypothesis:** κ against humans ≥0.6, and judge–human agreement ≥ human–human agreement.
- **Costs:** real money per evaluation run; a judge that can drift.

### 14. Position sensitivity, measured on a real model
**Seam ⑦** · effort S · EX-17

- **Hypothesis:** the U-curve exists and the spread is ≥5 points on this eval set.
- **Costs:** one API run. Cheap, and almost nobody does it.

### 15. Multi-turn conversational eval set
**Seam ⑨** · effort L

- **Hypothesis:** single-turn metrics overstate multi-turn performance by ≥10 points.
- **Costs:** building the set is the work. It is also the deliverable.

### 16. Per-tenant metric dashboards
**Seam ⑨** · effort S

Slice every metric by tenant and alert when one drops while the average holds.

- **Hypothesis:** catches at least one regression that the global average hides.
- **Costs:** almost nothing. This is the highest value-per-hour item on the page.

### 17. Adversarial / robustness eval set
**Seam ⑨** · effort M

Typos, wrong entity names, leading questions, prompt injection in retrieved documents.

- **Hypothesis:** answer correctness degrades gracefully on typos but the **injection cases
  reveal a real vulnerability** — retrieved content is untrusted input and the current prompt
  contract does not treat it that way.
- **Costs:** none. This one is nearly free and has a security dimension worth a section of its
  own.

---

## Tier 4 — infrastructure

### 18. Real ANN backend
**Seam ③** · effort M

Swap the in-process NSW graph for FAISS, hnswlib, or pgvector behind the same `Hit` interface.

- **Hypothesis:** at 10× corpus size, recall/latency beats the in-process graph; below that it
  does not justify the operational cost.
- **Costs:** a dependency, and a second thing to keep in sync.

### 19. Streaming generation and time-to-first-token
**Seam ⑧** · effort M

- **Hypothesis:** TTFT drops below 400 ms while total latency is unchanged — and the perceived
  budget changes completely.
- **Costs:** the guardrail has to become streaming-aware, or it stops being able to block.

### 20. Incremental index with a real CDC source
**Seams ①** · effort L

Wire the freshness path to an actual change stream rather than a simulated one.

- **Hypothesis:** p95 index lag under five minutes at a realistic edit rate.
- **Costs:** a queue, a dead-letter path, and an on-call rotation.

---

## Concepts deliberately *not* implemented, and why

Being explicit about what is out of scope is part of a good design document.

| Concept | Why it is absent |
|---|---|
| A production vector database | The lesson is that the choice is an ops and residency decision, not a recall one — `docs` covers it; running one teaches infrastructure, not retrieval |
| Fine-tuning an embedding model | Needs GPU and hours; the *decision* (when it is worth it) is covered in the embedding-model tree |
| Multimodal retrieval | A whole curriculum of its own; the seams would support it |
| Reinforcement learning from feedback | The feedback loop is modelled (production failures → eval set); the RL is not the teaching point |
| A UI | Every failure this curriculum cares about is invisible in a UI |

---

## Claiming one

1. Find or open the issue (`type: extension`).
2. Comment with **your hypothesis and how you will measure it** before you write code. Faculty
   will push back on the hypothesis, which is the most useful ten minutes of the whole exercise.
3. Post the design in
   [Discussions → Design Reviews](../../discussions/categories/design-reviews) if it touches
   more than one seam.
4. Branch, build, measure, PR. The eval gate will post your scorecard.

**A rejected extension with a clean negative result is a full-credit contribution here**, and
it is worth more on your CV than a feature that shipped without evidence.
