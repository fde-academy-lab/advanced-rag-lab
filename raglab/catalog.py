"""
The course's decision trees, matrices, failure points and interview
bank, as data.

Defining them once means the figure, the table and the executable predicate can
never drift apart. Wording is kept close to the deck so a learner moving
between the slides and the notebook is reading the same sentences.
"""
from __future__ import annotations

from .trees import Branch, DecisionMatrix, DecisionTree

DECK = "Retrieval, RAG and evaluation — the course this toolkit came from"

# ============================================================ decision trees ==

FAULT_ISOLATION = DecisionTree(
    key="fault_isolation",
    title="Fault isolation: which stage owns this bad answer?",
    caption="Four questions get you to a single owning stage. Walk it against one failing "
            "example before you touch any configuration.",
    source=DECK + " · slide 11",
    nodes=[
        Branch(
            question="Is any gold evidence in the top-k that was packed?",
            branch="NO", continues="YES ↓",
            outcome="Retrieval fault. Continue to Q2 — do not touch the prompt.",
            why="Nothing the prompt can say will make the model cite evidence it never saw.",
            knobs="none yet — narrow first", owner="Retrieval",
            terminal=False,
            test=lambda c: not c["gold_in_packed"]),
        Branch(
            question="Was every gold chunk present in the top-N candidate pool?",
            branch="NO", continues="YES ↓ candidates were there but did not survive ranking",
            outcome="First-stage recall. Chunking, embedding model, hybrid weights, ANN "
                    "parameters, filters.",
            why="Anything lost in stage one is lost permanently — no reranker can recover it.",
            knobs="N, chunking, hybrid weights, efSearch, filters",
            owner="First-stage retrieval",
            test=lambda c: not c["gold_in_candidates"]),
        Branch(
            question="Did the packed context contain the chunk, intact and attributed?",
            branch="NO", continues="YES ↓",
            outcome="Ranking or packing fault. Reranker, fusion, k, dedup, truncation, "
                    "provenance loss.",
            why="The evidence was retrievable and you discarded it — the cheapest class of "
                "failure to fix and the easiest to miss.",
            knobs="reranker, fusion, k, dedup, token cap, ordering",
            owner="Ranking / packing",
            test=lambda c: not c["gold_intact_in_context"]),
        Branch(
            question="Is the answer entailed by the packed evidence?",
            branch="NO", continues="YES ↓",
            outcome="Generation fault. Grounding instruction, abstention policy, citation "
                    "contract, model choice.",
            why="Correct evidence plus a bad contract still produces a bad answer. Evaluate "
                "generation controls separately from retrieval.",
            knobs="grounding instruction, abstention threshold, citation format, model",
            owner="Generation",
            test=lambda c: not c["answer_entailed"]),
    ],
    default="The pipeline is correct. Suspect the label, the question, or the rubric.",
    default_why="Ambiguous gold answers are the most under-reported source of “regressions”.")


CHUNKING_TREE = DecisionTree(
    key="chunking",
    title="Choosing a chunking strategy",
    caption="Do not answer chunk size with a number. Answer it with the shape of the document "
            "and the shape of the question.",
    source=DECK + " · slide 24",
    nodes=[
        Branch("Does the document carry reliable structure — headings, sections, cells, "
               "functions?", "YES", "Structural chunking. Split on the document's own "
               "boundaries. Carry the heading path into every chunk.", "NO ↓",
               why="The document already tells you where a coherent unit ends; using it is "
                   "free and it makes every chunk attributable.",
               knobs="heading depth, max tokens per section", owner="Index",
               test=lambda c: c.get("has_structure", False)),
        Branch("Do answers usually span several paragraphs of continuous argument?", "YES",
               "Large chunks with parent-document retrieval. Embed small, return the parent. "
               "Overlap 10–20%.", "NO ↓",
               why="Precision on the match, context in the answer — at 1.3x storage and a "
                   "much larger token bill per packed chunk.",
               knobs="child size, parent size, overlap", owner="Index",
               test=lambda c: c.get("answers_span_paragraphs", False)),
        Branch("Are queries short, factoid, and identifier-heavy?", "YES",
               "Small chunks, 200–400 tokens, plus a lexical index. Precision matters more "
               "than surrounding narrative.", "NO ↓",
               why="Identifiers need exact matching; a small chunk keeps the identifier's "
                   "neighbourhood dense and BM25 does the rest.",
               knobs="chunk size, BM25 b and k1", owner="Index + retrieval",
               test=lambda c: c.get("factoid_queries", False)),
        Branch("Is the corpus small enough to afford a model pass per chunk at index time?",
               "YES", "Contextual chunking. Prepend a generated situating sentence, then "
               "embed and BM25-index the augmented chunk.", "NO ↓",
               why="Index-time compute is paid once per chunk version; query-time compute is "
                   "paid forever. Prompt caching is what makes it affordable.",
               knobs="describe() model, index-time budget per document", owner="Index",
               test=lambda c: c.get("affordable_index_pass", False)),
    ],
    default="Recursive character splitting at ~512 tokens with 15% overlap — then measure "
            "Recall@N and revisit.",
    default_why="Treat this as a baseline to beat, not an answer.")


