"""The content `setup_github.py` provisions: labels, milestones, issues, discussions.

Kept in one place so it can be reviewed as *content* rather than read out of API calls.

A note on the issues below. The ones marked `closed` are **real defects found while building
this repository**, with their real fixes and the commits that carried them. They are seeded so
that a student arriving at an empty tracker can see what a well-run issue looks like end to
end — symptom, evidence, root cause, fix, verification — rather than being told.

Discussions marked `[worked example]` were written by faculty to model the shape of a good
question and a good answer. They say so in a footer. Nothing here impersonates a student.
"""
from __future__ import annotations

SEED_FOOTER = (
    "\n\n---\n<sub>*Seeded by faculty as a worked example of the format. "
    "Start your own thread rather than replying here unless you have something to add.*</sub>"
)

# ───────────────────────────────────────────────────────────────────── labels ──
LABELS = [
    # type
    ("type: bug", "d73a4a", "Something behaves incorrectly"),
    ("type: exercise", "0e8a16", "A student exercise submission"),
    ("type: extension", "5319e7", "A new technique plugged into a seam"),
    ("type: reading", "1d76db", "A reading assignment for a cohort"),
    ("type: docs", "0075ca", "Documentation only"),
    ("type: chore", "cfd3d7", "CI, dependencies, tooling"),
    ("type: discussion-followup", "bfd4f2", "Came out of a Discussions thread"),
    # area
    ("area: retrieval", "e99695", "Retrieval, fusion, indexes, encoders"),
    ("area: evaluation", "c2e0c6", "Metrics, judge, release gate"),
    ("area: agent", "fbca04", "Agentic search loop"),
    ("area: cost", "f9d0c4", "Tokens, caching, unit economics"),
    ("area: notebooks", "d4c5f9", "Teaching notebooks"),
    ("area: toolkit", "c5def5", "The raglab package"),
    ("area: docs", "bfdadc", "docs/ and top-level markdown"),
    ("area: ci", "ededed", "Workflows and automation"),
    ("area: bedrock", "ff9900", "AWS Bedrock integration"),
    # status
    ("status: triage", "fef2c0", "Not yet assessed"),
    ("status: needs-review", "fbca04", "Waiting on a reviewer"),
    ("status: blocked", "b60205", "Blocked — names who and by when"),
    ("status: stale", "795548", "No activity for 45 days"),
    # meta
    ("good first issue", "7057ff", "A good place to start"),
    ("help wanted", "008672", "Extra attention is welcome"),
    ("cohort", "006b75", "Cohort-facing work"),
    ("needs: eval-numbers", "e4664f", "Touches raglab — must ship with a measurement"),
    ("dependencies", "0366d6", "Dependency updates"),
    ("negative-result", "8a63d2", "A change that was measured and rejected — full credit"),
]

# ─────────────────────────────────────────────────────────────────── milestones ──
MILESTONES = [
    ("P0 · Harness", "Runner, metrics, results table, noise band. Before any retrieval code.",
     "closed"),
    ("P1 · Baseline", "Fixed chunking, single dense retriever, k=5, no reranker. Recorded.",
     "closed"),
    ("P2 · Retrieval", "Lexical leg, fusion, ANN, reranking. One change at a time.", "closed"),
    ("P3 · Context", "Token budget, packing, provenance, position.", "closed"),
    ("P4 · Evaluation", "Layered metrics, judge calibration, the release gate.", "closed"),
    ("P5 · Cost", "Token categories, prompt caching, unit economics.", "closed"),
    ("P6 · Agentic", "The loop, stop conditions, trace scoring.", "closed"),
    ("P7 · Hardening", "Open items: abstention, robustness, a real encoder.", "open"),
]

