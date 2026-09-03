# Interview preparation

Eighteen questions AI-engineer, applied-ML and forward-deployed-engineer panels actually ask about retrieval, with
the answer a strong senior candidate gives — not a definition, but the *procedure* they walk,
the tradeoff they name unprompted, and the number they reach for.

**How to use this.** Read the "what the panel is testing" column first and answer out loud
before reading the model answer. The gap between your answer and the model one is your study
plan. Every question links to the notebook where you can *run* the thing you are describing,
because an answer you have executed sounds different from one you have read.

---

## How panels actually score

Before the questions, the sheet they are scoring against. Most candidates lose points on
**Tradeoffs** and **Numbers**, not on knowledge.

| Dimension | Signal | Anti-signal |
|---|---|---|
| **Problem framing** | Asks what is being measured, and on which set, before proposing anything | Starts naming tools and vendors in the first minute |
| **Debugging** | Bisects: isolates a stage, compares against a known-good reference | Lists plausible causes with no way to eliminate any of them |
| **Tradeoffs** | States the cost of their own recommendation, unprompted | Presents an option with only upsides |
| **Numbers** | Estimates cost and latency out loud, then sanity-checks the magnitude | "It depends on the workload", with no attempt at an estimate |
| **Scope control** | Sequences work; says what they would *not* do in the time available | Proposes a full rebuild for a four-week engagement |
| **Client posture** | Turns a demand into a quantified choice the client can own | Either agrees to everything, or refuses with no alternative |
| **Honesty** | "I don't know — here is how I'd find out in a day" | Confident numbers that fall apart on one follow-up |

---

# Part 1 — Scenario questions

These have no single right answer. You are scored on how you scope, what you measure first,
and which tradeoffs you name without being prompted.

---

## Q1 · "Your client's assistant answers correctly about 80% of the time. They want 95%. You have four weeks. What do you do in week one?"

**Testing:** whether you interrogate the number before acting on it; whether your instinct is
to build or to measure; whether you can tell a client that 95% may not be achievable.

**Answer.**

Before anything else I would ask three questions about the 80%, because the plan changes
completely depending on the answers. *Who measured it, on what set, and correct by whose
judgment?* If it came from a demo with twenty hand-picked questions, I do not have a baseline,
I have an anecdote — and week one is about replacing it.

Assuming there is something to work with, week one is:

**Days 1–2 — label 100 real failures.** Not synthetic ones. Pull them from production traffic
if there is any, from the client's own support queue if there is not. Hand-label each against
a fault-isolation procedure: was the gold evidence in the packed context at all? If not, was
it in the candidate pool? If it was in the context, is the answer entailed by it? That gives
four buckets — first-stage recall, ranking/packing, generation, and "the label or the question
is wrong."

**Day 3 — the distribution decides the plan.** If 70% of failures are retrieval misses, this
is a chunking and hybrid-retrieval engagement and I will spend three weeks there. If 70% are
grounding failures with correct evidence present, retrieval is fine and this is a prompt
contract, abstention and possibly a model-choice problem. Those are completely different
four-week plans, and picking the wrong one costs the whole engagement. I have seen teams spend
a month swapping embedding models to fix what turned out to be a packing bug.

**Days 4–5 — stand up a regression set.** Those 100 cases plus null questions the corpus
genuinely cannot answer. Freeze 15% of it and do not look at it again until the end. Without
the frozen slice, every number I report in week four is a number I tuned against.

**And I would reframe the target.** Some fraction of that 20% is unanswerable from the corpus
— the document does not exist, or it exists and is out of date. I would split the goal into
"answer correctly" and "refuse correctly", because refusing well is often the faster path to a
client-acceptable system, and it is nearly always the cheaper one. If after labelling I find
that 8% of queries are unanswerable, then 95% correct-or-correctly-refused is achievable and
95% correct is not, and that is a conversation to have in week one rather than week four.