EMBEDDING_TREE = DecisionTree(
    key="embedding_model",
    title="Selecting an embedding model",
    caption="Dimension is a cost decision as much as a quality one.",
    source=DECK + " · slide 42",
    nodes=[
        Branch("Can the corpus leave the client's network?", "NO",
               "Self-hosted open-weight encoder. Budget GPU capacity for the initial backfill, "
               "not just steady state.", "YES ↓",
               why="Residency decides this before any benchmark does. Ask in discovery.",
               knobs="model size, GPU hours, backfill window", owner="Platform",
               test=lambda c: not c.get("corpus_can_leave_network", True)),
        Branch("Is the domain vocabulary far from general web text — clinical, legal, telecom, "
               "internal jargon?", "YES",
               "Benchmark 3 candidates on your eval set. Public leaderboard order rarely "
               "survives a domain shift. Lean harder on the lexical leg.", "NO ↓",
               why="Leaderboards rank on general corpora; your corpus is not one.",
               knobs="candidate set, hybrid alpha", owner="Retrieval",
               test=lambda c: c.get("domain_vocabulary_far", False)),
        Branch("Is the corpus multilingual, or are queries in a different language from the "
               "documents?", "YES",
               "Multilingual encoder with a shared space — and check that BM25 analyzers exist "
               "for every language you serve.", "NO ↓",
               why="A multilingual dense leg with a monolingual lexical leg is a half-built "
                   "hybrid that fails silently on the languages you forgot.",
               knobs="encoder, analyzer per language", owner="Retrieval",
               test=lambda c: c.get("multilingual", False)),
        Branch("Will the index exceed roughly 10M chunks, or is memory the binding constraint?",
               "YES", "Prefer a Matryoshka-trained model and truncate dimensions. Measure the "
               "recall you lose at 512 and 256 dims before paying for 3072.", "NO ↓",
               why="Dimension is a linear multiplier on RAM and on every ANN comparison.",
               knobs="output dimension, index type", owner="Platform",
               test=lambda c: c.get("large_index", False)),
    ],
    default="Take the strong general-purpose API model and move on.",
    default_why="Then spend the saved time on chunking and on the reranker, which usually "
                "return more Recall@k per hour of work than swapping encoders. Whatever you "
                "choose, pin the model version and store it on every vector.")


RELEASE_GATE = DecisionTree(
    key="release_gate",
    title="Should this retrieval change ship?",
    caption="In an interview, “what would block your release” is a question about judgement, "
            "not about metrics.",
    source=DECK + " · slide 69",
    nodes=[
        Branch("Did any frozen-slice metric drop beyond tolerance?", "YES",
               "Block. The frozen slice is the one thing tuning never saw — a drop there is "
               "real.", "NO ↓",
               why="Every other slice has been seen by a tuning run and can be overfitted.",
               knobs="tolerance per metric", owner="Release gate",
               test=lambda c: c.get("frozen_drop", 0.0) > c.get("tolerance", 0.01)),
        Branch("Did the average improve while a named slice or tenant got worse?", "YES",
               "Block by default. Someone experiences the regression as a total outage of "
               "their use case. Ship only with that owner's explicit sign-off.", "NO ↓",
               why="An aggregate is a summary that hides its own counterexample.",
               knobs="per-slice configuration, routing", owner="Product + release gate",
               test=lambda c: bool(c.get("regressed_slices"))),
        Branch("Is the gain inside the noise band of a re-run on the same config?", "YES",
               "Not a result. Measure your run-to-run variance once, write it down, and "
               "compare every delta against it.", "NO ↓",
               why="A delta smaller than your measurement error is a coin flip you have "
                   "chosen to believe.",
               knobs="eval-set size, bootstrap interval", owner="Measurement",
               test=lambda c: abs(c.get("delta", 0.0)) <= c.get("noise_band", 0.0)),
        Branch("Did cost per query or p95 latency move outside its envelope?", "YES",
               "Escalate, do not silently accept. Quality bought with unbudgeted cost is a "
               "decision for whoever owns the budget.", "NO ↓",
               why="Silently spending someone else's budget is how a team loses a renewal.",
               knobs="k, rerank depth, model routing", owner="Budget owner",
               test=lambda c: (c.get("cost_delta_pct", 0.0) > c.get("cost_envelope_pct", 15.0)
                               or c.get("p95_ms", 0) > c.get("p95_envelope_ms", 10**9))),
    ],
    default="Ship behind a canary.",
    default_why="Compare online signals against the control before full rollout, and keep the "
                "previous config one flag away.")