# ─────────────────────────────────────────────────────────────────────── issues ──
# Closed issues are real defects from the build, with their real fixes.
ISSUES = [
    {
        "title": "[bug] ERR_CONN_RESET returns the wrong chunks — FTS5 tokenizer splits identifiers",
        "labels": ["type: bug", "area: retrieval", "needs: eval-numbers"],
        "milestone": "P2 · Retrieval",
        "state": "closed",
        "body": """### Symptom

Identifier questions score *worse* on the lexical leg than on the dense leg, which is exactly
backwards. `ERR_CONN_RESET` should be the single easiest thing BM25 ever has to find.

```
Evidence Recall@8 by query class
                    lexical  dense
identifier            0.778  0.856   ← inverted
pure lexical gap      1.000  0.200
```

### Root cause

The default FTS5 tokenizer is `unicode61`, which treats `_` as a separator. `ERR_CONN_RESET`
is indexed as three tokens — `err`, `conn`, `reset` — and all three appear in **every**
incident report in the corpus. So the query matches everything and ranks nothing.

Reproduced in isolation:

```python
db.execute("CREATE VIRTUAL TABLE t USING fts5(x)")            # default tokenizer
db.execute('SELECT count(*) FROM t WHERE t MATCH ?', ('"ERR_CONN_RESET"',))   # → 0
```

Nothing errors. The query runs, returns results, and they are the wrong results.

### Fix

`tokenize = "unicode61 remove_diacritics 2 tokenchars '_-'"` on the FTS5 table.

### Verification

`tests/test_retrieval.py::test_identifiers_survive_the_analyzer` asserts that an identifier
query returns only chunks that literally contain it. Notebook 04 §4.3 measures the before/after
so a student sees the failure rather than being told about it.

### Why this issue is seeded

This is the cheapest silent recall bug in enterprise search and it has no symptom other than
"retrieval feels bad". Your analyzer decides what is searchable at all, and nothing downstream
will tell you.""",
    },
    {
        "title": "[bug] ANN recall collapses as the corpus grows — the k-NN graph is not navigable",
        "labels": ["type: bug", "area: retrieval", "needs: eval-numbers"],
        "milestone": "P2 · Retrieval",
        "state": "closed",
        "body": """### Symptom

After scaling the corpus from 1,186 to 2,430 chunks, ANN recall against flat search fell off a
cliff and did not recover with a larger visit budget:

```
ef=8    recall@20=0.00
ef=64   recall@20=0.00     ← should be near 1.0
ef=512  recall@20=0.55
```

### Root cause

`_matrix()` built a **pure k-NN graph** — every node connected to its 16 nearest neighbours and
nothing else. That is a lattice of tight neighbourhoods with no shortcuts between them. Greedy
best-first search walks into the nearest cluster and cannot leave it, so it never reaches the
region containing the answer. Every edge in the graph is correct; the graph as a whole is
unusable.

This is precisely the "navigable" half of *navigable small world* — the part HNSW's upper
layers provide and a flat k-NN graph does not.

### Fix

Four random long-range links per node (Kleinberg's construction), concatenated onto the k-NN
edges:

```python
rng = np.random.RandomState(17)
longr = rng.randint(0, n, size=(n, min(4, max(1, n - 1))))
entry["graph"] = np.concatenate([near, longr], axis=1)
```

### After

```
ef=8    recall@20=0.10
ef=32   recall@20=0.85
ef=128  recall@20=0.95
ef=512  recall@20=1.00
```

A proper recall/efSearch curve, which is what notebook 04 §4.6 needs in order to teach that
**ANN recall is a tunable, not a property.**

### Verification

`test_ann_recall_rises_monotonically_with_ef_search` asserts monotonicity and a ≥0.9 ceiling.""",
    },
    {
        "title": "[bug] Evaluation is 4× slower than it should be — resolve_gold re-normalises the whole corpus per question",
        "labels": ["type: bug", "area: evaluation", "type: chore"],
        "milestone": "P4 · Evaluation",
        "state": "closed",
        "body": """### Symptom

A full evaluation of 243 questions took ~40 s, making the notebook sweeps painful and pushing
notebook 04 past ten minutes.

### Root cause

Profiling put half the time in one place:

```
   ncalls  tottime  cumtime  function
       25    0.001    2.116  metrics.py:30(resolve_gold)
    60898    1.598    1.598  {method 'sub' of 're.Pattern' objects}
```

`resolve_gold` normalised **all 2,430 chunk texts for every question** — O(questions × chunks)
regex substitutions to answer a question whose answer only changes when the chunk list does.

A second instance of the same mistake: `exact_vector` called `_rows_for(all_ids, …)`, fetching
every row's full record to answer "which of these are visible to this persona?" — the ACL check
cost more than the vector search it was supporting.

### Fix

1. Memoise normalised chunk text, keyed on list identity, with a small LRU.
2. Cache the *visible-id set* per `(index_version, acl_groups, filters)`, cleared on every
   write; fetch full rows only for the hits actually returned.

### After

Full evaluation 40 s → **9.7 s**, with byte-identical metrics
(`evidence_recall 0.7645`, `full_chain_recall 0.4686` before and after).

### The transferable part

Both are the same mistake in different costumes: **doing per-item work for a question whose
answer only changes on a write.** Worth remembering the shape.""",
    },
    {
        "title": "[bug] The reranker makes retrieval worse at every k",
        "labels": ["type: bug", "area: retrieval", "needs: eval-numbers", "negative-result"],
        "milestone": "P2 · Retrieval",
        "state": "closed",
        "body": """### Symptom

The stage-2 reranker consistently *reduced* recall relative to the fusion it was reranking:

```
k=5 rerank=none    ER=0.773  FCR=0.455
k=5 rerank=cross   ER=0.630  FCR=0.386   ← worse
k=8 rerank=none    ER=0.849  FCR=0.614
k=8 rerank=cross   ER=0.752  FCR=0.523   ← worse
```

Shipping this would have taught the opposite of the lesson: the deck's own matrix names a
cross-encoder as the default stage-2 choice and the highest quality per unit of engineering
effort.

### Investigation

1. **First hypothesis — bad weights.** Grid-searched all four hand-set coefficients. The best
   grid point still lost to no-reranking.
2. **Second hypothesis — length bias.** Added BM25-style length normalisation to the coverage
   feature. Helped, still lost.
3. **Root cause.** The scorer used *lexical features only*, so reranking a hybrid candidate
   list threw away the dense signal entirely. It was a worse BM25 applied on top of a
   well-fused list.

### Fix

Two changes:

- Add genuinely pair-wise **semantic** features — `maxsim` (each query token against the best
  matching passage token) and `doc_cosine`. `maxsim` is the one a bi-encoder structurally
  cannot produce, because it compresses the passage before it has seen the query.
- Stop hand-tuning. **Fit** the weights by logistic regression on the dev slice, with class
  weighting because gold pairs are rare.

### After

```
weighted α=0.2               ER=0.6832  FCR=0.4155
weighted α=0.2 + learned     ER=0.7645  FCR=0.4686
paired bootstrap, evidence recall: +0.0813 [+0.0475, +0.1163] → real
frozen slice: FCR 0.419 → 0.548
```

### What this changed about the curriculum

It made the toolkit more honest about something the deck only implies: **a reranker is a
model.** It has training data, it can overfit, and its gain has to survive on a slice it never
saw. That is now notebook 04 §4.10 rather than an assumption. See
[ADR-0005](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0005-learned-reranker.md).""",
    },
    {
        "title": "[bug] Every chunking strategy scores the same — documents are too short for the comparison to mean anything",
        "labels": ["type: bug", "area: notebooks", "area: toolkit"],
        "milestone": "P1 · Baseline",
        "state": "closed",
        "body": """### Symptom

The seven-strategy chunking bake-off in notebook 03 produced near-identical results, and
`fixed` chunking came out on top:

```
Strategy        Chunks  Evidence recall
fixed              484            0.873
recursive          484            0.873   ← identical
structural       2,430            0.807
```

### Root cause

The generated corpus averaged **71 words per document**. At a 512-token chunk size, `fixed` and
`recursive` both produce exactly one chunk per document — so "fixed chunking" was really
"document-level retrieval", which wins by containing everything.

A corpus of 70-word documents cannot teach chunking, because every strategy degenerates to the
same thing.

### Fix

Added realistic surrounding prose to every generated document: background, market context,
"what is not known", operating notes, analyst commentary and boilerplate — all deliberately
**on-topic and undecisive**, so they are in-document distractors a retriever has to rank past.

Average document length 71 → **299 words**. The strategies now genuinely differ:

```
fixed              969 chunks   median 300 tok
recursive        1,351 chunks   median 173 tok
structural       2,430 chunks   median 138 tok
semantic         7,430 chunks   median  31 tok
parent_document  1,258 chunks   median 490 tok
```

### Note

This is the second time the corpus had to be scaled. The first was because N=100 candidates
over 230 chunks is a full scan wearing a costume — the "first stage" was not narrowing
anything. Both are recorded in [ADR-0002](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0002-synthetic-corpus.md).""",
    },
    {
        "title": "[bug] decision_tree() crashes when a case falls through to the default branch",
        "labels": ["type: bug", "area: toolkit", "area: notebooks"],
        "milestone": "P4 · Evaluation",
        "state": "closed",
        "body": """### Symptom

```
TypeError: '>=' not supported between instances of 'NoneType' and 'int'
  in viz.decision_tree, line 418
```

Triggered by the release-gate tree in notebook 06 whenever a candidate change passes every
check and reaches the default outcome ("ship behind a canary").

### Root cause

```python
onpath = path is not None and (path.get("exit_index", 10**9) >= i)
```

`decide()` returns `exit_index=None` when nothing exits — a *meaningful* value, not a missing
key. `dict.get` returns `None` rather than the default, and `None >= 0` raises.

The bug only fires on the happy path, which is why it survived until a notebook exercised a
clean release.

### Fix

```python
exit_at = 10**9
if path is not None and path.get("exit_index") is not None:
    exit_at = path["exit_index"]
```

### The transferable part

`dict.get(k, default)` does not do what you want when `None` is a legitimate stored value. If
`None` means something in your data model, test for it explicitly.""",
    },
    {
        "title": "[bug] The abstention PR curve contradicts the notebook's own conclusion",
        "labels": ["type: bug", "area: evaluation", "area: notebooks"],
        "milestone": "P4 · Evaluation",
        "state": "closed",
        "body": """### Symptom

Notebook 05 argues — correctly, and at length — that no retrieval-score threshold separates
answerable from unanswerable questions. The chart directly above that argument showed precision
reaching **1.0** and F1 peaking at **0.69**, which looks like a perfectly usable threshold.

The prose and the figure disagreed. One of them was wrong.

### Root cause

To keep the notebook under two minutes I had changed the θ sweep to run on a stratified
subsample: all 36 null questions plus 72 answerable ones. That moved the null base rate from
**15% to 33%**, and abstention precision is directly sensitive to the base rate. The subsample
flattered the threshold.

The prose was right. The figure was measuring a different population.

### Fix

Two changes:

1. **Run on the full eval set with the real base rate.** Abstention by threshold is a post-hoc
   decision on one number per question, so there is no reason to re-run the pipeline once per
   candidate θ — run it once, collect the top score per question, sweep θ in NumPy. Faster
   *and* correct.
2. Make the callout quote the measured curve rather than asserting a fixed conclusion, so it
   cannot drift out of sync again.

### After

Best F1 **0.38**, at the cost of refusing a large number of answerable questions. Which is what
the prose said.

### Why this is seeded as a worked example

This is the most instructive bug in the repository. A performance optimisation silently changed
the population being measured, and the resulting number was not *wrong* — it was correct about
a different question. If the notebook had not also contained an argument in prose, nothing
would have caught it.

**Base rate is part of the metric definition.** Write it down next to the number.""",
    },
    {
        "title": "[bug] Exact search poisons the ANN cache — graph never gets built",
        "labels": ["type: bug", "area: retrieval"],
        "milestone": "P2 · Retrieval",
        "state": "closed",
        "body": """### Symptom

```
AttributeError: 'InMemoryIndex' object has no attribute 'last_ann_visits'
```

…but only when `exact_vector()` had been called first in the same session.

### Root cause

`_matrix(index_version, build_graph=...)` cached its result keyed on `index_version` alone.
`exact_vector` calls it with `build_graph=False`, caching an entry with `graph=None`.
`ann_vector` then read that cached entry, found no graph, and silently fell back to exact
search — so it never set the visit counter, and, worse, **it was not doing approximate search
at all** while reporting that it was.

### Fix

Cache the matrix and the graph separately; build the graph lazily on first ANN use.

```python
entry = {"ids": ids, "mat": mat, "graph": None, "M": M}   # graph built on demand
```

### The transferable part

A cache keyed on less than the full set of inputs will eventually serve you the wrong answer.
The production version of this bug is an index that silently serves the wrong structure after a
partial rebuild — same shape, much worse consequences.""",
    },
    {
        "title": "[ext] Add HyDE — hypothetical document embeddings",
        "labels": ["type: extension", "area: retrieval", "good first issue", "help wanted",
                   "needs: eval-numbers"],
        "milestone": "P7 · Hardening",
        "state": "open",
        "body": """### Technique

HyDE (Gao et al., 2022). Generate a hypothetical answer to the query, embed *that* instead of
the query, and search. The generated answer lives in document-space rather than question-space,
which closes part of the asymmetry a bi-encoder has to bridge.

### Falsifiable hypothesis

Dense-leg evidence recall on the **descriptor/paraphrase slice** rises ≥8 points, with **no
change on the identifier slice**.

That second half matters. If it helps every slice equally, something else is going on and the
result should be distrusted.

### Seam

③ first-stage retriever — wrap `DenseRetriever.search` behind a config flag.

### What it costs

- One generation per query, on the critical path: ~300–800 ms and real money
- Fails loudly when the model hallucinates a plausible answer in the wrong domain
- Needs an offline fallback (template-generated pseudo-answers from the fact graph), clearly
  labelled as a stand-in

### Acceptance criteria

- [ ] Off by default; enabled via `RetrievalConfig`
- [ ] Offline path works with no network
- [ ] Evidence recall **sliced by query class**, with 95% intervals
- [ ] Added latency measured, not estimated
- [ ] A note in `docs/09-research/extension-points.md` recording the result — including if it is negative

Good first extension: one seam, a clear hypothesis, and a well-understood technique.""",
    },
    {
        "title": "[ext] Solve abstention — no retrieval-score threshold works",
        "labels": ["type: extension", "area: evaluation", "help wanted", "needs: eval-numbers"],
        "milestone": "P7 · Hardening",
        "state": "open",
        "body": """### The problem

This is the largest open item in the repository, and the one most worth doing.

Notebook 05 §5.6 establishes that **no retrieval-side signal separates answerable from
unanswerable questions** on this eval set. Four were tried:

| Signal | Best F1 |
|---|---|
| Top reranker score | 0.38 |
| Corpus-IDF coverage of the packed context | ~0.28 |
| Sentence-level rare-term coverage | ~0.27 |
| Conjunctive corpus-presence check | ~0.28 |

All near chance. The mechanism is visible once you look at the questions rather than the
scores: **null questions name real entities in the corpus's own vocabulary** ("Which
organization acquired Halcyon Robotics?") while answerable questions paraphrase and use
descriptors. So the unanswerable questions are *lexically closer* to the corpus than the
answerable ones. A similarity threshold is measuring the wrong thing.

Current state: abstention recall **0.097**. 28 of 36 null questions are answered anyway.

### Directions worth trying

1. A cheap **sufficiency call** with a strict schema — the deck's prescription
2. **Answer-type checking** — does the top evidence contain an entity of the type the question
   asks for, in the right relation?
3. A **trained classifier** over pair features, like the reranker
4. An **NLI-style entailment** check between question+evidence and a candidate answer
5. A **two-stage contract** where the model must name the supporting span before asserting

### Acceptance criteria

- [ ] Abstention precision/recall on the **full null set with the real base rate**
      (see the base-rate bug above — this trap is easy to fall into)
- [ ] Cost per query of the approach
- [ ] **Over-refusal on answerable questions** — the failure nobody measures
- [ ] An honest statement of what it still gets wrong

### Why it is hard, and worth it

Abstention is an entailment question, and entailment needs a reader. Whoever solves this will
have to bring generation into a decision that everything else in the repo keeps on the
retrieval side — and will learn more from it than from any other item on the board.

Linked exercise: **EX-18**.""",
    },
    {
        "title": "[ext] Route the fusion weight α by query class",
        "labels": ["type: extension", "area: retrieval", "help wanted", "needs: eval-numbers"],
        "milestone": "P7 · Hardening",
        "state": "open",
        "body": """### Context

Notebook 04 §4.9 measures that a single global α is a compromise, because the legs fail in
different places:

```
Evidence recall by query class
                         BM25   dense   weighted α=0.2
descriptor (paraphrase)  0.438  0.377   0.456
identifier               0.778  0.889   0.800
named entity             0.843  0.665   0.762
pure lexical gap         0.500  0.000   0.300
```

The deck says α can be routed — higher for paraphrase queries, lower for code and IDs. Nobody
has measured whether routing actually beats the best global value here.

### Hypothesis

Routed α beats the best global α by ≥3 points evidence recall, **and the gain holds on the
frozen slice**.

### The catch, and the actual lesson

The router is a **second system**. It has its own precision and recall, and its errors will
concentrate on exactly the queries that needed help — a query the router misclassifies is
usually a query that is hard for a reason. Report the router's own metrics alongside the
retrieval gain, and be prepared for the honest conclusion that it is not worth its own
maintenance.

Text-only features. **No gold labels** — using `question_type` would be leakage and would
flatter the result.

### Acceptance criteria

- [ ] Router precision/recall reported as its own metric
- [ ] Routed vs best-global, with intervals, on dev and frozen
- [ ] A statement on whether the second system earns its maintenance

Linked exercise: **EX-13**.""",
    },
    {
        "title": "[reading] Week 1 — Retrieval and evaluation foundations",
        "labels": ["type: reading", "cohort"],
        "milestone": "P1 · Baseline",
        "state": "open",
        "body": """### Required reading

1. **[Lewis et al., RAG (2020)](https://arxiv.org/abs/2005.11401)** — *what to look for:* the
   RAG-Sequence / RAG-Token distinction, and how little of the modern stack this paper
   describes. Most of the engineering arrived later.
2. **[Anthropic, Contextual Retrieval (2024)](https://www.anthropic.com/news/contextual-retrieval)**
   — *what to look for:* where the fix lives. It is at index time, and prompt caching is what
   made it affordable. Note that they kept BM25.

### Optional

- [Tang & Yang, MultiHop-RAG (2024)](https://arxiv.org/abs/2401.15391) — skim the record schema

### Questions — answer as comments before the Day 1 session

1. The contextual-retrieval post reports a 49% reduction in failed retrievals. **What is a
   "failed retrieval" in their measurement, and what would you need to know before quoting that
   number to a client?**
2. Both readings implicitly assume you can tell a retrieval failure from a generation failure.
   **How would you actually do that on a system you did not build?**
3. Anthropic kept BM25 alongside dense retrieval. **On what kind of corpus would dropping BM25
   be safe, and how would you check before doing it?**

### Notebook

Run `00_start_here.ipynb` and `01_retrieval_and_evaluation_foundations.ipynb` before the
session. You do not need to understand every cell — you need to have seen the fault-isolation
tree produce a verdict.

Due: **before the Day 1 session.**""",
    },
    {
        "title": "[docs] The README's three contradicting findings need a 'how to re-test this' section",
        "labels": ["type: docs", "area: docs", "good first issue"],
        "milestone": "P7 · Hardening",
        "state": "open",
        "body": """### The gap

The README's "Three results that contradict the expected answer" table names the mechanism and
the condition under which the expected result would return — but does not tell the reader
**how to re-test it themselves** on their own corpus.

That is the whole point of reporting negative results. A finding a reader cannot re-test is
just an assertion with better manners.

### What to add

For each of the three findings, a short recipe:

- The exact cells or script to run
- What to change (corpus, encoder, base rate)
- What number would falsify the finding

### Why this is a good first issue

It requires reading the notebooks carefully enough to know where each finding is measured, and
produces something genuinely useful. No new code.""",
    },
    {
        "title": "[ext] Adversarial and robustness eval set — including prompt injection through retrieved content",
        "labels": ["type: extension", "area: evaluation", "help wanted"],
        "milestone": "P7 · Hardening",
        "state": "open",
        "body": """### Technique

A fourth eval slice: typos, wrong entity names, leading questions, and — the important one —
**prompt injection embedded in retrieved documents**.

### Hypothesis

Answer correctness degrades gracefully on typos and leading questions, but the injection cases
reveal a real vulnerability: **retrieved content is untrusted input, and the current prompt
contract does not treat it as such.**

### Why this matters more than it looks

Every other failure in this repository is a quality problem. This one is a security problem,
and it is the one that turns into an incident. A document in a corpus can contain
"ignore previous instructions and…", and in most RAG systems that text arrives in the model's
context with the same status as the system prompt.

### Acceptance criteria

- [ ] ≥20 adversarial questions across the four categories
- [ ] Baseline behaviour measured on each category
- [ ] At least one injection that **succeeds** against the current contract, documented
- [ ] A proposed mitigation (delimiter discipline, instruction hierarchy, a guard) with its
      cost, measured
- [ ] `SECURITY.md` updated to reflect what changed

Linked: `docs/09-research/extension-points.md` #17.""",
    },
    {
        "title": "[chore] Add a real ANN backend behind the same Hit interface",
        "labels": ["type: chore", "area: retrieval", "help wanted"],
        "milestone": "P7 · Hardening",
        "state": "open",
        "body": """### Context

The in-process NSW graph is real and teaches the recall/`efSearch` tradeoff honestly, but it is
ours to maintain and it does not scale.

### Hypothesis

At 10× the current corpus size, FAISS or hnswlib beats the in-process graph on recall at equal
latency. **Below that size it does not justify the operational cost** — and demonstrating that
threshold is more useful than the swap itself.

### Seam

③, behind the existing `Hit` interface. `store.InMemoryIndex.ann_vector` keeps its signature.

### Acceptance criteria

- [ ] Optional dependency; the offline path is unchanged when it is absent
- [ ] Recall/latency curve for both, at two corpus sizes
- [ ] The crossover point, stated
- [ ] `docs/01-architecture/overview.md` local→AWS table updated

Linked: `docs/09-research/extension-points.md` #18.""",
    },
]