**Red flags I would avoid:** jumping to "I'd try a better embedding model"; proposing three
changes at once so that no delta is attributable; accepting 95% as well-defined.

> **Run it:** [notebook 01 §1.6](../../notebooks/01_retrieval_and_evaluation_foundations.ipynb)
> executes exactly this tree over the full failure set and produces the distribution.

---

## Q2 · "A retrieval change raises average answer quality 6%, but one business unit reports the system got worse. Do you ship it?"

**Testing:** whether you treat an aggregate as evidence or as a summary that hides its own
counterexample; whether you will actually make a decision.

**Answer.**

Not yet — but I will decide this week, not "investigate further" indefinitely.

**Reproduce before believing.** Pull that unit's real queries, run both configurations, and
check whether the regression appears in the metrics at all. Perceived regressions are
sometimes a UI change, a change in what users started asking, or one loud incident. If it does
not reproduce, that is a conversation with the unit, not a rollback.

**If it reproduces, find the mechanism.** A unit-specific regression almost always has a
concrete cause. Two I have seen: their corpus is identifier-heavy and the change shifted
fusion weight toward the dense leg, so error codes stopped matching exactly; or their documents
are much shorter than average and a chunking change moved `avgdl`, which silently re-tuned
every BM25 score in the index. Both are findable in an afternoon by slicing the metrics by
tenant and looking at the queries that moved most.

**Then prefer a per-segment configuration over an all-or-nothing ship**, if the mechanism
supports it. Routing α by query class, or running that tenant on the previous fusion weights,
is usually cheaper than either losing the 6% or losing the stakeholder. It costs a second
configuration to maintain, and I would say that out loud rather than pretending it is free.

**And make the decision explicit and owned.** If I ship despite the regression, that unit's
owner hears it from me first, with the number, the mechanism, and a remediation date — not
from their users. If I hold the change, the rest of the business hears why they are not getting
the 6%.

The thing I would refuse to do is ship on the average and let the unit discover it. An
aggregate that improved while a named segment got worse is exactly the case my release gate
blocks by default, and overriding a gate is a decision that gets logged with a name on it.

> **Run it:** [notebook 06 §6.4](../../notebooks/06_evaluation_approaches.ipynb) executes the
> release-gate tree against a real candidate change, including the per-slice check.

---

## Q3 · "You upgraded the embedding model and Evidence Recall@10 fell from 0.86 to 0.71. Walk me through the diagnosis."

**Testing:** whether you check operational causes before model-quality causes; whether you
bisect rather than guess.

**Answer.**

A 15-point drop is almost never "the new model is worse." That is the seventh thing I check,
not the first. In order:

**1 · Mixed-version index.** Are some vectors still from the old model? One SQL query against
the model-version tag stored on each row. This is first because it is the cheapest check and
by far the most common cause — a partial re-ingest that failed halfway, or a backfill that ran
against a stale queue. Vectors from two encoders are not comparable and cosine similarity will
return perfectly well-formed numbers for the comparison, so nothing else in the system will
tell you.

**2 · Prefix asymmetry.** Many encoders require instruction prefixes — `query:` on one side,
`passage:` on the other. If the index was built with the passage prefix and the query path
lost the query prefix, recall drops and nothing errors. Check both sides read the same config.

**3 · Normalisation and metric.** Are the new vectors L2-normalised, and is the index still
configured for cosine rather than raw inner product or L2 distance? After normalisation cosine
and dot product give identical rankings; without it they do not, and a schema that "worked
before" quietly stops.

**4 · Dimension truncation.** Was the model output truncated to fit an existing column width?
This happens constantly when the schema is hard to change, and the recall cost is rarely
measured before it ships.

**5 · Context-length truncation.** Does the new encoder have a shorter input limit than the old
one? If so it is silently cutting the tail off your longest chunks — and the tail is often
where the answer is.

**6 · ANN parameters.** Was the graph rebuilt with the same `efConstruction` and `M`? Here is
the key move: **compare against flat exact search on a sample.** Flat search is ground truth.
If flat recall is fine and ANN recall is not, the loss is in the index, not the embedding, and
those have different fixes.