TREES = {t.key: t for t in (FAULT_ISOLATION, CHUNKING_TREE, EMBEDDING_TREE, RELEASE_GATE)}


# ========================================================= decision matrices ==

QUESTION_TYPE = DecisionMatrix(
    "question_type", "Question type drives retrieval strategy",
    ["Type", "What the system must do", "Dominant failure", "Lever that helps"],
    [["Inference", "Chain a fact in doc A to an entity named only in doc B",
      "Second hop never enters the candidate pool", "Query decomposition; iterative retrieval"],
     ["Comparison", "Retrieve balanced evidence for both sides, then contrast",
      "One entity dominates top-k; the other is starved",
      "Per-entity retrieval quotas in packing"],
     ["Temporal", "Order events, or restrict to a date window",
      "Embeddings ignore dates; the newest doc wins on similarity",
      "Metadata filters; recency-aware fusion"],
     ["Null", "Recognise the corpus does not contain the answer",
      "Model answers anyway from a plausible distractor",
      "Score thresholds; explicit abstention contract"]],
    source=DECK + " · slide 19",
    note="Null questions are the cheapest thing you can add to a client eval set and the "
         "fastest way to expose a system that never says “I don't know”.")

CHUNKING_MATRIX = DecisionMatrix(
    "chunking_matrix", "Chunking strategies and what they cost",
    ["Strategy", "Best for", "Fails on", "Index cost", "Storage"],
    [["Fixed-size", "Homogeneous prose, quick baselines",
      "Tables, code, anything with structure", "low", "1×"],
     ["Recursive", "Mixed prose with paragraph breaks",
      "Documents with no punctuation rhythm", "low", "1×"],
     ["Structural", "Contracts, wikis, API docs, source files",
      "Scanned PDFs with unreliable layout", "medium", "1×"],
     ["Semantic", "Topic-drifting long-form text",
      "Producing unpredictable chunk sizes", "medium", "1×"],
     ["Parent-document", "Precise matching, wide context needed",
      "Tight token budgets — parents are big", "low", "1.3×"],
     ["Contextual", "Chunks that lose their referent in isolation",
      "Corpora that churn hourly — you re-pay per edit", "high", "1.2×"],
     ["Late chunking", "Keeping long-range context inside each vector",
      "Encoders with short context limits", "medium", "1×"]],
    source=DECK + " · slide 25", recommend="Structural",
    note="Storage multiplier is relative to fixed-size chunking of the same corpus. Index cost "
         "is compute you pay once per document version — and again on every reindex.")

STATE_LOCATION = DecisionMatrix(
    "state_location", "Where the retrieval state should live",
    ["Option", "Choose when", "What it costs you", "Scale ceiling"],
    [["In-process (FAISS, in-memory)", "Single tenant, read-mostly, rebuild is cheap",
      "No live updates; every replica holds a full copy", "~1–5M chunks"],
     ["Postgres + pgvector",
      "You already run Postgres and need transactional joins with business data",
      "Index build competes with OLTP; tuning is on you", "~10–50M chunks"],
     ["Search engine (OpenSearch, Elastic, Vespa)",
      "You need BM25 and vectors with one filter language and one ACL model",
      "Cluster operations; JVM tuning; real headcount", "100M+ chunks"],
     ["Managed vector DB", "Small team, fast delivery, elastic and bursty load",
      "Per-query pricing; data residency review; a second ACL model to reconcile",
      "vendor-defined"]],
    source=DECK + " · slide 28",
    note="In a regulated client environment this is usually decided by data residency and the "
         "existing ACL model, not by recall benchmarks. Ask about both in discovery, before "
         "you benchmark anything.")

