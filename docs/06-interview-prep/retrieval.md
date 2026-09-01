# Retrieval

Twelve questions, in the form they are actually asked: a scenario with real constraints, the
interviewer's scoring sheet, and transcript fragments showing what each answer band sounds like
out loud — including where strong candidates stumble, because they do.

**On company names.** Where a company is named it describes the *style* of question that team
is publicly known for — Search-heavy shops probe index internals, deployment-heavy shops probe
what happens on day 400. Nobody has an insider question list, and any resource claiming to is
selling you something. Prepare for the shape, not the trivia.

**Scoring bands** used throughout: **✗ misses** · **○ passes a screen** · **● hires at mid** ·
**★ hires at senior**.

---

## R1 · The 90-second opener

> *"Walk me through what happens between a user typing a question and your system returning an
> answer. Assume I know nothing about your stack."*

Almost every retrieval loop opens with a variant. It is not a warm-up — it is a **structure
test**, and the interviewer has usually decided your band within four minutes.

### What they are scoring

| | Signal |
|---|---|
| ✗ | Names technologies instead of stages. "It goes into Pinecone and then we call GPT-4." |
| ○ | Gets the happy path in order: embed → search → rank → pack → generate. |
| ● | Names where each stage can fail, and volunteers the one place their design is weakest. |
| ★ | Splits index-time from query-time unprompted, and attaches a budget to each stage. |

### What ★ sounds like

> "Two timelines, and I'd separate them because they have completely different cost models.
>
> Index-time, paid once per document: ingest, chunk, embed, write to the index. This can be
> slow — it is a batch job — but it is where most quality is decided, and it is the part you
> cannot fix at query time.
>
> Query-time, paid on every request, and I'd budget it. Say 800ms p95 end to end. Retrieval
> candidates ~40ms, rerank the top 100 ~120ms, pack the context, then generation is 400–600ms
> and dominates everything. So if someone asks me to make it faster, I already know the answer
> is 'fewer output tokens or a smaller model', not 'a faster vector database' — the retrieval
> is 20% of the budget.
>
> The weakest part of that as described is the chunk boundary. If a fact spans a boundary,
> neither chunk scores well and no amount of retrieval quality downstream recovers it. That
> failure is invisible in aggregate recall and it is what I would instrument first."

The move that earns the band is the last paragraph. Volunteering your own weakest link reads as
someone who has operated a system rather than drawn one.

---

## R2 · The saturation question

> *"Here is a scoring function: `score = Σ tf × idf`. What's wrong with it?"*

**Style:** Search teams, Elastic, anywhere with an inverted index in production.

They want two failures, and most candidates give one.

**Failure one — no saturation.** A document containing "latency" forty times scores forty
times a document containing it once. Relevance saturates; raw `tf` does not. BM25's
`tf/(tf+k₁)` is a hyperbola derived from the 2-Poisson elite/background model, and `k₁`
controls where the knee sits.

**Failure two — no length normalisation.** A 5,000-word page accumulates term frequency simply
by being long. BM25's `b` divides by `|d|/avgdl`.

### The follow-up that does the sorting

> *"You set b = 0.75 and recall got worse. Why might that be?"*

**● at mid:**
> "Probably the length distribution. If documents are all similar lengths, normalisation is
> just noise. I'd check the distribution and lower b."

**★ at senior:**
> "Two candidates and I'd tell them apart with one plot.
>
> If length is **bimodal** — say short error stubs and long reference pages — a single b cannot
> serve both. Full normalisation penalises the long pages, and the stubs already win on density,
> so you have made the good documents worse and the easy documents no better. I'd plot document
> length, and if it is bimodal the answer isn't a different b, it's **stop pretending it is one
> corpus**: separate fields with separate normalisation, BM25F-style.
>
> The other candidate is that length correlates with quality here. On documentation it often
> does — long pages are the maintained ones. Then b is penalising exactly the signal you want,
> and the fix is b near zero plus a quality prior, not a tuned b.
>
> Either way I'd want the answer sliced by query class before touching the parameter. A global
> b tuned on a global average is wrong on every individual class."

---

## R3 · The one nobody prepares for

> *"Your retrieval works. A PM tells you users say search is broken. Recall@10 is 0.89 and
> stable. Where do you look?"*

**Style:** Palantir, deployment-engineering roles, anywhere the job is a customer's system.

This tests whether you believe your metrics. The trap is defending the number.

### Scoring

| | Signal |
|---|---|
| ✗ | "The metric says it's fine, so it's a UX or expectations problem." |
| ○ | Suggests looking at logs. |
| ● | Proposes slicing: by query class, by user segment, by recency. |
| ★ | Questions whether the eval set resembles production traffic at all, and says how to check. |

### What ★ sounds like