**7 · Only now: the model really is worse on this domain.** And even then I would slice the
misses by question type before concluding it, because "worse on average" and "worse on the
identifier queries that are 30% of our traffic" lead to different responses — the second one
is fixed by leaning harder on the lexical leg, not by reverting.

**Red flags:** starting at step 7; not knowing flat search gives you a ground-truth comparison;
having no plan to bisect.

> **Run it:** [notebook 04 §4.7](../../notebooks/04_retrieval_methods_and_reranking.ipynb)
> reproduces steps 1–6 on a live index, each with the measured recall drop.

---

## Q4 · "Legal requires that no answer can be influenced by a document the user is not allowed to read. Design for that."

**Testing:** whether you hear "influenced" and realise post-filtering does not satisfy it;
whether caches, logs and traces are part of your security boundary; whether you name the
recall cost up front rather than discovering it in UAT.

**Answer.**

The word that matters is *influenced*, and it rules out the design most people reach for.

**Post-filtering does not satisfy this.** If you retrieve top-k globally and then drop what the
user may not see, the restricted documents were candidates: they occupied ranks, they shifted
every permitted document beneath them, and they were in the reranker's batch. The answer was
influenced by them even though none appear in it. There are two observable failures too — `k`
collapses, so a narrowly-scoped user gets two chunks instead of eight and a worse answer with
no explanation; and the existence of restricted documents is inferable from result counts and
latency.

**So: pre-filter, always.** The ACL predicate goes *into* the query — into the SQL `WHERE` for
the lexical leg and into the ANN search for the dense leg — so restricted chunks are never
candidates and never contribute to a score, a rank, or a rerank batch.

**Name what it costs, up front.** A highly selective pre-filter degrades graph-based ANN
indexes: the traversal can only walk through nodes it is allowed to see, so when those are
sparse it dead-ends in a region far from the answer, at the same `efSearch`. Mitigate with
per-tenant namespaces or a partitioned index, and — this is the part teams skip — **measure
recall with the real filters on**, not without them. A benchmark that reports 0.99 recall
unfiltered tells you nothing about production.

**Close the side channels**, because the index is not the whole boundary:
- Prompt caches keyed per tenant. A shared prefix cache across tenants is a data-leak class of
  bug, not a performance issue.
- Traces store retrieved text, so the trace store inherits the corpus's compliance boundary —
  including its retention policy and its jurisdiction.
- Result counts and latency should not vary observably with what exists but is hidden.

**Revocation has an SLA.** If ACLs are denormalised onto chunks for speed, they need their own
change-capture stream, and I should be able to state the propagation lag in minutes. If legal
needs sub-minute revocation, denormalisation is off the table and we resolve per request,
which costs latency on every query — that is a tradeoff for them to own.

**And prove it.** An automated test that runs the same query as two personas and asserts
disjoint evidence sets, in the release gate, not as a one-off review. If someone later changes
the filter, the chunking, or the ACL denormalisation, the build fails rather than UAT.

> **Run it:** [notebook 03 §3.7](../../notebooks/03_rag_system_design.ipynb) measures the
> k-collapse and runs the two-persona isolation test;
> `tests/test_retrieval.py` has it wired into CI.

---

## Q5 · "Agentic search costs $0.90 on hard questions. Finance wants $0.15. What do you change, and what do you refuse to change?"

**Testing:** whether you can decompose a per-query cost from memory; whether you optimise the
distribution or the worst case; whether you push back with a quantified consequence.

**Answer.**

First, I would not accept the framing. $0.90 is a worst case, and Finance is almost certainly
looking at a blended bill.

**Get the distribution before redesigning anything.** If 8% of queries are hard and the rest
cost $0.02, the blended number is about $0.09 and we are already under target — the whole
exercise was about a number nobody had computed. I have seen that outcome more than once. If
30% are hard, we have a real problem and I want to know that before I start.