ANN_INDEX = DecisionMatrix(
    "ann_index", "Choosing the ANN index",
    ["Index", "Strength", "What it costs", "Recall knob", "Use when"],
    [["Flat / exact", "Recall = 1.0 by construction; no tuning, no surprises",
      "Linear scan — latency grows with corpus size", "none needed",
      "<500k chunks, or as ground truth"],
     ["HNSW", "Best latency/recall tradeoff; supports incremental insert",
      "Memory-resident graph, roughly 1.5–2× the raw vectors; deletes need compaction",
      "efSearch, M", "Default for online serving"],
     ["IVF-PQ", "Compresses vectors hard — the memory-constrained option",
      "Quantisation loses recall; needs a training pass and periodic re-training",
      "nprobe, nlist", "100M+ vectors on limited RAM"],
     ["Disk-based graph", "Billions of vectors at SSD cost rather than RAM cost",
      "Higher and noisier tail latency; rebuilds are slow", "beam width",
      "Archive-scale corpora"]],
    source=DECK + " · slide 41", recommend="HNSW",
    note="Always measure ANN recall against flat search on a sample. Approximate means a gold "
         "chunk can be missing from top-N even though the embedding was correct — invisible in "
         "every downstream metric. And test recall with your real filters, not without them.")

RERANKER_MATRIX = DecisionMatrix(
    "reranker", "Reranking options and what each one buys",
    ["Stage 2 choice", "How it scores", "Added latency", "Index cost", "Reach for it when"],
    [["None", "First-stage score is the final order", "0 ms", "none",
      "Recall@k is already near 1.0 at small k"],
     ["Cross-encoder", "Full attention over the query–passage pair",
      "50–300 ms (batched, N≈50)", "none",
      "Default. Highest quality per unit of engineering effort."],
     ["Late interaction", "MaxSim over precomputed token vectors", "10–40 ms", "10–100× storage",
      "Strict latency SLA and storage is cheap for you"],
     ["LLM reranker", "Prompted to score or order the candidate list", "300–2000 ms", "none",
      "Relevance needs reasoning, or as an offline labeller for training data"]],
    source=DECK + " · slide 47", recommend="Cross-encoder",
    note="Reranker ceiling: no stage-2 model can rank a document it never received. If "
         "Recall@N is 0.78, reranking cannot take end-to-end evidence recall above 0.78.")

METRIC_SELECTION = DecisionMatrix(
    "metric_selection", "Which metric catches which failure",
    ["Symptom in production", "Metric that moves", "Metric that stays flat", "Stage to fix"],
    [["Answers are confident and wrong on new terminology", "Evidence Recall@N",
      "Faithfulness — the model is loyal to bad evidence", "First-stage retrieval"],
     ["Right document found, wrong part quoted", "nDCG@k · context precision", "Recall@k",
      "Chunking / reranking"],
     ["Two-part questions answered halfway", "Full-chain recall · completeness",
      "Answer correctness on single-hop slices", "k, packing, decomposition"],
     ["Citations point at the wrong source", "Citation accuracy · attribution",
      "Correctness — the answer can be right anyway", "Context assembly"],
     ["Invented facts with correct evidence present", "Faithfulness / groundedness",
      "All retrieval metrics", "Generation controls"],
     ["System answers questions it should refuse", "Abstention precision/recall on null set",
      "Everything, if the null set is missing", "Thresholds + prompt contract"],
     ["Quality dropped only for one customer", "Per-tenant sliced metrics", "Every global average",
      "Index scoping / filters"]],
    source=DECK + " · slide 64",
    note="Read this right to left in a debugging session: pick the symptom, then the metric "
         "that will move.")

LONG_CONTEXT = DecisionMatrix(
    "long_context", "“Why not just put everything in the context window?”",
    ["Dimension", "Stuff the window", "Retrieve, then generate"],
    [["Cost per query", "Scales with corpus size. 200k tokens per call is a per-query bill.",
      "Roughly flat in corpus size. Index cost is paid once."],
     ["Latency", "Prefill grows with input length; time-to-first-token suffers.",
      "Bounded by the evidence cap you set."],
     ["Accuracy at length",
      "Improves then plateaus or declines past a model-specific length. Distractors accumulate.",
      "Precision is a controllable parameter."],
     ["Attribution", "Weak. Which of 400 documents produced the claim?",
      "Native. The packed set is the citation set."],
     ["Access control", "You must pre-scope the dump per user anyway — which is retrieval.",
      "Filters are already in the query path."],
     ["Freshness", "Always current — nothing is precomputed.", "Bounded by index lag."],
     ["Build effort", "Hours.", "Weeks, plus ongoing index operations."]],
    source=DECK + " · slide 58",
    note="The honest client answer: stuff the window for a small, slow-changing, single-tenant "
         "corpus and ship this week. Move to retrieval when cost per query, attribution or "
         "access control becomes the binding constraint — sooner than the client thinks.")