# ────────────────────────────────────────────────────── discussion categories ──
# (name, emoji, description, format)  format ∈ {DISCUSSION, ANNOUNCEMENT, POLL}
# GitHub creates "General", "Ideas", "Q&A", "Show and tell", "Announcements", "Polls"
# by default on enable; we add the teaching-specific ones and reuse the rest.
CATEGORIES = [
    ("Design Reviews", "🏗",
     "Post a design BEFORE you build it. The point is to get the objection now rather than in "
     "week three. Include your constraints and what your own design costs.", "DISCUSSION"),
    ("Reading Club", "📚",
     "Discussion of assigned papers. The assignment itself is an issue; the argument about it "
     "lives here.", "DISCUSSION"),
    ("Interview Prep", "🎯",
     "Practise an answer and get it critiqued. Nothing under NDA — use the scenarios in "
     "docs/06-interview-prep/ or invent your own.", "ANSWER"),
    ("Exercises & Submissions", "🧪",
     "Every exercise runs here. Approach before code, submission with an interval, one peer "
     "review owed before one is asked for. See docs/10-community/exercise-workflow.md.",
     "ANSWER"),
    ("Math & Theory", "🧮",
     "Derivations, proofs and the question behind the formula. If you can state it in LaTeX, "
     "state it in LaTeX.", "ANSWER"),
    ("Debugging Clinic", "🐞",
     "Bring a failure you cannot explain. Symptom first, then what you have already ruled out. "
     "Threads here are long on purpose.", "ANSWER"),
    # The simulator's own category. Named without dots so the slug is predictably
    # `lab-simulator`, which is what .github/DISCUSSION_TEMPLATE/lab-simulator.yml is keyed to.
    ("LAB Simulator", "🧪",
     "Post a unit, a bot grades it. It runs the same `python -m labsim check` you would run "
     "locally, on a clean checkout, and replies with the named checks that failed. Comment "
     "/hint for the next hint, /solution once you clear, /status for the pathway. No clone "
     "needed — or open the repo in Codespaces and use the editor.", "ANSWER"),
    ("Weekly Standup & Retro", "🗓",
     "What moved, what is blocked, what we got wrong. One thread per week, posted by the "
     "maintainers.", "ANNOUNCEMENT"),
]