Assuming it is real, the levers in order, with what each costs:

**Escalate rather than loop by default.** Run single-shot, and enter the loop only when a
sufficiency check on the first pass fails. Most traffic never pays the multiplier. This alone
usually removes most of it, and it costs nothing in quality because the escalation trigger is
the same check the loop uses internally.

**Cache the stable prefix and the tool schemas.** Fifteen to thirty percent of input spend,
for a prompt-ordering change. Free.

**Carry a compacted evidence summary between turns** instead of the full text of everything
found so far. This turns the loop's token growth from roughly quadratic to roughly linear.
Small risk of dropping a detail — summarise, do not truncate.

**Cap turns**, typically four to eight. This bounds the tail, which is what actually hurts:
the p95 is where an agentic bill lives, not the median.

**Use a small model for decomposition and the sufficiency check**, and the large one only for
synthesis. Thirty to sixty percent of the loop's overhead. The cost is a router you must also
evaluate — a second system with its own failure modes.

**What I refuse:** removing the grounding and abstention checks, and removing the trace. Both
are cheap. Both are what stop a wrong answer becoming an incident, and the trace is the only
reason we can have this conversation with numbers at all.

**Then quantify the residual rather than agreeing to the target.** "I can reach $0.22 blended
without any quality loss. Getting to $0.15 means capping at two turns, which costs roughly X
points of full-chain recall on multi-hop questions — here is the measurement. That is a
business decision and I am happy to make either call, but I want it made with the number
visible."

**Red flags:** agreeing to $0.15 without a plan; "we'll use a cheaper model" as the whole
answer; naming no quality cost for any lever.

> **Run it:** [notebook 07 §7.6](../../notebooks/07_cost_and_token_optimization.ipynb) computes
> the blended cost under different hard-traffic shares;
> [notebook 08 §8.4](../../notebooks/08_agentic_search_and_evaluation.ipynb) measures the
> escalation policy against always-loop.

---

## Q6 · "Your LLM judge says quality went up. How would you know if the judge is wrong?"

**Testing:** whether you treat the evaluator as a component that can regress; whether you know
agreement statistics rather than accuracy; whether you can name specific biases and controls.

**Answer.**

I would treat the judge exactly like the retriever: a component with a version, a test set,
and a way to regress.

**A held-out human-labelled calibration set**, re-scored on every judge, rubric or model
change. Track Cohen's κ over time as a metric in its own right, not raw agreement — on a skewed
set a judge that always says "pass" scores 90% accuracy and has learned nothing. κ corrects for
chance and that difference is the whole point.

**Compare judge–human agreement against human–human agreement.** This is the step people skip
and it changes the interpretation completely. If two trained humans following the same rubric
only agree 70% of the time, a judge at 72% is doing fine and the *rubric* is the problem — it
is ambiguous, and fixing the judge will not help. You cannot know that without running the
human pass, and it costs about a day.

**Adversarial probes.** Feed known-bad answers that are long, fluent and confidently wrong. A
judge that passes them has verbosity bias, not quality signal. Same for position: in pairwise
comparison, swap A and B and require the verdict to hold. And self-preference — a judge tends
to favour output from its own model family, so I use a different family from the generator
where I can, and note it in the report where I cannot.

**Cross-check with an independent production signal.** If judged quality rises while citation
click-through, escalation rate and thumbs-down do not move at all, I believe the production
signal. A quality improvement that no user experiences is a measurement artefact until proven
otherwise.

**Version everything** — judge model, temperature, rubric text, few-shot examples. An
unexplained score jump with no system change is judge drift until proven otherwise, and
without versioning you cannot even tell whether something changed.

One more thing I would say unprompted: I use the judge for *relative* comparisons between two
versions of the system. Its absolute score is a dashboard number, not a client-facing quality
claim, and I would push back on anyone who wanted to put it in a contract.

**Red flags:** "we'd spot-check some outputs"; raw agreement on a skewed set; same model family
as generator and judge with no note about it.