COST_LEVERS = DecisionMatrix(
    "cost_levers", "Cost levers, in the order you should pull them",
    ["#", "Lever", "Typical saving", "What it costs in quality"],
    [["1", "Cache the stable prefix; reorder the prompt by volatility", "15–30%", "Nothing"],
     ["2", "Deduplicate near-identical chunks before packing", "5–15%",
      "Usually improves it — duplicates are distractors"],
     ["3", "Cap output length and enforce a terse schema", "10–25%",
      "None if the contract is well specified"],
     ["4", "Lower k after proving full-chain recall holds", "20–40%",
      "Real risk on multi-hop — measure the tail, not the mean"],
     ["5", "Route easy queries to a smaller model", "30–60%",
      "Needs a router you must also evaluate — a second system"],
     ["6", "Semantic caching of full answers", "varies wildly",
      "A near-miss cache hit serves a confidently wrong answer"],
     ["7", "Drop the reranker", "~2%",
      "The worst trade on this list — large quality loss, trivial saving"]],
    source=DECK + " · slide 81",
    note="Work top down. The first three are free in quality terms; the last two are trades "
         "you must declare.")

AGENTIC_VS_SINGLE = DecisionMatrix(
    "agentic_vs_single", "When the loop earns its cost",
    ["Signal", "Single-shot RAG", "Agentic search"],
    [["Question shape", "Answerable from evidence one query can surface",
      "Later hops depend on what earlier hops returned"],
     ["Latency budget", "1–3 s, predictable", "5–60 s, high variance — needs progress UI"],
     ["Cost per query", "One generation", "3–20× — and the tail is what hurts"],
     ["Failure mode", "Missing evidence, one bad answer",
      "Compounding drift across turns; harder to explain to a client"],
     ["What you evaluate", "One retrieval and one answer",
      "The whole trace: decomposition, tool choice, stop decision, answer"],
     ["Operational load", "Standard service monitoring",
      "Per-turn tracing, budget guards, kill switches"]],
    source=DECK + " · slide 84",
    note="A useful middle: run single-shot by default and escalate to the loop only when the "
         "sufficiency check on the first pass fails. Most traffic pays single-shot cost.")

PROVIDER_CACHE = DecisionMatrix(
    "provider_cache", "Prompt caching: two providers, practical differences",
    ["Dimension", "OpenAI (GPT-5.6)", "Anthropic"],
    [["Activation", "Implicit caching or explicit prefix marking",
      "cache_control, automatic or explicit breakpoints"],
     ["Write price", "1.25× uncached input for explicit cache writes",
      "1.25× for 5-minute retention, 2× for 1-hour"],
     ["Read price", "Discounted cached input; exact rate is model-specific",
      "0.1× base input price for the active cache duration"],
     ["Observe", "cached and cache-write token counters",
      "input, cache-creation, cache-read and output fields"]],
    source=DECK + " · slides 76–78",
    note="Do not compare cache costs without fixing the model, retention policy, prompt shape "
         "and expected reuse rate. Rates change; the arithmetic does not.")

TRACE_EVAL = DecisionMatrix(
    "trace_eval", "Evaluating a search trace, not just an answer",
    ["Trace property", "How to score it", "What a bad score means"],
    [["Decomposition quality", "Do the sub-questions cover every gold evidence item?",
      "The plan was wrong; no amount of retrieval will rescue it"],
     ["Tool selection accuracy", "Fraction of turns using the tool an expert would have used",
      "Tool descriptions are ambiguous, or there are too many tools"],
     ["Turn efficiency", "Turns taken ÷ minimum turns needed for full evidence",
      "Cost is being burned on redundant search"],
     ["Cumulative evidence recall", "Gold evidence found anywhere in the trace",
      "The loop never reached the second hop"],
     ["Evidence retention", "Gold found early that survived into the final context",
      "You found it and then threw it away — the worst and most invisible failure"],
     ["Stop-decision quality", "Precision and recall of the sufficiency check vs human judgment",
      "Either premature confidence, or loops that never terminate"]],
    source=DECK + " · slide 86", recommend="Evidence retention")