# ───────────────────────────────────────────────────────────────── discussions ──
DISCUSSIONS = [
    # ── Announcements ────────────────────────────────────────────────────────
    {
        "category": "Announcements",
        "title": "Welcome — start here, and how this place works",
        "body": """Welcome to the Advanced RAG playground for cohorts **C1** and **C2**.

## First 30 minutes

1. Clone, `make setup`, `make lab`
2. Open `notebooks/00_start_here.ipynb`, press **Run All**
3. When it finishes, read the *honesty inventory* at the bottom — the table of what is real and
   what is a stand-in. Everything else in the curriculum depends on you having read it.

## Where things go

| You want to… | Go to |
|---|---|
| Ask why something behaves the way it does | **Q&A** — not Issues |
| Get an architecture challenged before building it | **Design Reviews** |
| Show what you built, including what did not work | **Show & Tell** |
| Submit an exercise | An **exercise issue** + a branch |
| Report a genuine defect with a reproduction | A **bug issue** |
| Practise an interview answer | **Interview Prep** |

## Three house rules

**1 · Evidence beats adjectives.** "Recall seems low" is not answerable. "Evidence Recall@8 is
0.61 on the temporal slice and 0.79 elsewhere" is.

**2 · Every claimed improvement carries an interval.** `metrics.paired_bootstrap` gives you one.
A delta inside the noise band is reported as inside the noise band — not rounded into a win.
This is enforced by the PR template and by CI.

**3 · Negative results are full credit.** "I tried HyDE and it did not clear the noise band,
here is the mechanism I think explains that" is one of the most useful things you can post.
The repository itself reports three findings that contradict the source material — see the
README.

## A thing worth knowing on day one

There is a `good first issue` label with real, scoped work behind it, and a `docs/03-exercises/catalogue.md`
with 22 exercises graded by difficulty. You are not expected to invent your own starting point.

Ask anything. The only bad question here is the one asked in a DM, because it helps one person
instead of every future cohort.""",
    },
    {
        "category": "Announcements",
        "title": "The findings in this repo that contradict the deck — and the one of them that was wrong",
        "body": """Four measurements in these notebooks contradict what the source deck's decision matrices
predict. Each one could have been engineered away. We kept all four, and this post explains
why, because it is the single most important thing about how this material is taught.

One of them used to say the opposite of what it says now. That correction is at the bottom and
it is the part worth reading twice.

## The findings

**1 · Fusion does not separate from its better single leg.** Dense alone scores 0.7733 evidence
recall; equal-weight RRF scores 0.7742. That gap is +0.0008 with a 95% interval of
(−0.0101, +0.0109) — not a small difference, *not a difference*. On nDCG the **unfused** dense
leg wins outright, by 0.075. The mechanism: fusion turns two signals into a better one only when
the legs fail on *different* queries, and here they fail together. Shipping the fused system
means a second index and a fusion rule in the query hot path, bought with a number whose
interval contains zero.

**2 · Comparison-question starvation does not reproduce.** The matrix predicts one entity
dominating top-k while the other is starved. Our corpus is balanced by construction — every
company has the same number of quarters — so the prevalence ratio between two compared entities
is ≈1 and nothing starves.

**3 · No retrieval-score threshold separates answerable from unanswerable** (best F1 0.38). Four
signals were tried; all sit near chance. Null questions name real entities in the corpus's own
vocabulary while real questions paraphrase — so the unanswerable ones are *lexically closer* to
the corpus.

**4 · No retrieval configuration moves answer correctness.** Evidence recall spans 0.7118 →
0.7790 across five fusion configurations — a real 9.4% relative improvement — while
`answer_correct` stays inside the noise band on *every* pairwise comparison, and the numerically
best answers come from the numerically worst retriever. The system is generation-limited, not
retrieval-limited. It was visible the whole time in the 0.4686 → 0.4115 gap between full-chain
recall and answer correctness, and nobody joined it up.

## Why we did not fix them

Because a decision matrix **names a mechanism you should go and test**, and the test is allowed
to come back negative.

A curriculum where every matrix row confirms teaches something corrosive: that these tables are
facts to recite, and that when your measurement disagrees with the slide you should change your
measurement. That is exactly backwards, and it is the habit that produces a team that spends a
sprint fixing starvation it does not have.

Each finding in the README carries a "when the expected result returns" column, because the
matrix is not *wrong* — it names a real mechanism under conditions our corpus does not meet.

## What this means for you

When you run an exercise and your result contradicts what you expected, **that is a finding,
not a mistake.** Post it in Show & Tell. Then work out the mechanism, and state the condition
under which the expected result would return.

That sequence — measure, contradict, explain, bound — is most of what separates a senior
engineer from a competent one in this field.

## The one that was wrong

Finding 1 used to read: **"Equal-weight RRF does not beat BM25 alone here; weighted fusion at
α=0.2 does."** With a mechanism: RRF gives both legs the same vote, our dense leg is a
fifty-year-old method and therefore the weak one, and fusing strong with weak at equal weight
moves you toward the weak one.

Re-measured, none of that holds. RRF *beats* BM25 by +0.0624, ci (+0.0407, +0.0857). The dense
leg is the **stronger** of the two, not the weaker — +0.0616 evidence recall and +0.2416 nDCG
over BM25 — because these questions are paraphrase and inference over prose, where term overlap
has almost nothing to score. And weighted α=0.2 is not the argmax; α=0.5 measures better.

It was wrong for months and quoted in about twenty places, including material some of you have
already learned from and quoted in interviews. That is a real cost and we are not going to
soften it.

**The part worth your attention is why nothing caught it.** The eval gate compares one
configuration against its own history and never against alternatives — so a claim about which
*configuration* is better sat outside everything the CI was capable of checking. The gate was
working perfectly and could not have noticed. Two fixes went in: `python scripts/run_eval.py
--compare`, which produces the whole table with intervals in one command, and a retraction ADR
that records what was claimed, what was measured, and this paragraph.

If you take one habit from this repository, take that one. When you publish a comparison, ask
what would have to break for you to find out you were wrong — and if the answer is "somebody
re-runs it by hand", you have not published a finding, you have published a belief.

Full write-up: [ADR-0007](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0007-report-negative-results.md)
and the retraction, [ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md).
The measurement note with every interval is
[here](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/fusion-rules.md).""",
    },

    # ── Q&A ──────────────────────────────────────────────────────────────────
    {
        "category": "Q&A",
        "title": "Recall@N climbs and full-chain recall does not. Where does the difference go?",
        "body": """### The question in one line

I widened `n_candidates` from 100 to 400 and `Recall@N` improved, but `full_chain_recall` barely
moved. Why?

### What I have already tried

- Confirmed the extra candidates are real — the pool genuinely contains more gold chunks
- Checked it is not a caching artefact by restarting the kernel
- Sliced by `question_type`: the flatness is worst on `comparison` and `temporal`

### The numbers

```
N=100   Recall@N 0.938   full-chain 0.469
N=400   Recall@N 0.974   full-chain 0.481
```

### Where

Notebook 01 §1.3""",
        "answer": """This is the most useful confusion in the whole curriculum, so it is worth answering at length.

**`Recall@N` and `full_chain_recall` measure different stages.** `Recall@N` is about the
*candidate pool*: did stage one find the evidence at all? `full_chain_recall` is about the
*packed context*: did **every** gold item for a question survive into the k chunks the model
actually reads?

Widening N only affects the first. The second is bounded by `k`.

Concretely: a two-hop comparison question needs both entities' evidence in the packed context.
At `k=8`, with a global relevance ranking, it is entirely possible for six of your eight slots
to go to one entity. Adding 300 more candidates does not create a ninth slot.

**How to confirm it on your own run** — this is the diagnostic worth learning:

```python
for r in rows:
    if r["full_chain_recall_at_N"] == 1.0 and r["full_chain_recall"] == 0.0:
        print(r["qid"], r["question_type"])   # found it, then dropped it
```

If that list is long, your bottleneck is stage three, not stage one. Notebook 01 §1.3 measures
the two lines separately for exactly this reason: **the gap between them is precision work**,
and no amount of widening N closes it.

**What actually moves it:**

1. Raise `k` — the blunt fix; costs tokens and context precision
2. A better reranker — reorder so both hops land in the top 8
3. **A packing constraint** — notebook 02 §2.2 reserves slots per entity for comparison
   questions and moves full-chain recall +0.065 with the same candidates and the same k

Option 3 is the interesting one. A global relevance ranking cannot express a constraint about
*coverage*, so the constraint belongs in the packer rather than being wished for in the
reranker.

**The general form of this** is worth carrying: when a metric at stage *n* improves and a metric
at stage *n+1* does not, the bottleneck moved. That is not a disappointing result — it is the
measurement doing its job.""",
    },
    {
        "category": "Q&A",
        "title": "My reranker moved evidence recall and full-chain stayed inside the noise band. Ship it?",
        "body": """### The question in one line

`paired_bootstrap` says my change is "real" on evidence recall and "inside the noise band" on
full-chain recall. Which one do I believe?

### What I have already tried

Re-ran both. Same verdicts. Checked I am comparing the same question set.

### The numbers

```
evidence_recall     delta +0.0334  CI [+0.0101, +0.0584]  → real
full_chain_recall   delta +0.0338  CI [-0.0097, +0.0821]  → inside the noise band
```

The point estimates are nearly identical. Why do the verdicts differ?

### Where

Notebook 04 §4.10""",
        "answer": """Both verdicts are correct, and understanding why is worth more than the answer to "should I
ship".

**Why the intervals differ despite equal point estimates.** `evidence_recall` is continuous —
a question can score 0, 0.5 or 1.0 depending on how many gold items arrived.
`full_chain_recall` is **binary per question**: 1 only if *every* gold item arrived, 0
otherwise. Binary outcomes have much higher variance per sample, so the same effect size needs
more questions to become distinguishable from zero.

You have not measured two different effects. You have measured one effect with two different
amounts of statistical power.

**So do you ship it?** On this evidence, yes — with the honest sentence attached:

> "Ships on evidence recall, which cleared the band. Full-chain did not clear it on this eval
> set, and that is stated rather than rounded away."

That is close to verbatim what the capstone's decision record generates, and it is the sentence
an interview panel is listening for.

**Two things to do next**, in this order:

1. **Check the frozen slice.** A gain that appears on dev and vanishes on frozen is
   overfitting, and that matters far more than which metric cleared the band.
2. **Note the eval-set size in your record.** With 207 questions the noise band on a binary
   metric is around ±0.06. Doubling the set is the cheapest way to make this decision decidable
   and it costs less than any of the engineering — that belongs in "revisit when".

**The thing not to do** is pick whichever metric cleared and report only that one. Everyone can
tell, and it is the fastest way to lose credibility in a review.""",
    },
    {
        "category": "Q&A",
        "title": "RRF or weighted fusion — and what actually decided it on this corpus",
        "body": """### The question in one line

Notebook 04 says "default to RRF" and then measures RRF losing to BM25 alone. Which is the
advice?

### What I have already tried

Read §4.9 twice. I think I follow the mechanism but I do not know what to actually *do* on a
new corpus.

### Where

Notebook 04 §4.9""",
        "answer": """Both statements are right, and the resolution is a procedure rather than a preference.

**The advice is: default to RRF, *then measure*.**

RRF is the right default because it needs no labelled data, cannot be overfitted, and survives
score drift — a retriever whose score distribution shifts does not break the merge. If you have
no eval set, use RRF and do not think about it.

**Once you have a labelled set large enough to tune α, measure.** That is exactly what §4.9
does, and on this corpus the measurement overrode the default. The mechanism: RRF gives both
legs the same vote, and our dense leg is materially weaker than the lexical one here. An equal
vote drags the merge toward the weaker retriever.

So the procedure on a new corpus:

1. Start with RRF. Ship something.
2. Build the eval set (notebook 02 — this is the real work).
3. Sweep α. Compare against RRF **and** against each single leg — the second comparison is the
   one people skip, and it is the one that caught this.
4. If weighted wins, adopt it **and put a re-tune on a schedule**, because an α tuned on 200
   examples will not survive a corpus refresh.

**What you must not do** is copy α=0.2 from this repo. It is fitted to this corpus and this
encoder. With a modern encoder the dense leg gets stronger and α moves up — probably a lot.

One diagnostic worth running before you tune anything: **slice evidence recall by query class
for each leg separately** (§4.9 has the table). If your legs fail in the same places, fusion has
little to offer and you should fix the weaker leg instead. If they fail in different places —
which is the normal case — the size of the disagreement tells you roughly how much fusion can
buy you.""",
    },
    {
        "category": "Q&A",
        "title": "Retrieval looks fine on temporal questions and answer_correct is 0.091. Why?",
        "body": """### The question in one line

Temporal questions show evidence recall 0.807 but answer correctness 0.061. Is retrieval
lying to me?

### What I have already tried

Spot-checked five temporal questions — the gold evidence really is in the packed context.

### Where

Notebook 02 §2.2""",
        "answer": """Retrieval is not lying. You have found the seam between the retrieval lane and the answer
lane, and it is a good thing you looked.

**The offline reader is *extractive*.** It selects and cites supporting sentences from the
packed evidence. It cannot *derive* anything. A temporal question like "Did growth accelerate
or slow between Q2 and Q3?" needs the reader to compare two numbers and emit a word —
"accelerated" — that appears in neither chunk. The evidence is right there; the reader has no
mechanism to combine it.

This is stated in notebook 00's honesty inventory and it is deliberate: an extractive reader is
faithful by construction, which lets the whole retrieval half of the curriculum be measured
without an LLM adding its own variance to every number.

**Why this is a feature for teaching.** It is a clean demonstration of the deck's central claim
that an end-to-end score never tells you which stage moved. Run the fault-isolation tree on one
of these questions: Q1 yes, Q2 yes, Q3 yes, Q4 — is the answer entailed by the evidence? — and
you land on **generation fault**, correctly, with no ambiguity.

**What to do about it:**

- If you want the answer lane to work, set up Bedrock or the Claude API. `BedrockGenerator`
  drops into the same interface and the retrieval numbers will not move at all — which is
  itself the demonstration.
- If you are working on retrieval, **report the retrieval lane and say why the answer lane is
  low.** That is not a workaround; separating the lanes is the point.

**The transferable version:** when one lane moves and the others do not, you have located your
problem. A team watching only end-to-end quality would see 0.061 here and start tuning the
retriever, which is already doing its job.""",
    },
    {
        "category": "Q&A",
        "title": "Can I put these numbers in front of a client, and with what caveats?",
        "body": """### The question in one line

Can I quote the cost-per-query and recall figures from these notebooks to a client?

### Where

Notebooks 06 and 07""",
        "answer": """**The numbers, no. The arithmetic and the method, absolutely — and that is the more valuable
half anyway.**

Three reasons the absolute values do not transfer:

**1 · The corpus is synthetic.** Generated from a fact graph so gold evidence is true by
construction, which is excellent for teaching measurement and means nothing about your client's
documents. It is also *balanced by construction*, which is why one of the deck's failure modes
does not reproduce here.

**2 · The components are stand-ins.** LSA rather than a modern encoder; a logistic regression
rather than a trained cross-encoder; an extractive reader rather than a model. Notebook 00
prints the full inventory. Recall figures are not comparable to a production stack.

**3 · The rates are illustrative.** $3/MTok in, $15/MTok out, reads at 0.1× — placeholders,
labelled as such in `costs.Rates`. Provider prices change.

**What *does* transfer, and is worth bringing to a client:**

- The **line-item structure** of a per-query cost. Turning "AI is expensive" into cached prefix
  / evidence / question / generation / rerank / embedding is the conversation, and it is one
  most vendors cannot have.
- The **levers in order**, with the quality cost of each named. The first three are free; the
  last two are trades you declare out loud.
- The **method**: build the measurement first, change one thing, report the interval.
- The **index-time versus query-time** argument. Index-time compute is paid once, query-time
  forever — that reframing changes architecture decisions and costs nothing to explain.

**How to actually do it:** put the client's real rate card into `costs.Rates(...)`, their real
`k`, and their measured tokens-per-chunk. `unit_economics()` then produces *their* table. That
takes ten minutes and is defensible; quoting our number is not.

Worth saying plainly: a client who catches you quoting a number from a teaching corpus will
discount everything else you said. The honest version is also the one that survives the
follow-up question.""",
    },
    {
        "category": "Q&A",
        "title": "The notebook and the README disagree on a number. Which one do I trust?",
        "body": """### The question in one line

I ran notebook 01 and got different evidence recall than the README quotes.

### What I have already tried

Re-ran the cell. Same result.

### Where

Notebook 01 §1.3 vs README""",
        "answer": """Almost always a **stale kernel** holding an older `raglab` module. Restart the kernel and run
all cells from the top. `bootstrap()` pins the seed but it cannot un-import a module Python
already loaded.

If it persists after a clean restart, work through these in order — this is a small version of
the diagnostic discipline the whole curriculum teaches:

1. **Are you comparing the same thing?** The README quotes the `TUNED` configuration over the
   full 243-question set. Several notebook cells run on a 60–90 question *sweep subsample* to
   stay fast, and say so in the cell. A different population gives a different number and
   neither is wrong.
2. **Same slice?** Some cells report dev only; the frozen slice is reported separately.
3. **Did you change something upstream?** A different chunking strategy or `dim` changes
   everything downstream. `quickstart()` prints its configuration — compare that line.
4. **Genuinely different environment?** Different NumPy versions can produce tiny floating-point
   differences in the SVD. If your numbers differ in the third decimal, that is this and it does
   not matter. If they differ in the first, it is one of 1–3.

If you have ruled all four out, **that is a bug and worth an issue** — with your
`quickstart()` output line, your Python and NumPy versions, and both numbers. There is a
seeded example of exactly that shape in the tracker.

**The habit worth taking from this:** "the numbers disagree" is not one question, it is four,
and asking them in order takes about two minutes. That is the same move as the encoder-swap
checklist in notebook 04 §4.7, at a smaller scale.""",
    },

    # ── Design Reviews ───────────────────────────────────────────────────────
    {
        "category": "Design Reviews",
        "title": "Design review: retrieval for a regulated insurance client, 40M docs, strict ACLs [worked example]",
        "body": """### The problem, in the client's words

> "Our claims handlers waste 20 minutes per complex claim searching policy documents,
> precedents and regulatory guidance. We want them to ask a question and get a cited answer.
> Nothing can leave our VPC, and a handler must never see a document outside their line of
> business."

### Constraints

- **Latency:** 3 s p95. Handlers are on the phone to a customer.
- **Cost:** no hard ceiling given, which means there is one and nobody has said it. I will
  produce a per-query number in week one and make them own it.
- **Data residency:** everything inside their VPC. No managed API that leaves it.
- **ACLs:** line of business × jurisdiction × seniority. Roughly 400 distinct scopes.
- **Corpus:** ~40M chunks. Policy documents change on renewal; regulatory guidance changes
  unpredictably and matters immediately.
- **Team:** me plus one of their engineers, twelve weeks.

### Proposed design

```mermaid
flowchart LR
    subgraph idx["Index path — nightly + CDC"]
        S[Policy docs<br/>Precedents<br/>Reg guidance] --> P[Parse + normalise]
        P --> C[Structural chunking<br/>clause-level, heading path retained]
        C --> A[ACL denormalised onto chunk<br/>+ its own CDC stream]
        A --> E[Self-hosted encoder<br/>GPU backfill budgeted separately]
        E --> V[(OpenSearch in-VPC<br/>BM25 + kNN, one filter language)]
    end
    subgraph qp["Query path"]
        Q[Question] --> F[ACL predicate built from<br/>the handler's session claims]
        F --> H[Hybrid retrieve N=100<br/>ACL pre-filtered in the query]
        H --> R[Cross-encoder rerank →25]
        R --> K[Pack k=6, 5k token cap]
        K --> G[Generate + cite]
        G --> GD{Inline guardrail<br/>grounding + policy}
        GD -->|pass| U[Handler]
        GD -->|fail| RG[Regenerate or abstain]
    end
    V --> H
```

**Key choices and why:**

1. **OpenSearch in-VPC**, not a managed vector DB — one filter language and one ACL model for
   both legs, and it satisfies residency. Costs real cluster operations, which is a headcount
   conversation I will have in week one rather than week ten.
2. **Clause-level structural chunking.** For contracts the natural retrievable unit is a
   clause, not a paragraph. Heading path carried into every chunk so a retrieved clause is
   attributable.
3. **ACL denormalised onto the chunk, with its own change-capture stream.** Resolving 400
   scopes per request against the source system would blow the latency budget. The cost is
   revocation lag, and I will state it in minutes.
4. **Inline guardrail from day one.** The cost of a wrong answer here is regulatory, not
   embarrassing.

### What my own design costs

- **Pre-filtering with 400 selective scopes will degrade ANN recall.** Graph traversal
  dead-ends when the permitted set is sparse. I plan per-line-of-business namespaces to
  mitigate, which costs cross-LOB recall — real, and I would rather lose that than leak.
- **The guardrail is inside the latency budget on every turn.** That is ~200 ms I do not get
  back, and it makes the 3 s p95 tighter than it looks once generation is in there.
- **Self-hosted encoder means a GPU backfill for 40M chunks** before we serve a single query,
  and again on every encoder upgrade. Weeks, not days.
- **Twelve weeks is not enough to do all of this well.** I would cut agentic search entirely
  and probably cut the precedents corpus from phase one.

### What I would measure first

Week one, before any of the above: **label 100 real handler questions against the
fault-isolation tree.** If most failures turn out to be "the document exists but is out of
date", this is a freshness engagement and the retrieval architecture above is over-built.

### What I want challenged

1. Is denormalised ACL with a CDC stream the right call at 400 scopes, or should I be pushing
   for namespaces from the start and accepting the cross-scope recall loss?
2. Am I wrong to cut the precedents corpus from phase one? It is the part the client is most
   excited about.""",
    },
    {
        "category": "Design Reviews",
        "title": "Design review: sufficiency check as a model call or a classifier?",
        "body": """### The problem

The abstention issue in the tracker establishes that no retrieval-score threshold works. The
deck prescribes a "separate, cheap model call with a strict schema". Before building that, I
want to argue about whether a *trained classifier* would be better.

### Constraints

- Runs on every query in the escalate-by-default design, so it is inside the latency budget
- Must not itself become a component nobody can evaluate
- Has to work offline in this repo, with a documented path to the model version

### Option A — a cheap model call

```
prompt: question + packed evidence → {"sufficient": bool, "missing": [str]}
```

**For:** understands entailment, which is the actual question. Handles novel phrasings.
No training data needed.
**Against:** 200–500 ms and real money on every query. A second model to version, pin and
calibrate. Its failure mode is confident agreement, which is the same failure mode we are
trying to fix.

### Option B — a trained classifier over pair features

Features like the reranker's, plus: does the top evidence contain an entity of the type the
question asks for; does any single sentence cover the question's rare terms; margin between
top-1 and top-5 scores.

**For:** microseconds, free, deterministic. Trainable on the existing null set.
**Against:** needs labelled data we would have to keep producing. Almost certainly learns
surface features rather than entailment — and the notebook already showed four surface signals
sitting near chance. It would also be trained on *our* nulls, which are synthetic.

### My current view

**Option A, but not on every query.** Run it only when a cheap gate fires — top score below a
permissive threshold, or the question's rare terms not co-occurring in any single packed chunk.
That keeps the model call off the majority of traffic while catching the cases where it is
needed.

That is the same escalation shape as single-shot-then-loop, which makes me think it is the
right structure rather than a hedge.

### What my own design costs

- **Two components instead of one**, and the cheap gate has its own precision/recall to
  maintain
- **The gate's false negatives are invisible** — a null question that sails past the gate never
  reaches the model call, and nothing flags it
- Offline, the model call has to be a stand-in, which means the repo can demonstrate the
  *architecture* but not the *quality*

### What I would measure first

The cheap gate's recall on the null set, alone. If it cannot catch 80% of nulls at a tolerable
over-refusal rate, the escalation structure does not work and it is Option A on every query.

### What I want challenged

Is "gate then model" a real design or am I optimising a cost that has not been measured? I have
not priced Option A on every query against the actual traffic shape.""",
    },

    # ── Show & Tell ──────────────────────────────────────────────────────────
    {
        "category": "Show and tell",
        "title": "Capstone: two of my four improvements were inside the noise band [worked example]",
        "body": """### What I built

The build brief end to end: harness first, baseline, three measured improvements, frozen-slice
check, decision record.

### The result

| Step | Change | Δ full-chain | 95% CI | Verdict |
|---|---|---|---|---|
| 1 | baseline (fixed chunks, dense only, k=5) | — | — | — |
| 2 | + weighted hybrid α=0.2 | **+0.2500** | [+0.182, +0.318] | **real** |
| 3 | + learned cross-encoder N=50 | +0.0170 | [−0.063, +0.097] | inside the noise band |
| 4 | + routed query decomposition | +0.0000 | [+0.000, +0.000] | inside the noise band |

Noise band measured **before** any change: ±0.0614 on 207 dev questions.

### What surprised me

**Step 4 producing an exactly zero delta looked like a bug**, so I dug in rather than reporting
it. The diagnostic:

```
of 60 routed questions:
  candidate pool changed        47
  packed context changed         1
  packed context gained gold     0
```

Decomposition genuinely widened the pool — 47 of 60 questions got different candidates, and 297
extra retrieval calls were issued. The reranker then put **the same chunks on top anyway**. The
extra candidates were real and none of them won a slot.

That is a finding about this corpus, not a bug: at N=100 the first-stage pool already contained
what the sub-questions went looking for. On a corpus where the second hop genuinely falls
outside the top 100, this lever is the one that recovers it — and I would not have known that
distinction if the delta had been a plausible +0.02 I could have shipped without looking.

### The uncomfortable part

Step 3 is the change I was most confident about. It cleared the band on *evidence* recall
(+0.022, CI [−0.025, +0.068] — also inside, actually) and not on full-chain. My decision record
lists it under **rejected**, with "kept in the codebase and re-measured when the eval set
grows".

Writing that down was harder than any of the code.

### What I would do next

Double the eval set before doing any more engineering. The noise band on a binary metric at 207
questions is ±0.06, and both of my rejected changes are smaller than that. Making those
decisions *decidable* costs less than either implementation did.""",
    },
    {
        "category": "Show and tell",
        "title": "Negative result: contextual chunking cost 2.4x storage and did not clear the band",
        "body": """### What I tried

Contextual chunking — the Anthropic recipe. Prepend a generated sentence situating each chunk
in its parent document, then embed and BM25-index the augmented chunk. Notebook 01 introduces
it; I wanted to know whether to make it the default.

### The result

```
Strategy      Chunks  Storage×  Index ms  Evidence recall  Full-chain
structural     2,430      1.35       183            0.807       0.686
contextual     2,430      2.35       210            0.767       0.671
```

Worse on both quality metrics, at **2.4× the storage** and a per-reindex compute bill.

### Why I think it did not help here

Two reasons, and I think the first is the real one.

**1 · Our chunks do not lose their referent.** Structural chunking already carries the document
title and the heading path into every chunk, so a chunk reading "Engineering will widen the
interval" already says which product and which incident it belongs to. Contextual chunking is a
fix for chunks that have been orphaned from their context — and ours have not been.

**2 · The offline `describe()` is a template**, not a model. It adds source, date and entity
names, most of which are already in the chunk. With a real model generating a genuinely
situating sentence the result would likely differ, and I have not tested that.

### What I would tell a client

Contextual chunking is a real technique with a reported 49% reduction in failed retrievals on
Anthropic's corpus. **It is a fix for a specific failure — chunks that are unretrievable in
isolation — and you should confirm you have that failure before paying for it.**

The diagnostic is cheap: sample 20 chunks, read them cold, and ask whether you could tell what
they are about. If you can, your chunking is already carrying context and this will not help.

### What this cost me

About three hours, and it is the submission I am most pleased with. The storage column is what
made the decision, and I would not have looked at it if the recall column had gone the other
way — which is itself worth knowing about myself.""",
    },

    # ── Reading Club ─────────────────────────────────────────────────────────
    {
        "category": "Reading Club",
        "title": "Lost in the Middle (Liu et al., 2023) — is the U-curve still true, and does it matter? [worked example]",
        "body": """Discussion thread for the week 5 reading.

**The paper:** [arXiv:2307.03172](https://arxiv.org/abs/2307.03172). Holding the evidence set
constant and moving only the position of the relevant document, accuracy traces a U — strongest
at the start or end of the context, weakest in the middle.

### Three questions to argue about

**1 · The paper is from 2023 and the models have changed. Does the finding still hold?**

Worth being careful here in both directions. "Models got better so this is obsolete" is a
comfortable belief that would let us skip a measurement. But the effect size genuinely does
vary by model and task, and some of the specific results were on models nobody serves now.

The position the curriculum takes: **this is a paper to replicate, not to cite.** Notebook 05
§5.4 gives you the harness — force the gold chunk into position 1, mid and last with the
evidence set held constant, and report the spread. That is a one-run experiment against a real
model and almost nobody does it.

**2 · If the effect is real, which mitigation is worth its cost?**

The four the deck names, in cost order: keep k small (free, and saves money); order by score and
interleave edges (free, one line in the packer); restate the question after the evidence (~15
tokens); test it rather than assume it (one experiment).

Notice the first one is free *and* helps for a second reason — fewer chunks in the middle at
all. Worth asking whether the other three are worth doing if you have done the first properly.

**3 · What does this imply about long-context models replacing retrieval?**

The sharper version of the question. If accuracy degrades with position in a 4k context, what
happens in a 1M one? The deck's long-context matrix says accuracy "improves then plateaus or
declines past a model-specific length", which is careful phrasing for "nobody has a general
answer".

### What I would like people to post

If you have access to a model, **run the experiment on your own eval set and post the spread.**
Three numbers and one sentence about your setup. That is a more useful contribution to this
thread than any amount of argument about the paper.""",
    },

    # ── Ideas ────────────────────────────────────────────────────────────────
    {
        "category": "Ideas",
        "title": "Idea: a 'measurement smell' linter for PRs",
        "body": """Half-formed, posting it here rather than as an issue because it does not have a hypothesis yet.

The PR template asks for a measurement table. CI checks that the eval gate passes. Neither
checks whether the *claims in the PR description* are supported by the numbers in it.

Things a linter could catch:

- A delta quoted without an interval
- An interval that straddles zero, described with the word "improves"
- A metric quoted at more decimal places than the noise band justifies
- A comparison across different question sets or slices, presented as a before/after
- The word "significant" without a p-value or an interval anywhere nearby

Most of those are regex-able against the PR body plus the eval JSON.

**Where I am unsure:** this could easily become annoying and get disabled, which is worse than
not having it. And a linter that produces false positives on honest PRs teaches people to
ignore CI comments generally.

Possibly the right shape is a **comment that asks a question** rather than a check that fails.
"This PR describes an improvement — I could not find an interval for it. Is that in the eval
output?"

Does anyone think this is worth building, or is it solving a problem the template already
solves well enough?""",
    },
    {
        "category": "Ideas",
        "title": "Idea: replay a real cohort's questions as an eval slice",
        "body": """Every cohort asks roughly the same twenty questions in Discussions, and those questions are
*better* than our synthetic eval set in one specific way: they are the questions people
actually have.

**The idea:** turn the Q&A category into an eval slice. Each answered thread becomes a
(question, expected-evidence) pair pointing at the notebook section that answers it. Then
measure whether a retriever over the repo's own documentation can find the right section.

**Why it might be worth it**

- It is a real corpus (our docs) with real questions (student threads) and real gold labels
  (the section the answer linked to)
- It would immediately show which docs are unfindable, which is a documentation metric nobody
  has
- It is a genuine second corpus for the toolkit, which currently only ever sees one

**Why it might not be**

- The corpus is tiny — maybe 400 chunks of docs — so N=100 is a full scan again
- Question volume is low; it would take several cohorts to get to a usable set size
- The gold label is "the section a human linked to", which is a weaker label than the fact
  graph gives us

**What would make me confident:** somebody counting how many distinct answered Q&A threads
exist after one cohort. If it is 15, this is not worth building. If it is 60, it might be.""",
    },

    # ── Interview Prep ───────────────────────────────────────────────────────
    {
        "category": "Interview Prep",
        "title": "Critique my answer: 'How would you separate a retrieval failure from a generation failure?' [worked example]",
        "body": """Practising Q1-adjacent from `docs/06-interview-prep/legacy-bank.md`. Here is my answer — please tear it
apart.

---

**My answer:**

> "I'd look at whether the right documents were retrieved. If they were and the answer is still
> wrong, it's a generation problem. If they weren't, it's a retrieval problem. I'd check the
> logs to see what was retrieved for the failing queries and go from there."

---

### Self-critique before anyone else does

Reading it back, I think it is *correct* and *shallow*. It describes the idea but does not
demonstrate that I have ever done it. Specifically:

- "The right documents" — I never say how I know which those are. That silently assumes gold
  evidence exists, which is the whole hard part.
- Two buckets, not four. It collapses "never retrieved" with "retrieved and dropped during
  packing", and those have completely different fixes.
- "Check the logs" assumes a trace exists. In most engagements it does not, and saying so is
  itself a signal.
- No mention of what I would do with the *distribution* of failures.

### What I think a better version does

Names four verdicts rather than two, names the trace fields each needs, and ends with the
distribution being the work plan.

Would appreciate a critique of the rewrite as much as the original.""",
        "answer": """Your self-critique is better than most first answers, and it identifies the right three gaps.
Building on it:

**The four verdicts, and the question that separates each pair:**

1. *Is any gold evidence in the packed context?* No → retrieval fault, and **do not touch the
   prompt**. Saying that clause out loud is worth points, because reaching for the prompt first
   is the most common wrong instinct.
2. *Was every gold chunk in the top-N pool?* No → first-stage recall. Fix: chunking, encoder,
   fusion weights, ANN parameters, filters.
3. *Did the packed context keep it, intact and attributed?* No → ranking or packing. Fix:
   reranker, k, dedup, truncation.
4. *Is the answer entailed by the packed evidence?* No → generation. Fix: grounding
   instruction, abstention, citation contract, model.

If all four pass and the answer is still marked wrong — **suspect the label, the question, or
your rubric.** Ambiguous gold answers are the most under-reported source of "regressions", and
a candidate who volunteers that has clearly done this on real data.

**Two things to add that would move you from good to strong:**

*First*, the honest caveat about gold evidence. In a real engagement nobody hands you labels.
The answer to "how do I know which documents were right?" is that **you build that set in week
one** — sample 100 real failures, label the evidence by hand. That is notebook 02's whole
lesson and it is the part that makes the rest possible.

*Second*, end on the distribution rather than the procedure. "70% retrieval misses is a
chunking and hybrid problem; 70% grounding failures is a prompt and abstention problem. Those
are completely different four-week plans." That sentence is what tells a panel you have used
this to *decide something* rather than to diagnose one query.

**One thing to drop:** "check the logs". Say **trace** and name the fields — retrieved ids and
scores per stage, the packed context with provenance, the response, per-stage latency. If the
system does not have that, your first deliverable is the trace, and saying so is a stronger
answer than assuming it exists.

Your rewrite instinct is right. Post it and we will go again.""",
    },
    {
        "category": "Interview Prep",
        "title": "Talking about a synthetic-corpus project without it sounding like a toy",
        "body": """I want to put this project on my CV but I am worried the first question will be "isn't the
data fake?" and that I will not have a good answer.

How do I frame it honestly without undercutting myself?""",
        "answer": """Lead with the framing rather than defending it, and the question mostly does not get asked.

**The move is to make the synthetic corpus the *reason* the project is rigorous**, which is
true:

> "The corpus is generated from a fact graph, which means the gold evidence is true by
> construction — there's no annotation-error floor under any number I report. That's what let
> me measure things like the reranker's ceiling exactly rather than approximately. What it
> costs is external validity, and the repo says so explicitly — there's a real-versus-stand-in
> table on the front page."

Three things that does: turns the apparent weakness into a design decision, demonstrates you
know what it costs, and shows you documented the limitation before anyone asked.

**Then move to what actually transfers**, quickly, because that is where the interesting
conversation is:

> "The absolute numbers don't transfer and I wouldn't quote them. What transfers is the method
> — measure before you change, one change at a time, every delta with an interval against a
> measured noise band. Two of my four improvements turned out to be inside that band and
> they're in the decision record as rejected."

That last sentence is the one that lands. Almost no candidate volunteers a negative result, and
an interviewer who hears it stops assessing whether you can build RAG and starts assessing how
senior you are.

**Have these ready for the follow-ups:**

- *"Why not use a real dataset?"* — the record schema matches MultiHop-RAG and there is a loader
  for it; the constraint was that the whole curriculum has to run offline in seconds, which is
  ADR-0002.
- *"So you didn't work with real data?"* — separate the claim. You built and measured a system;
  you did not do a client engagement. If you have done client work, that is a different bullet.
  Do not blur them.
- *"What would you do differently?"* — have a real answer. "Double the eval set; the noise band
  at 207 questions is ±0.06 and several of my deltas sit inside it" is a good one because it
  shows you understand the limit of your own evidence.

**What not to do:** do not oversell it as production experience, and do not apologise for it
either. It is a rigorous piece of engineering with a stated scope. Say that, and move to the
decision record — which is the artefact almost nobody else in the pile will have.""",
    },
]