> **Run it:** [notebook 06 §6.3](../../notebooks/06_evaluation_approaches.ipynb) computes κ, runs
> the verbosity and position probes, and demonstrates judge drift from a single rubric
> parameter.

---

# Part 2 — Technical depth

Shorter answers, but the panel is checking that you can connect the mechanism to a consequence.

---

## Q7 · When would you use BM25, dense retrieval, or a hybrid?

BM25 when the query carries identifiers, error codes, API names, SKUs, dates or exact
terminology — anything where the user typed the literal string that is in the document. It is
deterministic, explainable, cheap, easy to filter by metadata, and it benefits from domain
vocabulary an embedding model has never seen. Dense retrieval when the query wording differs
from the corpus wording: paraphrase, description instead of name, a user's register rather
than the author's.

Hybrid when both, which is most enterprise corpora. But I would add two things most answers
miss. First, **hybrid is not free, and it is not automatically better** — fusion pays only when
the legs fail on *different* queries. I have measured a corpus where they did not: 96.8% of the
questions the dense leg missed were missed by the lexical leg too, and fusion came out
indistinguishable from the better single leg (+0.0008, ci −0.0101 to +0.0109) while losing 0.075
nDCG against it. The diagnostic is the per-query failure overlap and it takes one line; almost
nobody runs it before choosing. Second, **the merge method is a real decision**: RRF is rank-based, needs
no tuning and survives score drift; weighted fusion keeps magnitude so a dominant exact match
can win outright, but it needs a labelled set to tune α and that α will not survive a corpus
refresh. Default to RRF, move to weighted only with a labelled set and a plan to re-tune on a
schedule.

## Q8 · Why does L2 normalisation change the relationship between cosine similarity and dot product?

Cosine is `q·d / (‖q‖‖d‖)`. After L2 normalisation both norms are 1, so the denominator
vanishes and cosine *is* the dot product. The rankings become identical.

The engineering consequence is the part that matters: an index configured for inner product
returns the same ranking as one configured for cosine **only if you normalise on write**. Mix
those up and every ranking silently changes — longer vectors win on inner product regardless of
direction. So: normalise on write, or configure the index for cosine, and know which one you
did. It is also why a similarity threshold is not portable: cosine is a relative score, not a
calibrated probability, and 0.82 on one corpus is not 0.82 on another.

## Q9 · How do early-interaction and late-interaction rerankers differ?

A cross-encoder (early interaction) concatenates query and passage and runs full attention over
both, so every query token can attend to every passage token. Highest quality. Nothing can be
precomputed because the representation depends on the pair, so cost is linear in N — reranking
100 candidates is 100 forward passes, per query, every query. Typically 50–300 ms batched at
N≈50, and *batched* is doing real work in that sentence: the difference between batching and
looping is often 90 ms versus 900 ms.

Late interaction (ColBERT-style) encodes query and passage tokens independently, keeps
token-level vectors, and scores with MaxSim at query time. Passage representations are
precomputable, so online latency drops to 10–40 ms. The cost is storage: 10–100× a single
vector per chunk. That multiplier is the part candidates forget, and it is the reason late
interaction is a strict-SLA choice rather than a default.

The default is a cross-encoder at N≈50. Everything else needs a reason.

## Q10 · How do you select chunk size and overlap for a mixed-format corpus?

I would not answer with a number. The size is a consequence of two things: the shape of the
document and the shape of the question.

If the documents carry reliable structure — headings, sections, cells, functions — split on
their own boundaries and carry the heading path into every chunk. That is free, and it makes
chunks attributable. If answers span several paragraphs of continuous argument, embed small and
return the parent. If queries are short, factoid and identifier-heavy, smaller chunks plus a
lexical index, because precision matters more than surrounding narrative.

Then measure. Run the strategies against one eval set and put three columns next to recall:
storage multiplier, index cost, and the number of gold spans that no chunk of that strategy
contains — because a chunking choice can make a label unscoreable, which looks like a recall
problem and is not.