BUILD_RUBRIC = DecisionMatrix(
    "build_rubric", "Build rubric",
    ["Dimension", "Meets the bar", "Exceeds it", "Wt."],
    [["Measurement discipline", "Every change has a before/after on the same set",
      "Run-to-run variance measured and quoted alongside each delta", "25"],
     ["Retrieval quality", "Full-chain recall improves over baseline within the token cap",
      "Gains hold on the frozen slice and on the hardest question type", "20"],
     ["Grounding & abstention", "Citations resolve; null questions are refused",
      "Abstention threshold justified with a precision/recall curve", "15"],
     ["Cost & latency", "Inside both ceilings, measured per query",
      "A stated cost/quality frontier with the chosen operating point marked", "15"],
     ["Traceability", "Any answer can be replayed from its stored trace",
      "Traces are diffable between two runs of the same query", "10"],
     ["Decision record", "One page: what shipped, what was rejected, and why",
      "Names the condition under which the decision should be revisited", "15"]],
    source=DECK + " · slide 88",
    note="The weighting is deliberate: the decision record is worth as much as retrieval "
         "quality. That is the job.")

SIGNAL_ANTISIGNAL = DecisionMatrix(
    "signal", "Signal and anti-signal in a retrieval interview",
    ["Dimension", "Signal", "Anti-signal"],
    [["Problem framing",
      "Asks what is being measured and on which set before proposing anything",
      "Starts naming tools and vendors in the first minute"],
     ["Debugging", "Bisects: isolates a stage, compares against a known-good reference",
      "Lists plausible causes without a way to eliminate any of them"],
     ["Tradeoffs", "States the cost of their own recommendation, unprompted",
      "Presents an option with only upsides"],
     ["Numbers", "Estimates cost and latency out loud, then sanity-checks the magnitude",
      "“It depends on the workload” with no attempt at an estimate"],
     ["Scope control", "Sequences work and says what they would not do in the time available",
      "Proposes a full rebuild for a four-week engagement"],
     ["Client posture", "Turns a demand into a quantified choice the client can own",
      "Either agrees to everything, or refuses without offering an alternative"],
     ["Honesty", "“I don't know — here is how I'd find out in a day”",
      "Confident numbers that fall apart on one follow-up question"]],
    source=DECK + " · slide 96")

MATRICES = {m.key: m for m in (QUESTION_TYPE, CHUNKING_MATRIX, STATE_LOCATION, ANN_INDEX,
                               RERANKER_MATRIX, METRIC_SELECTION, LONG_CONTEXT, COST_LEVERS,
                               AGENTIC_VS_SINGLE, PROVIDER_CACHE, TRACE_EVAL, BUILD_RUBRIC,
                               SIGNAL_ANTISIGNAL)}


# ============================================================ failure points ==
FAILURE_POINTS = {
    1: [("Lexical gap", "“retry delay” does not match a document that only says "
                        "“backoff interval.”"),
        ("Missing hop", "One of two required documents is absent from top-k; the answer uses "
                        "only half the evidence chain."),
        ("Distractor dominance", "A high-scoring but irrelevant passage crowds out the "
                                 "required source."),
        ("Metric blind spot", "Answer accuracy looks stable while Evidence Recall@10 has "
                              "regressed.")],
    3: [("Boundary loss", "A premise and its conclusion are split across chunks with no "
                          "overlap."),
        ("Stale index", "A document changes, but its old embedding remains in production."),
        ("Metadata drop", "Title or publication date is not indexed, so a required filter "
                          "cannot be applied."),
        ("Missing trace", "A bad answer cannot be replayed because retrieved chunks and "
                          "scores were not logged.")],
    4: [("Identifier miss", "Dense search retrieves related incidents but not "
                            "ERR_CONN_RESET."),
        ("Embedding mismatch", "Documents use a passage prefix; queries omit the required "
                               "query prefix."),
        ("ANN loss", "The approximate index does not return a gold chunk that exact search "
                     "would find."),
        ("Reranker ceiling", "The gold document is not in the candidate pool, so reranking "
                             "cannot recover it.")],
    5: [("Top-k too small", "A two-document answer receives only the first evidence hop."),
        ("Context overload", "Twelve low-value chunks bury the highest-ranked source."),
        ("Provenance loss", "Concatenated snippets make the citation point to the wrong "
                            "document."),
        ("No abstention", "The model fills an evidence gap with a plausible but unsupported "
                          "claim.")],
    6: [("Answer-only metric", "The final answer is correct by chance even though retrieval "
                               "missed the gold evidence."),
        ("Static benchmark", "A retriever overfits to the offline set and fails on new "
                             "production terminology."),
        ("Judge drift", "A rubric prompt changes and silently shifts LLM-as-a-judge scores."),
        ("Average masking", "Strong easy-case performance hides failure on long-tail "
                            "multi-hop queries.")],
}