# ─────────────────────────────────────────────────── modular thread collections ──
# Threads live in scripts/seed/ by category once they carry full reply chains — a single
# literal holding sixty threads and three hundred replies is not reviewable in a diff.
from seed import (  # noqa: E402
    threads_clinic,
    threads_clinic_more,
    threads_design,
    threads_design_more,
    threads_exercises,
    threads_extra,
    threads_general,
    threads_ideas,
    threads_interview,
    threads_labsim,
    threads_labsim_more,
    threads_math,
    threads_more,
    threads_prep,
    threads_qa_more,
    threads_reading,
    threads_showandtell,
    threads_standup,
    threads_standup_more,
    threads_usecases,
)

# Five early threads were single posts with no conversation. Each has been superseded by a
# fully-arced version in scripts/seed/, so they are filtered rather than deleted in place —
# keeping the filter visible documents that the replacement was deliberate.
# Threads that were RENAMED rather than superseded in place. The old one is already live, so
# filtering it from DISCUSSIONS does nothing — it just sits there, and in one case it sat there
# teaching a finding this repository has since retracted.
#
# Each entry is old title -> the title that replaced it. The seeder prepends a retraction banner
# to the old thread and points at the new one. Edited, not deleted: the wrong version is part of
# the record, and a repository that argues for reporting negative results should not quietly
# remove its own.
RETIRED = {
    "The three findings in this repo that contradict the deck — and why we kept them":
        "The findings in this repo that contradict the deck — and the one of them that was wrong",
}