And one thing I would raise unprompted: **re-chunking silently re-tunes BM25.** The
length-normalisation term is relative to the average document length of the corpus you just
rebuilt, so lexical scores change even though no code did. Re-measure after every chunking
change.

## Q11 · What trace data is required to reproduce an answer failure?

Retrieved chunk ids and their scores at each stage, the packed context with full provenance
(doc id, chunk ordinal, title, publication date, score), the assembled prompt, the model
response, per-stage latency, the index version and the encoder tag.

The test of whether you have enough: can you **diff two runs of the same query** and see which
chunks moved? The row that matters most in that diff is "retrieved then dropped, of which
gold" — it separates *we could not find it* from *we found it and threw it away*, and those
have completely different fixes. Almost nobody instruments the second one.

Without a trace you cannot reproduce a failure, cannot diff a change, and cannot turn a
production failure into a regression case — which means your eval set can never learn anything
your users found.

## Q12 · How would you design a RAG pipeline for documents that change daily?

Two paths, and mixing them is the classic outage.

The **incremental path** runs in minutes and is triggered by content. Change capture emits
document *ids*, not documents. A content-hash diff decides what actually needs re-chunking —
metadata-only edits skip embedding entirely. Chunk-level upsert on stable ids derived from
doc id + ordinal + content hash, so unchanged chunks keep their id and need no new vector.
Orphaned chunks are tombstoned rather than deleted, and stay filterable until the next
compaction so in-flight queries stay consistent.

The **rebuild path** runs in hours and is triggered by a *model* change — an embedding model,
a chunker, an analyzer — never by content. Build v(n+1) alongside v(n), both queryable, one
routed to. Shadow-evaluate the new one on the frozen eval slice and on replayed production
queries. Then an atomic alias swap, keeping the old index warm so rollback is a pointer change
rather than a rebuild.

The thing to say out loud: **never write new-model embeddings into an index that still holds
old-model vectors.** Nothing will error. Cosine similarity will return well-formed numbers for
vectors that mean nothing to each other. A model-version tag on every row plus a check in the
release gate is the entire defence.

## Q13 · Which metadata belongs in the index, and which belongs in the prompt?

In the index: anything you filter or scope on — source, publication date, tenant, ACL,
document type, language. A field you did not index is a filter you cannot apply, and the
failure looks like poor recall rather than like a schema bug.

In the prompt: anything the model must reason about — the title, the source, and especially
the publication date, because a temporal question is unanswerable if dates live only in the
index.

Dates go in **both**, and that is the part most candidates miss.

## Q14 · How would you tune top-k when answer quality improves but latency and cost rise?

I would ask what the latency and cost envelope is before answering, because k is a purchase
and I need to know the budget.

Then I would produce the curve: sweep k, and report marginal full-chain recall per thousand
additional tokens. That number falls off a cliff at some point, and the cliff is the operating
point — not a round number somebody liked. I would present it as a frontier with the chosen
point marked, so the client can see what a different choice would buy them.

Two things worth naming: context precision falls monotonically as k rises, so every extra slot
is more likely to hold a distractor than a gold chunk; and generation dominates the latency
budget anyway, so cutting retrieval quality to save 200 ms of a 2.5 s p95 is usually the wrong
trade.

## Q15 · How do you detect and mitigate "lost in the middle"?

Detect by measuring it on your own eval set rather than citing the paper: hold the evidence set
constant and force the gold chunk into position 1, the middle, and last. The spread is your
position sensitivity. It varies by model and by task, so somebody else's U-curve is a
hypothesis, not your number.

Mitigate in order of cost. Keep k small — fewer chunks in the middle at all, and it saves money
too. Order by reranker score then interleave, putting the two highest-scoring chunks at the
head and the tail. Restate the question briefly after the evidence, which puts the task in the
strong end position for about fifteen tokens.