> "I'd assume the users are right and my number is measuring the wrong thing. Four places, in
> order of how often they're the answer.
>
> **The eval set has drifted from production.** This is the most common one by a distance. It
> was built eighteen months ago from questions somebody imagined. Real traffic is now 40%
> navigational — 'take me to the refund policy' — and my eval set is all factoid questions.
> Recall@10 of 0.89 on a distribution nobody sends. I'd sample 200 real queries from logs,
> label them, and measure on those. That number is the real one.
>
> **The average is hiding a slice.** 0.89 overall with 0.95 on the 80% easy head and 0.65 on
> the tail that generates the complaints. Slice by query class, length, whether it names an
> entity, and by whether the user reformulated — a reformulation is a labelled failure the user
> gave you for free.
>
> **Recall isn't the user's metric.** They experience rank and precision. The right document at
> rank 9 is a failure to a human and a success to Recall@10.
>
> **It's not retrieval.** The generator may be receiving the right context and answering badly,
> or hedging. I'd check answer quality conditioned on correct retrieval — if that's poor, no
> retrieval work helps and I've just saved a quarter.
>
> Fastest first step is twenty complaint queries run by hand. Twenty is usually enough to see
> the pattern, and it costs an afternoon rather than a sprint."

**Interviewer's note:** the last line matters more than it looks. Proposing a cheap diagnostic
before an expensive one is a seniority signal in itself.

---

## R4 · Chunking, asked as a trap

> *"What chunk size do you use?"*

The question has no answer and the interviewer knows it. They are checking whether you'll
produce a number.

**✗:** "512 tokens with 50 overlap." Confident, arbitrary, unfalsifiable.

**★:**
> "I don't have a default, because the right size depends on something I'd need to look at
> first: whether the corpus has structure worth respecting.
>
> On documents with real headings — API docs, policy, anything authored with sections — I chunk
> structurally, on the headings, and accept variable sizes. The heading is a human-authored
> statement about what belongs together, and it beats any window I'd pick.
>
> On unstructured prose I'd start with recursive splitting around 400–600 tokens and treat that
> as a hypothesis, not a setting.
>
> The thing I'd actually measure is not recall by chunk size — it's **boundary damage**: the
> fraction of gold evidence spans that get split across two chunks. That is the failure mode
> chunking uniquely causes, and it is invisible in aggregate recall because a split fact
> degrades both chunks slightly rather than failing one loudly.
>
> One methodology trap I'd flag: if you fit your embedder on chunks, the chunking strategy
> changes the embedding space, and then you can't compare strategies — you're measuring two
> things and attributing to one. Fit on documents, encode chunks into that space."

That last paragraph is a genuine differentiator. It is the kind of detail that only shows up
after you have run the comparison and had it come out wrong.

---

## R5 · Reranking, and the honest failure

> *"You add a cross-encoder reranker and recall goes down. Debug it out loud."*

**Style:** Cohere, Anthropic, teams that have shipped a reranker.

Deliberately adversarial, because it happens constantly and the textbook says it shouldn't.

### What ★ sounds like — including the stumble

> "First reaction is that I've wired it backwards — ascending instead of descending sort. That's
> the boring cause and I'd rule it out in two minutes with a spot check on one query.
>
> Assuming it's not that… hmm. Let me think about what a reranker actually does. It reorders
> the top N. It cannot add anything, so if recall@k dropped, it's demoting true positives that
> the first stage had correctly placed inside k.
>
> So the question is what the reranker knows that the first stage doesn't — and the failure case
> is when the answer is **nothing**. If my reranker's features are lexical overlap and phrase
> matching, and my first stage is a *fused* list where the dense leg contributed the ranking
> signal, then the reranker is applying a worse BM25 on top of a list that already used more
> information. It is throwing away the dense signal.
>
> That's exactly what happened when we built ours — evidence recall at k=5 went 0.773 → 0.630,
> worse at *every* k, which is the signature. Not a wiring bug, because a wiring bug is usually
> catastrophic rather than uniformly-slightly-worse.
>
> The fix was making the features genuinely pairwise — MaxSim between query and passage token
> embeddings, and document-level cosine — so the reranker sees the semantic signal too. Then
> fitting the weights by logistic regression on a dev slice instead of hand-tuning them; the
> hand-tuned grid search never beat the baseline. That got us +8 points of evidence recall, and
> it held on the frozen slice, which is the part I'd insist on before believing it."

**Why the stumble helps.** "Hmm, let me think about what a reranker actually does" is a real
person reasoning. Candidates who deliver a polished answer to a debugging question read as
having memorised it, which is the opposite of what the question tests.

---

## R6 · ANN, past the buzzwords

> *"Explain HNSW to someone who knows k-NN but not ANN."*

