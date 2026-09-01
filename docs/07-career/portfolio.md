# Putting this on your CV, LinkedIn and GitHub

A guide to presenting this work so that a recruiter screening 200 CVs stops, and an engineer
who opens the repo in an interview finds what they are looking for in ninety seconds.

> **The honesty rule, first.** Claim what you did, not what the repo does. If you completed
> four exercises and the capstone, say that. A fabricated claim survives the CV screen and dies
> in the interview, taking your credibility with it — and interviewers in this field
> *will* ask you to walk through a commit. Everything below is written so that the truthful
> version is also the impressive version.

---

## What actually differentiates you

Most candidates for retrieval/RAG roles have built a demo: a vector store, a prompt, an answer.
The hiring signal is not "can you build RAG" — that has been commoditised. It is these four,
and this project produces evidence of all of them:

| What panels are short of | Evidence you can point at |
|---|---|
| Someone who **measures** rather than asserts | A results ledger with 95% intervals; a noise band computed before any change |
| Someone who knows **which stage owns a failure** | A fault-isolation procedure run over a failure set, producing a work plan |
| Someone who states the **cost of their own recommendation** | A decision record naming what was rejected and why; a cost/quality frontier |
| Someone who has thought about **enterprise constraints** | Pre-filtered ACL retrieval with a persona-isolation test in CI |

Notice that none of those is a technology. Do not lead with "Python, FAISS, LangChain."

---

## The CV

### The bullets

Use **three to five** bullets, each with a number and a mechanism. Pick from these based on
what you actually did:

> **Advanced RAG — Retrieval, Evaluation & Cost Engineering** · [github.com/…/raglab](../../)
>
> - Built a retrieval stack (BM25 over FTS5, LSA dense retrieval, weighted hybrid fusion, a
>   learned cross-encoder reranker) with an evaluation harness that reports **evidence recall,
>   full-chain recall and abstention with 95% bootstrap intervals** — raising full-chain recall
>   0.33 → 0.47 while proving two of four candidate changes were inside the noise band.
> - Implemented a navigable small-world ANN index and **measured the recall/`efSearch`
>   tradeoff against exact search**, showing recall collapse from 1.00 to 0.10 at low visit
>   budgets and quantifying the additional degradation under selective ACL pre-filters.
> - Designed permission-aware retrieval that **pre-filters the ACL predicate into the query**,
>   demonstrating that post-filtering collapses `k` from 8 to 0 for narrowly-scoped users; wrote
>   a two-persona isolation test that runs in CI.
> - Built an LLM-judge calibration loop (Cohen's κ, verbosity and position bias probes) and
>   showed a **single rubric parameter moving the headline quality number across a range wider
>   than most releases** — judge drift with no system change.
> - Shipped an evaluation **release gate as a GitHub Action** that blocks a merge on a metric
>   regression beyond tolerance and posts the scorecard on the PR.

**Why these work:** each has a verb, a mechanism and a number, and three of the five report a
*negative* or a *limit* — which is what makes the positive claims believable.

### The one-liner, if you only get one

> Built and measured a full retrieval/RAG stack end to end — hybrid retrieval, learned
> reranking, ACL-aware pre-filtering, LLM-judge calibration and a CI release gate — with every
> improvement reported against a measured noise band.

### Skills section

Group by capability, not by library. Recruiters keyword-match; engineers read the grouping.

```
Retrieval    BM25/inverted indexes · dense retrieval · ANN (HNSW/NSW) · hybrid fusion (RRF,
             weighted) · cross-encoder and late-interaction reranking · chunking strategies
Evaluation   Evidence/full-chain recall · nDCG · MRR · LLM-as-judge calibration (Cohen's κ) ·
             paired bootstrap · abstention scoring · release gating
Systems      Index freshness (CDC, blue/green, tombstones) · permission-aware retrieval ·
             prompt caching and token economics · trace-based debugging
Cloud/LLM    AWS Bedrock (Knowledge Bases, Titan embeddings, rerank, Converse) · Claude API
Engineering  Python · SQLite/FTS5 · NumPy · pytest · GitHub Actions · Jupyter
```

---

## LinkedIn

### The Featured section

Pin the repo, and pin the **executed notebooks page** (GitHub Pages) if you have enabled it —
a recruiter will click a rendered notebook and will not clone a repo.

### The project entry

**Title:** `Advanced RAG — Retrieval, Evaluation & Cost Engineering`

**Description (LinkedIn truncates around 200 characters, so front-load):**

> Retrieval stack + evaluation harness where every improvement is reported with a 95% interval
> against a measured noise band. Hybrid retrieval, learned reranking, ACL-aware pre-filtering,
> judge calibration, and a CI gate that blocks merges on metric regressions.

### A post that gets read

Posts that perform are specific and slightly counter-intuitive. Do not post "I built a RAG
project 🚀". Post a finding.

> **Three things I measured on a RAG system that contradicted what I expected.**
>
> **1. Equal-weight RRF was worse than BM25 alone.** Fusing a strong retriever with a weak one
> at equal weight moves you toward the weak one. Weighted fusion at α=0.2 beat both. The folk
> rule "always hybrid" hides a tuning decision.
>
> **2. No retrieval-score threshold could separate answerable from unanswerable questions**
> (best F1 0.38). The reason turned out to be visible in the questions rather than the scores:
> unanswerable questions named real entities in the corpus's own vocabulary, while real user
> questions paraphrase — so the unanswerable ones were *lexically closer* to the corpus.
> Abstention is an entailment problem, not a similarity problem.
>
> **3. Two of my four "improvements" were inside the noise band.** I measured run-to-run
> variance with a paired bootstrap before changing anything. Without that number I would have
> shipped both and reported a win.
>
> Full write-up, runnable notebooks and the decision record: [link]
>
> #RAG #InformationRetrieval #MLEngineering #Evaluation

**Why this works:** it demonstrates measurement discipline and intellectual honesty in a
format people share, and the third point is the one hiring managers screenshot.

---

## The GitHub profile

1. **Pin the repo.** Make sure the About section has the description, topics
   (`rag`, `retrieval`, `information-retrieval`, `evaluation`, `bm25`, `reranking`, `bedrock`,
   `llm-evaluation`), and the website link.
2. **A green CI badge is a hiring signal.** It says the thing runs, which is not true of most
   portfolio repos.
3. **Your commit history is read.** Small, well-described commits that reference issues look
   like someone who has worked on a team. `wip`, `fix`, `stuff` do not.
4. **The decision record is the artefact to be proud of**, more than any code. Very few
   candidates have one.

---

## In the interview

### The 90-second walkthrough

Rehearse this. You will get roughly this long before they interrupt with a question, and
being interrupted with a *good* question means it worked.

> "It's a retrieval stack that runs entirely in memory so the whole thing is reproducible —
> SQLite FTS5 for the lexical leg, a dense leg, hybrid fusion, and a reranker I fit on a dev
> slice and verify on a frozen slice I only look at once.
>
> The part I'd actually want to show you is the measurement layer. Every change reports a 95%
> paired-bootstrap interval against a noise band I measured before I started, and two of my
> four candidate improvements turned out to be inside that band — so they're in the decision
> record as rejected rather than shipped.
>
> The one that surprised me most: I couldn't find any retrieval-side signal that separated
> answerable from unanswerable questions. Best F1 was 0.38. Turned out my null questions named
> real entities in the corpus's vocabulary while the real questions paraphrased — so the
> unanswerable ones were lexically *closer*. That's when it clicked that abstention is an
> entailment problem and belongs in the generation contract, not in a threshold."

Three things that does: leads with the measurement rather than the tech, volunteers a negative
result, and ends on a mechanism you understood rather than a feature you built.

### Have these three open in tabs

| Tab | Why |
|---|---|
| The **decision record** (notebook 09) | Answers "what did you ship and why" in one screen |
| The **ANN recall curve** (notebook 04 §4.6) | A real measurement with a real tradeoff, easy to discuss |
| The **eval gate workflow** + a PR with its scorecard | Shows you have worked the way a team works |

### Questions you will get about this project

**"Isn't the corpus synthetic? Doesn't that invalidate the results?"**
> It's generated from a fact graph, which means gold evidence is true by construction — there's
> no annotation-error floor under any number. That's a *feature* for teaching measurement.
> What it costs is external validity: the absolute values don't transfer, and the README says
> so explicitly. The record schema matches MultiHop-RAG so the real dataset drops in
> unchanged, and I'd expect the shape of the findings to hold and the values to move.

**"Your embedding model is LSA. Why not a real encoder?"**
> Because the whole thing had to run offline and deterministically in ten seconds — that
> constraint is what makes the measurement curriculum work. LSA is genuine dense retrieval and
> it's honestly weaker than a modern encoder, which the README states in an explicit
> real-vs-stand-in table. The interface is swappable; `SentenceTransformersEmbedder` and
> `BedrockEmbedder` are both implemented. And the weakness produced a real lesson: it's *why*
> equal-weight RRF lost to BM25 here.

**"What would you do differently?"**
> Two things. The eval set is 243 questions and the noise band on full-chain recall is ±0.06 —
> several of my deltas sit inside it. Doubling the set is the cheapest way to make those
> decisions decidable and it costs less than any of the engineering. And abstention is
> genuinely unsolved in the repo; I know the direction — a sufficiency call with a strict
> schema — but I have not measured it yet.

**"Walk me through a commit."**
> Pick one where you measured something and it did not work. Those are the ones that make
> interviewers relax, because they signal you will tell them the truth when it matters.

---

## Where the evidence lives

| Claim | Where an interviewer can verify it |
|---|---|
| Measurement discipline | `notebooks/09_capstone_build.ipynb` — ledger, intervals, decision record |
| Retrieval depth | `notebooks/04_…` — BM25 from scratch, ANN curve, fusion sweep |
| Enterprise thinking | `notebooks/03_…` §3.7 + `tests/test_retrieval.py` |
| Evaluation rigour | `notebooks/06_…` — κ, bias probes, judge drift |
| Cost engineering | `notebooks/07_…` — four cache killers, priced |
| Engineering practice | `.github/workflows/eval-regression.yml`, the PR template, `tests/` |
| Communication | `docs/01-architecture/overview.md`, the ADRs, and this document |

---

## A last word on honesty

The strongest thing in this repository is not any technique. It is that it reports three
findings that contradict the expected answer, and it explains the mechanism rather than tuning
them away.

Carry that into the interview. When you are asked what your project achieved, the sentence that
separates you from the field is not a bigger number — it is:

> *"Two of the four changes I tried were inside the noise band, and they're recorded as
> rejected."*

Almost nobody says that. Everybody who hires for this work is looking for the person who does.