## Q16 · When should a RAG system abstain instead of answering?

When the evidence does not entail an answer. That sounds obvious and the important part is
what it rules out: **it is an entailment judgment, not a similarity score.**

I have measured this. On an eval set with deliberately-constructed unanswerable questions, no
retrieval-side signal separated answerable from unanswerable — not the reranker score, not
IDF-weighted coverage, not sentence-level rare-term coverage, not a conjunctive corpus-presence
check. Best F1 was 0.38. The reason is visible once you look at the questions rather than the
scores: unanswerable questions often name real entities in the corpus's own vocabulary, while
real user questions paraphrase. The unanswerable ones are *lexically closer* to the corpus.

So abstention lives in the generation contract — one exact refusal token so it is parseable,
not "I'm not sure" — verified by a cheap sufficiency check as a separate call, and scored
against a null set that is part of your eval set from day one. In a regulated product you also
want an inline guardrail that blocks before the reply is sent, which is a different component
from the offline judge that teaches you what to fix.

## Q17 · How do offline evaluation and production monitoring complement each other?

Offline gates the release: deterministic, fast, runs on every change, and blocks a merge on a
regression. It cannot tell you about terminology your users started using last week.

Production has no labels but has reality: escalation rate, citation click-through, thumbs-down,
the questions people actually ask. Its job is to supply the failures that become next quarter's
regression cases.

The loop between them is the thing to name: **every production failure that gets a human
verdict becomes a new offline regression case.** Without that feed, your offline set slowly
becomes a mirror of your own retriever's blind spots, and it will keep passing while your users
suffer. I would also run the offline suite nightly on unchanged code, which is not redundant —
it is how you detect corpus drift, upstream model updates and judge drift, three things that
change your system without anyone committing anything.

## Q18 · What would block a retrieval-model release in your evaluation pipeline?

Two hard blocks and two warnings.

**Hard block** if any frozen-slice metric drops beyond its tolerance — the frozen slice is the
one thing tuning never saw, so a drop there is real. **Hard block** if a previously-passing
regression case now fails; those cases exist because someone was hurt by that failure once.

**Warn** if cost per query rises more than about 15%, and **warn** if any single tenant or
slice drops while the average holds — that second one is the case where someone experiences a
6% average improvement as a total outage of their use case.

Two things I would add. A delta inside the noise band is not a result: I measure run-to-run and
sampling variance once, write it down, and compare every delta against it. And the override
path matters as much as the gate — a human can ship past a block, and that decision is logged
with their name on it. A gate nobody can override gets disabled; a gate with a silent override
is theatre.

---

# Part 3 — Questions to ask *them*

Panels score you on the questions you ask, and these also tell you whether the role is real.

1. **"How do you currently know when retrieval quality regresses?"** — If the answer is "users
   tell us", you would be building the measurement layer, and that is worth knowing before you
   sign.
2. **"What is in your eval set, and who labelled it?"** — Reveals whether there is a
   ground-truth culture or a demo culture.
3. **"What is the cost of a wrong answer reaching a user in this product?"** — Determines
   whether you need an inline guardrail on day one or after the pilot. It is the single most
   architecture-shaping question you can ask.
4. **"How does a document change reach the index, and how long does it take?"** — Tells you
   whether the freshness path exists or whether somebody re-runs a notebook.
5. **"When did you last re-run your index-time enrichment?"** — A great question because most
   teams have never thought about it.
6. **"Who owns the decision when the average improves and one segment regresses?"** — Tells you
   whether there is an owner or a committee.

---

## A note on how to answer

The single biggest difference between a mid-level and a senior answer in these interviews is
not knowledge. It is that the senior candidate **states the cost of their own recommendation
before being asked**, and **reaches for a number where a mid-level candidate reaches for an
adjective**.

If you take one habit from this document: after every recommendation you make in an interview,
add one sentence beginning *"what this costs us is…"*. It is the fastest way to move from the
anti-signal column to the signal column on the sheet at the top of this page.