Then, always: *"Why doesn't a plain k-NN graph work?"* — see
[mathematics.md M4](mathematics.md#m4--why-does-a-k-nn-graph-fail-as-an-ann-index-and-what-fixes-it)
for the full derivation.

The compressed version worth having ready:

> "Greedy search over a pure k-NN graph gets stuck, because every edge is short and the graph's
> diameter is O(n^(1/d)) — you'd need to traverse enormous numbers of hops to cross the space,
> and greedy stops at the first local minimum long before that.
>
> Kleinberg's result is that adding random long-range links makes it navigable in O(log²n), and
> only within a band — too few and you're back to a lattice, too many and greedy has no gradient.
> HNSW organises that into layers instead of randomising it: sparse upper layers for coarse
> routing, dense base layer for the final descent.
>
> The thing I'd flag operationally: this failure is **latent in corpus size**. We had a k-NN
> graph that worked fine at 230 vectors and gave literally 0.00 recall at 2,430. Every test
> passed, because every test ran on a small fixture. Any ANN test on a small corpus is testing
> a regime where the bug cannot appear."

---

## R7 · The multi-tenant question

> *"Every document has an ACL. Users see different subsets. How do you retrieve?"*

**Style:** Palantir, Glean, enterprise search, anything B2B.

### The two designs and why one is wrong

**Post-filter** — retrieve top k, then drop what the user can't see. Simple. Two failures:

1. **k-collapse.** Ask for 10, get 10, filter to 2. The user's result count now depends on their
   permissions, and the more restricted a user is the emptier their search gets. Over-fetching
   to compensate is unbounded: a user permitted 0.1% of the corpus needs k=10,000.
2. **Score leak.** If you show relevance scores, or anything derived from corpus statistics, a
   restricted user can infer the existence and approximate content of documents they cannot
   read. This is a real exfiltration channel and it is what a security reviewer will ask about.

**Pre-filter** — constrain the candidate set to what the user may see, then retrieve. Correct,
and harder: your ANN index must support filtered search, and a naive implementation degrades to
a scan when the filter is selective.

### The ★ answer's extra move

> "Pre-filter, with a caveat about how it interacts with the ANN structure. A filtered graph
> search can disconnect the graph for a restricted user — the long-range links may all point to
> documents they can't see — so recall collapses for exactly the users with the tightest
> permissions, which is the worst possible distribution of failure.
>
> Practically, I'd bucket by ACL group where the group count is small and maintain per-group
> index partitions; where it's large, filtered HNSW with a fallback to exact search once the
> filter selectivity crosses a threshold you measure rather than guess.
>
> And I'd want the permission check evaluated at **query time against the source of truth**, not
> baked into the index at ingest. Permissions change more often than documents do, and an index
> that caches them is an index that serves a revoked user their old access until the next
> reindex."

---

## R8–R12 · Rapid rounds

Shorter, but the follow-up is where the marks are.

| # | Question | The ★ move |
|---|---|---|
| **R8** | *"Query expansion — worth it?"* | Distinguish expansion from rewriting. Expansion helps recall on short queries and hurts precision on specific ones, so it should be **conditional on query length and specificity**, not global. Mention HyDE and that its cost is one generation per query, which usually kills it on latency before quality is even discussed |
| **R9** | *"Your index is 400GB and won't fit in RAM."* | Quantise first — product quantisation buys 8–16× at a measurable recall cost you can plot. Then check whether you need all of it hot: most corpora have a long cold tail that can live on disk behind a smaller hot index. Sharding is the last resort because it adds a fan-out and a merge to every query |
| **R10** | *"How do you keep the index fresh?"* | Content-hash the source, diff, upsert only what changed — which requires stable chunk ids, which requires content-addressed ids (`doc_id:ordinal:hash`), or your "update" is a delete-then-insert that orphans rows. Blue/green index versions with an atomic alias swap so a bad rebuild is one pointer away from being reverted, and tombstones for deletes so a purge is not a full rebuild |
| **R11** | *"When would you not use RAG?"* | When the corpus fits in the context window and stays there — then retrieval adds a failure mode for nothing. When the task needs the whole document rather than passages, like summarising a contract. When freshness requirements are sub-second. And when the real problem is that the answer isn't written down anywhere, which no retrieval architecture fixes |
| **R12** | *"Estimate cost per query."* | Four token categories, not one: input, output, cache-write, cache-read. Then the arithmetic out loud, and the observation that prompt caching requires **byte-identical** prefixes — so the ordering of your context blocks is a cost decision, and putting anything volatile early destroys the cache for everything after it |

---

## Practising this

Record yourself. The gap between candidates at this level is rarely knowledge — it is that one
of them takes ninety seconds to say what the other says in twenty, and runs out of time before
the follow-up that carries the marks.

Three habits that move a band:

1. **State the shape before the detail.** "Two timelines" / "two failures" / "four places, in
   order of likelihood." The interviewer can then follow you, and knows you have a plan.
2. **Volunteer the weakness.** Every design has one. Naming yours reads as operating experience;
   waiting to be caught reads as inexperience.
3. **Propose the cheap diagnostic first.** "Twenty queries by hand" before "instrument the
   pipeline" is a seniority signal on its own.

Every answer above corresponds to a cell in the notebooks where the number is computed rather
than asserted. Run it, change a parameter, watch the metric move — then you have the sentence
nobody else in the loop has: *"I ran that, and here's where it stops behaving the way the
formula suggests."*