# =========================================================== interview bank ===
SECTION_QUESTIONS = {
    1: ["How would you separate a retrieval failure from a generation failure?",
        "Which retrieval metrics would you use for a multi-hop RAG system, and why?",
        "How do offline evaluation and production monitoring complement each other?",
        "What makes an LLM-as-a-judge rubric trustworthy enough to use?"],
    3: ["How would you design a RAG pipeline for documents that change daily?",
        "Which metadata belongs in the index, and which belongs in the prompt?",
        "How do you select chunk size and overlap for a mixed-format corpus?",
        "What trace data is required to reproduce an answer failure?"],
    4: ["When would you use BM25, dense retrieval, or a hybrid retriever?",
        "Why does L2 normalization change the relationship between cosine similarity and dot "
        "product?",
        "How do early- and late-interaction models differ in latency, storage, and quality?",
        "How would you diagnose a recall regression after switching embedding models?"],
    5: ["How would you tune top-k when answer quality improves but latency and cost rise?",
        "What belongs in a context block to make citations reliable?",
        "How would you detect and mitigate “lost in the middle” behavior?",
        "When should a RAG system abstain instead of answering?"],
    6: ["How would you build an evaluation dataset for a proprietary knowledge base?",
        "Which metrics diagnose retrieval ranking quality versus answer faithfulness?",
        "How do you calibrate an LLM-as-a-judge against human assessment?",
        "What would block a retrieval-model release in your evaluation pipeline?"],
}