RETIREMENT_BANNER = """> [!WARNING]
> **Retracted, and kept for the record.** Finding 1 below does not reproduce: equal-weight RRF
> *beats* BM25 alone on this corpus, and the LSA leg is the stronger of the two, not the weaker.
> The mechanism argued for here was built on a number mis-attributed to the wrong configuration.
>
> The corrected post is [{replacement}]({url}). The retraction, including why nothing in CI was
> able to notice for months, is
> [ADR-0015](/{owner}/{repo}/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md).

"""

# ───────────────────────────────────────────────────────────────── cross-links ──
# Three pairs of threads cover the same ground and none of them says so.
#
# Two are a worked example and the real question a cohort member later asked anyway, which is
# not a mistake — the real one is longer, better and worth more, and the worked one is the
# shape it was written against. Leaving them unlinked means a reader finds whichever GitHub
# sorts higher and never learns the other exists. The third is GitHub's own boilerplate welcome
# post, which cannot be deleted and outranks the maintained one.
#
# Deliberately *not* handled by closing one as a duplicate: the duplicate's wording is how the
# next person will search, and both of these pairs are genuinely worth reading.
SEE_ALSO_MARK = "<!-- labsim:see-also:v1 -->"

SEE_ALSO = {
    "Welcome to advanced-rag-lab Discussions!": (
        "GitHub opened this thread automatically when Discussions was enabled. It is not "
        "maintained and nothing links to it.",
        ["Welcome — start here, and how this place works"]),

    "Recall@N climbs and full-chain recall does not. Where does the difference go?": (
        "A worked example. The version below was asked for real, runs six replies deep and "
        "gets further into the arithmetic — read that one if you only read one.",
        ["Recall@N keeps climbing but full-chain recall is flat. What am I not understanding?"]),
    "Recall@N keeps climbing but full-chain recall is flat. What am I not understanding?": (
        "The same question exists as a worked example, written by faculty to model the shape "
        "rather than to ask.",
        ["Recall@N climbs and full-chain recall does not. Where does the difference go?"]),

    "Week 3 · P2 Retrieval — the reranker week, and it did not go how we planned": (
        "The fusion figures in this thread do not reproduce. They are quoted and withdrawn in "
        "the Week 6 standup, which is linked below rather than replacing this one.",
        ["Week 6 · P5 Cost — the cache win, and a finding we have to retract"]),
    "Week 6 · P5 Cost — the cache win, and a finding we have to retract": (
        "This thread withdraws a claim made in Week 3. The original is left standing so the "
        "retraction has something to point at.",
        ["Week 3 · P2 Retrieval — the reranker week, and it did not go how we planned"]),

    "Talking about a synthetic-corpus project without it sounding like a toy": (
        "A worked example. The real thread below is longer and has the better answer.",
        ["How do I talk about a synthetic-corpus project without it sounding like a toy?"]),
    "How do I talk about a synthetic-corpus project without it sounding like a toy?": (
        "There is a worked example of this question too, written before anybody asked it.",
        ["Talking about a synthetic-corpus project without it sounding like a toy"]),
}