INTERVIEW_BANK = [
    {"n": 1, "tag": "scoping under ambiguity",
     "q": "Your client's assistant answers correctly about 80% of the time. They want 95%. "
          "You have four weeks. What do you do in week one?",
     "testing": [
         "Whether you interrogate the number before acting on it. Who measured 80%? On what "
         "set? Correct by whose judgment?",
         "Whether your instinct is to build or to measure. Four weeks is enough time to fix "
         "the wrong thing twice.",
         "Whether you can say “95% may not be achievable, and here is the evidence” to a "
         "client."],
     "strong": [
         "Days 1–2: sample 100 real failures and hand-label each against the fault-isolation "
         "tree — not retrieved, retrieved-not-used, or wrong despite good evidence.",
         "Day 3: the distribution decides the plan. 70% retrieval misses is a chunking and "
         "hybrid problem; 70% grounding failures is a prompt and abstention problem.",
         "Days 4–5: stand up a regression set from those 100 cases plus null questions, and "
         "freeze a slice.",
         "Reframe the target: some of the 20% is unanswerable from the corpus. Split the goal "
         "into “answer correctly” and “refuse correctly”."],
     "red": "Jumping straight to “I'd try a better embedding model”; proposing three changes "
            "at once; accepting 95% without asking how it is measured.",
     "notebook": "01 — the fault-isolation tree, executed over a labelled failure sample."},
    {"n": 2, "tag": "release judgment · stakeholder handling",
     "q": "A retrieval change raises average answer quality 6%, but one business unit reports "
          "the system got worse. Do you ship it?",
     "testing": [
         "Whether you treat an aggregate as evidence or as a summary that hides its own "
         "counterexample.",
         "Whether you can separate “is the complaint real” from “is the complaint decisive”.",
         "Whether you will actually make a decision, or hide behind “it depends”."],
     "strong": [
         "Reproduce before believing. Pull that unit's real queries, run both configs, check "
         "whether the regression appears in the metrics.",
         "Find the mechanism. Identifier-heavy corpus plus a fusion shift toward dense; or "
         "short documents plus a chunking change that altered avgdl.",
         "Prefer a per-segment configuration over an all-or-nothing ship, if the mechanism "
         "supports it.",
         "Make the decision explicit and owned, with the number and a remediation date."],
     "red": "“The average improved, so we ship”; treating the complaint as politics; promising "
            "a later fix with no mechanism and no date.",
     "notebook": "06 — sliced metrics and the release-gate tree."},
    {"n": 3, "tag": "systematic debugging",
     "q": "You upgraded the embedding model and Evidence Recall@10 fell from 0.86 to 0.71. "
          "Walk me through the diagnosis.",
     "testing": [
         "Whether you check operational causes before model-quality causes. A 15-point drop is "
         "almost never “the new model is worse”.",
         "Whether you know the specific ways an encoder swap breaks a pipeline.",
         "Whether you can bisect rather than guess."],
     "strong": [
         "1 · Mixed-version index. Are some vectors still from the old model? Check the "
         "model-version tag on a sample.",
         "2 · Prefix asymmetry. Does the new model require query and passage prefixes, and are "
         "both applied on the right side?",
         "3 · Normalisation and metric. Are the new vectors L2-normalised, and is the index "
         "still configured for cosine?",
         "4 · Dimension truncation. Was the model shortened to fit the existing schema?",
         "5 · Context-length truncation. Does the new encoder silently cut long chunks?",
         "6 · ANN parameters. Same efConstruction/M? Compare against flat search to isolate "
         "index loss from embedding loss.",
         "7 · Only now: the model really is worse on this domain. Slice the misses to show "
         "where."],
     "red": "Starting at step 7; not knowing flat search gives a ground-truth comparison; no "
            "plan to bisect.",
     "notebook": "04 — every one of steps 1–6 is reproducible on the in-memory index."},
    {"n": 4, "tag": "enterprise constraints · security thinking",
     "q": "Legal requires that no answer can be influenced by a document the user is not "
          "allowed to read. Design for that.",
     "testing": [
         "Whether you hear “influenced” and realise post-filtering does not satisfy it.",
         "Whether you think about caches, logs and traces as part of the security boundary.",
         "Whether you can name what this costs in recall up front, rather than in UAT."],
     "strong": [
         "Pre-filter, always. The ACL predicate goes into the ANN query so restricted chunks "
         "never become candidates — and never contribute to a score, a rank, or a rerank batch.",
         "Name the recall cost. Selective filters degrade graph traversal; mitigate with "
         "per-tenant namespaces or partitioned indexes, and measure recall with filters on.",
         "Close the side channels. Caches keyed per tenant; traces inside the same compliance "
         "boundary; result counts and latency not leaking existence.",
         "Revocation has an SLA. Denormalised ACLs need their own change-capture stream.",
         "Prove it. An automated test that runs one query as two personas and asserts disjoint "
         "evidence sets — part of the release gate."],
     "red": "“Filter the results after retrieval”; forgetting the cache; no answer for "
            "revocation propagation.",
     "notebook": "03 — the two-persona disjointness test is written and run."},
    {"n": 5, "tag": "unit economics · saying no well",
     "q": "Agentic search costs $0.90 on hard questions. Finance wants $0.15. What do you "
          "change, and what do you refuse to change?",
     "testing": [
         "Whether you can decompose a per-query cost into line items from memory.",
         "Whether you optimise the distribution rather than the worst case.",
         "Whether you push back with a quantified consequence instead of silently degrading "
         "quality."],
     "strong": [
         "Reframe from worst case to blended cost. If 8% of queries are hard, the blended "
         "number may already be near target.",
         "Escalate, do not loop by default. Single-shot first; enter the loop only when the "
         "sufficiency check fails.",
         "Cheap wins in order: cache the stable prefix and tool schemas; carry a compacted "
         "evidence summary between turns; cap turns; small model for decomposition and "
         "sufficiency, large one only for synthesis.",
         "What I refuse: removing the grounding and abstention checks, and removing the trace.",
         "Quantify the residual: “$0.22 blended without quality loss. $0.15 means capping at "
         "two turns, which costs X points of full-chain recall. That is a business decision.”"],
     "red": "Agreeing to the number without a plan; “we'll use a cheaper model” as the whole "
            "answer; no quality cost attached to any lever.",
     "notebook": "07 and 08 — the blended-cost model and the escalation policy, both measured."},
    {"n": 6, "tag": "epistemics of measurement",
     "q": "Your LLM judge says quality went up. How would you know if the judge is wrong?",
     "testing": [
         "Whether you treat the evaluator as a component that can regress, like the retriever.",
         "Whether you know agreement statistics, not just accuracy.",
         "Whether you can name specific judge biases and the control for each."],
     "strong": [
         "A held-out human-labelled calibration set the judge is re-scored against on every "
         "judge, rubric or model change. Track Cohen's κ over time as its own metric.",
         "Compare judge–human agreement to human–human agreement. If two humans agree 70% of "
         "the time, a judge at 72% is fine and the rubric is the problem.",
         "Adversarial probes. Feed known-bad answers that are long, fluent and confidently "
         "wrong. A judge that passes them has verbosity bias.",
         "Cross-check with an independent signal — citation click-through, escalation rate.",
         "Version everything: judge model, temperature, rubric text, few-shot examples."],
     "red": "“We'd spot-check some outputs”; raw agreement on a skewed set; same model family "
            "as generator and judge with no note about self-preference.",
     "notebook": "06 — κ, the verbosity probe and the position probe are all runnable."},
]

CLOSING_LINES = [
    "Nothing downstream can recover a document the first stage never returned.",
    "Index-time compute is paid once; query-time compute is paid forever.",
    "An average is not a result until you have seen the slices underneath it.",
    "Build the measurement before the improvement, every single time.",
]