# ─────────────────────────────────────────────────────────── live corrections ──
# A retraction that only renames the title is not a retraction.
#
# The fusion thread was renamed away from the claim it was asserting, and that fixed what a
# reader sees in the sidebar. It did not touch the body, which still says "measures RRF losing
# to BM25 alone", and it did not touch the **accepted answer**, which explained the result with
# a mechanism pointing the wrong way — "our dense leg is materially weaker than the lexical
# one". Both are false, and an accepted answer carries more authority than a title.
#
# So: post the correction as a comment, and mark *that* as the answer. The wrong answer stays
# visible below it, which is the point — deleting it would delete the evidence that a room full
# of people found it convincing.
CORRECTION_MARK = "<!-- labsim:correction:v1 -->"

CORRECTED = {
    "RRF or weighted fusion — and what actually decided it on this corpus": """> [!IMPORTANT]
> **Correction, 2026-09-01.** The answer below this one is wrong about the mechanism, and it was
> the accepted answer for months. It is left in place deliberately. The procedure it gives —
> *default to RRF, then measure* — survives; the explanation of why does not.

**What the question assumed, and what the notebook actually said.**

The premise was that §4.9 "measures RRF losing to BM25 alone". It does not, and never did once
the comparison was run properly. Re-measured with `python scripts/run_eval.py --compare`
(`structural`, n=100, cross-encoder, k=8, 243 questions, paired bootstrap over questions):

```
configuration       evidence_recall  full_chain_recall               ndcg
-----------------------------------------------------------------------
bm25                         0.7118             0.4348             0.3639
dense                        0.7733             0.4638             0.6055
rrf                          0.7742             0.4638             0.5302
w0.2  (the default)          0.7645             0.4686             0.4767
w0.5                         0.7790             0.4686             0.5967
```

**RRF beats BM25 alone by +0.0624 evidence recall, ci (+0.0407, +0.0857).** That is not close
to the noise band. The earlier claim had the sign backwards.

**And the leg weighting was backwards too.** The old answer said the dense (LSA) leg is
"materially weaker than the lexical one". It is the stronger one: +0.0616 evidence recall over
BM25, ci (+0.0382, +0.0870), and +0.2416 nDCG. An α of 0.2 puts four fifths of the weight on
the *worse* leg, which is why `w0.2` gives up 0.0535 nDCG against plain RRF, ci (−0.0776,
−0.0295).

**The finding that is actually here, and it is a more interesting one.**

Fusion does not separate from its better single leg. `dense → rrf` is +0.0008 evidence recall,
ci (−0.0101, +0.0109) — squarely inside the band — and on nDCG fusion is a *real regression*
against the unfused dense leg, −0.0753, ci (−0.1061, −0.0462).

The mechanism is measurable rather than arguable. Fusion pays when the legs fail on **different**
queries. Here they fail on the same ones: of the 207 answerable questions the dense leg misses
95 and the lexical leg misses 102, and 92 of those are the same questions. P(lexical also misses
| dense misses) = **0.9684**; Jaccard of the two failure sets = 0.8762. There is almost nothing
for a merge to recover.

**So the revised procedure.**

1. Start with RRF. It needs no labelled data, cannot be overfitted, and survives score drift.
2. Build the eval set. This is still the real work.
3. Before tuning α, **measure the per-query failure overlap of your legs.** If P(B misses | A
   misses) is near 1, fusion has nothing to offer and tuning α is spending a week to move a
   number inside its own interval. Fix the weaker leg instead.
4. Compare any candidate against **each single leg**, not only against the previous fused
   configuration. Comparing a configuration against its own history is exactly the blind spot
   that let the original claim stand — nothing in CI was capable of noticing it.

**What you must still not do** is copy α=0.2 to another corpus. It is fitted to this corpus and
this encoder, and on this corpus it is not even the best α — `w0.5` is better on evidence recall
(+0.0145, ci +0.0048/+0.0254) and on nDCG, and identical on the gated metric, which is the only
reason the default has not moved.

Full write-up: [the fusion measurement note](/{owner}/{repo}/blob/main/docs/09-research/measurements/fusion-rules.md)
and [ADR-0015](/{owner}/{repo}/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md),
which is about why it survived rather than about fusion.
""",
}

# ─────────────────────────────────────────────────────── discussion labels ──
# Thirty-eight threads carried none. A forum without labels has exactly one axis — the category
# — and the category answers "what kind of post is this", never "what is it about". Somebody
# looking for everything on cost, or every thread where a measurement came back negative, had
# no way to ask.
#
# Deliberately few. A taxonomy nobody can hold in their head gets applied inconsistently and
# then means nothing, so this is four topic labels, four kinds, and one level.
DISCUSSION_LABELS = [
    ("worked example", "0e8a16",
     "Written by the maintainers to model a good question, a good wrong turn and a good "
     "correction. Not a real cohort member."),
    ("retracted", "b60205",
     "Contains a claim this repository has since withdrawn. Kept for the record, banded at "
     "the top."),
    ("mechanism", "1d76db",
     "Explains why something behaves as it does, in terms that transfer to a corpus you have "
     "not measured."),
    ("first-week", "c2e0c6",
     "Answers a question somebody has in their first week and is embarrassed to ask."),
]

# Which labels a thread carries, keyed by an exact title. Topic labels reuse the `area:` set the
# issues already use, so one query spans both surfaces.
THREAD_LABELS = {
    "Welcome — start here, and how this place works": ["first-week"],
    "The findings in this repo that contradict the deck — and the one of them that was wrong":
        ["negative-result", "mechanism", "retracted"],
    "The three findings in this repo that contradict the deck — and why we kept them":
        ["retracted"],

    "Recall@N climbs and full-chain recall does not. Where does the difference go?":
        ["worked example", "area: evaluation", "mechanism", "first-week"],
    "My reranker moved evidence recall and full-chain stayed inside the noise band. Ship it?":
        ["worked example", "area: evaluation", "negative-result"],
    "RRF or weighted fusion — and what actually decided it on this corpus":
        ["worked example", "area: retrieval", "mechanism", "retracted"],
    "Retrieval looks fine on temporal questions and answer_correct is 0.091. Why?":
        ["worked example", "area: evaluation", "mechanism"],
    "Can I put these numbers in front of a client, and with what caveats?":
        ["worked example", "cohort"],
    "The notebook and the README disagree on a number. Which one do I trust?":
        ["worked example", "first-week"],
    "Recall@N keeps climbing but full-chain recall is flat. What am I not understanding?":
        ["area: evaluation", "mechanism", "first-week"],

    "ANN recall is 0.00 at ef=64. Not degraded — zero. Where do I even start?":
        ["area: retrieval", "mechanism"],
    "Prompt cache hit rate is 4%. The prefix looks identical to me.":
        ["area: cost", "mechanism"],

    "Design review: sufficiency check as a model call or a classifier?":
        ["worked example", "area: agent"],
    "Design review: retrieval for a regulated insurer, 14 ACL groups, 40-day audit trail":
        ["area: retrieval", "cohort"],
    "Architecture breakdown: what actually changes when you move from 500 docs to 5 million":
        ["area: retrieval", "mechanism"],
    "Use case: internal policy search for 4,000 employees — where a RAG system is the wrong answer":
        ["cohort", "mechanism"],

    "Negative result: contextual chunking cost 2.4x storage and did not clear the band":
        ["worked example", "negative-result", "area: retrieval"],
    "Capstone: two of my four improvements were inside the noise band, and I nearly reported all four":
        ["negative-result", "area: evaluation"],

    "Talking about a synthetic-corpus project without it sounding like a toy":
        ["worked example", "cohort"],

    "Why is Cohen's κ so brutal on our abstention labels when agreement is 85%?":
        ["area: evaluation", "mechanism"],
    "Why is there a +0.5 in the BM25 IDF? Someone told me it is 'just smoothing'":
        ["area: retrieval", "mechanism"],

    "Start here — the simulator, and how to use it without cloning anything": ["first-week"],
    "R1 · my attempt — every shape check passes and the last one does not":
        ["worked example", "area: retrieval"],
    "R2 · rejected before it ran a single test, and I think the gate is wrong":
        ["worked example", "area: retrieval", "mechanism"],

    "Lost in the Middle (Liu et al., 2023) — does the U-curve survive on our corpus?":
        ["type: reading", "negative-result"],
    # `retracted` because its "what moved" section still carries the α=0.2 fusion claim, with
    # figures (0.7891, [+0.008, +0.041]) that do not reproduce. It is left standing on purpose —
    # the Week 6 standup quotes it verbatim in order to withdraw it, and a retraction that
    # quotes a thread nobody can find is not a retraction.
    "Week 3 · P2 Retrieval — the reranker week, and it did not go how we planned":
        ["cohort", "negative-result", "retracted"],

    # The twelve that shipped before THREAD_LABELS existed. An unlabelled thread is invisible
    # to `-label:"worked example"`, which is the filter a real cohort member wants first, and
    # invisible to `label:"type: exercise"`, which is how a facilitator finds the submissions.
    "Idea: replay a real cohort's questions as an eval slice":
        ["area: evaluation", "cohort"],
    "Idea: a 'measurement smell' linter that fails a PR describing a delta dishonestly":
        ["area: evaluation", "area: ci"],

    "Critique my answer: 'how would you separate a retrieval failure from a generation failure?'":
        ["area: evaluation", "mechanism"],
    "Asked 'why is your recall number trustworthy?' and I froze. What was he actually after?":
        ["area: evaluation", "mechanism"],
    "'How would you cut our RAG bill by 60%?' — I said quantisation and he looked disappointed":
        ["area: cost", "mechanism"],
    "The question I was not ready for: 'what would you have to see to abandon this design?'":
        ["cohort", "mechanism"],
    "How do I talk about a synthetic-corpus project without it sounding like a toy?":
        ["cohort"],

    "EX-01 · Establish the baseline you are allowed to argue with":
        ["type: exercise", "area: evaluation", "first-week"],
    "EX-02 · Break the tokenizer on purpose":
        ["type: exercise", "area: retrieval"],
    "EX-07 · Find the k where more context starts making answers worse":
        ["type: exercise", "area: evaluation", "area: cost"],
    "EX-09 · Try to reproduce comparison starvation, and fail":
        ["type: exercise", "area: evaluation", "negative-result"],

    # ── the second wave: one thread per thin or empty category ──────────────────
    "Hyphenated identifiers return zero rows since we picked up the tokenizer change. Underscored ones are fine.":
        ["area: retrieval", "mechanism"],
    "Dense leg is now worse than BM25 and mixed_version_check says the index is clean":
        ["area: retrieval", "mechanism"],
    "full_chain_recall dropped 0.0385 and nothing under raglab/ has changed":
        ["area: evaluation", "mechanism"],
    "The analyst persona's result count changes when legal ingests documents it cannot see":
        ["area: retrieval", "mechanism"],

    "Design review: two quarters of retrieval work before anything ships, and I want to be argued out of it":
        ["area: evaluation", "cohort", "mechanism"],
    "Design review: 40 tenants, one assistant, and I think the cache key is the whole design":
        ["area: cost", "cohort"],
    "Design review: the eval set for a policy assistant, before I spend three weeks labelling it":
        ["area: evaluation", "cohort"],

    "Week 4 · P3 Context — the exit criterion that was only measuring k":
        ["cohort", "area: evaluation", "mechanism"],
    "Week 5 · P4 Evaluation — a metric read 0.0 for three weeks and all of us filed it as 'not built yet'":
        ["cohort", "area: evaluation"],
    "Week 6 · P5 Cost — the cache win, and a finding we have to retract":
        ["cohort", "area: cost", "retracted"],
    "Week 7 · P6 Agentic — the audit found the second one, and it is the number that scoped this phase":
        ["cohort", "area: agent", "negative-result"],

    "F1 · my chunker tiles perfectly and drops the end of every document":
        ["worked example", "area: retrieval", "mechanism"],
    "E1 · my nDCG is 1.0 and I do not believe it":
        ["worked example", "area: evaluation", "mechanism"],
    "C1 · every named check passed and both bars are red":
        ["worked example", "area: cost", "mechanism"],
    "R3 · 0.8762 and 0.9684 tell the same story, so why does the bar sit between them":
        ["worked example", "area: retrieval", "mechanism"],

    "Why 1/log2(i+1) and not 1/i for the nDCG discount, and is the log base load-bearing?":
        ["area: evaluation", "mechanism"],
    "The paired bootstrap gives a much tighter interval if I resample documents. Which one is lying?":
        ["area: evaluation", "mechanism"],
    "I cannot reproduce the retracted multi-hop shortfall. Where did the 21 points come from?":
        ["area: evaluation", "mechanism", "retracted"],
    "What do BM25's k1 and b actually model? Deciding whether to freeze them or open them for tuning":
        ["area: retrieval", "mechanism"],

    "context_precision is 0.2433. Is three quarters of my context window wasted?":
        ["area: evaluation", "mechanism", "first-week"],
    "The system answers all 36 unanswerable questions. Why is that not the top priority?":
        ["area: evaluation", "mechanism"],
    "What is the difference between the macro and micro evidence recall, and which one is 0.7645?":
        ["area: evaluation", "mechanism", "first-week"],
    "Why does the repo ship alpha=0.2 when alpha=0.5 measures better?":
        ["area: retrieval", "mechanism"],

    "Cormack et al. 2009 (RRF) — our note said it did not transfer, and the note was wrong":
        ["type: reading", "area: retrieval", "retracted", "mechanism"],
    "MultiHop-RAG (Tang & Yang, COLM 2024) — we borrowed the schema, so where are the hard questions?":
        ["type: reading", "area: evaluation"],
    "Anthropic's Contextual Retrieval post — the client has read it and wants the 5.7% to 1.9%":
        ["type: reading", "negative-result", "cohort"],
    "CRAG's retrieval evaluator as a component we could actually grade before wiring it in":
        ["type: reading", "area: agent"],

    "Negative result: I swept alpha from 0.1 to 0.7 and answer_correct never moved":
        ["negative-result", "area: retrieval", "mechanism"],
    "I moved our release gate off the aggregate and onto the question_type slice":
        ["area: evaluation", "mechanism"],
    "Negative result: I tried to build the abstention gate and all I have is a control that passes":
        ["negative-result", "area: evaluation", "mechanism"],
    "Cut the prompt cache bill on C1 and nearly sent a client the wrong number":
        ["area: cost", "mechanism"],

    "Idea: RAPTOR over the temporal slice — a proposal, not another diagnosis":
        ["area: retrieval"],
    "Idea: teach the thing to say it does not know, and the embarrassing question underneath":
        ["area: evaluation", "mechanism"],
    "Idea: a semantic answer cache in front of the assembler":
        ["area: cost"],
    "Idea: learn alpha per query class instead of shipping one global compromise":
        ["area: retrieval", "retracted"],

    "Where does this go? The column the category table does not have":
        ["area: docs", "first-week"],
    "I have thirty minutes a week. What order do I do this in?":
        ["cohort", "first-week"],
    "How to read a number here, because I quoted one and could not defend it":
        ["area: evaluation", "first-week", "mechanism"],
}


# Titles that should change on threads that already exist.
#
# Seeding is keyed by title, so editing a title in this file does not rename anything — it
# creates a second thread and orphans the first. That is how #32 ended up sitting in
# Announcements for a day still teaching a retracted finding. RENAMED is the in-place path.
#
# `[worked example]` is stripped from eight titles because it is a tag wearing a title's
# clothes. It says nothing about the question, it pushes the actual subject past the point where
# GitHub truncates in a list, and it is duplicated on every one of them. It is a label now.
RENAMED = {
    # The retracted fusion finding, asserted in a title.
    "Should I use RRF or weighted fusion? The notebook says RRF is the default but then measures it losing. [worked example]":
        "RRF or weighted fusion — and what actually decided it on this corpus",

    "Why does Recall@N go up but full-chain recall stay flat? [worked example]":
        "Recall@N climbs and full-chain recall does not. Where does the difference go?",
    "My reranker improved evidence recall but full-chain recall is 'inside the noise band'. Do I ship it? [worked example]":
        "My reranker moved evidence recall and full-chain stayed inside the noise band. Ship it?",
    "Why is `answer_correct` so low on temporal questions when retrieval looks fine? [worked example]":
        "Retrieval looks fine on temporal questions and answer_correct is 0.091. Why?",
    "Can I use these numbers in a client conversation? [worked example]":
        "Can I put these numbers in front of a client, and with what caveats?",
    "The notebook gives different numbers than the README. Which is right? [worked example]":
        "The notebook and the README disagree on a number. Which one do I trust?",
    "Design review: should the sufficiency check be a model call or a classifier? [worked example]":
        "Design review: sufficiency check as a model call or a classifier?",
    "Negative result: contextual chunking cost 2.4× storage and did not clear the band [worked example]":
        "Negative result: contextual chunking cost 2.4x storage and did not clear the band",
    "How do I talk about a synthetic-corpus project without it sounding like a toy? [worked example]":
        "Talking about a synthetic-corpus project without it sounding like a toy",
}

SUPERSEDED = (
    "Design review: retrieval for a regulated insurance client",
    "Capstone: two of my four improvements were inside the noise",
    "Lost in the Middle (Liu et al., 2023) — is the U-curve",
    "Idea: a 'measurement smell' linter for PRs",
    "Critique my answer: 'How would you separate a retrieval",
)
DISCUSSIONS = [d for d in DISCUSSIONS if not d["title"].startswith(SUPERSEDED)]


def _answer_as_reply(thread):
    """Promote a thread's single `answer` into a one-reply chain marked as accepted.

    The original schema allowed a body and one answer. Threads written under it are still
    good content; they just need to be expressed in the shape the engine now speaks.
    """
    if thread.get("replies") or not thread.get("answer"):
        return thread
    out = dict(thread)
    out["replies"] = [{"by": "maintainer", "body": thread["answer"], "accepted": True}]
    out.pop("answer", None)
    return out


DISCUSSIONS = (DISCUSSIONS
               + threads_exercises.THREADS
               + threads_clinic.THREADS
               + threads_clinic_more.THREADS
               + threads_design.THREADS
               + threads_design_more.THREADS
               + threads_interview.THREADS
               + threads_standup.THREADS
               + threads_standup_more.THREADS
               + threads_more.THREADS
               + threads_prep.THREADS
               + threads_labsim.THREADS
               + threads_labsim_more.THREADS
               + threads_math.THREADS
               + threads_qa_more.THREADS
               + threads_reading.THREADS
               + threads_showandtell.THREADS
               + threads_ideas.THREADS
               + threads_general.THREADS
               + threads_usecases.THREADS)

ANSWERABLE = {name for name, _emoji, _desc, fmt in CATEGORIES if fmt == "ANSWER"} | {"Q&A"}


def _drop_unmarkable_answers(thread):
    """Strip `accepted` where the category cannot carry an answer.

    A resolution reply in an open-discussion category is still the resolution — it just
    cannot be *marked* as one, and asking GitHub to mark it is an error rather than a no-op.
    The flag stays in the source so the intent is visible, and so it starts working by itself
    if the category is later converted to Q&A format.
    """
    if thread["category"] in ANSWERABLE:
        return thread
    out = dict(thread)
    out["replies"] = [{k: v for k, v in r.items() if k != "accepted"}
                      for r in thread.get("replies", [])]
    return out


def _attach_extra_replies(thread):
    """Give a thread its conversation, where one was written separately in threads_extra."""
    for prefix, replies in threads_extra.REPLIES.items():
        if thread["title"].startswith(prefix):
            out = dict(thread)
            out["replies"] = list(thread.get("replies", [])) + replies
            return out
    return thread


DISCUSSIONS = [_drop_unmarkable_answers(_attach_extra_replies(_answer_as_reply(d)))
               for d in DISCUSSIONS]
