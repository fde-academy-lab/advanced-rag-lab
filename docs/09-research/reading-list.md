# Reading list

Papers and posts behind each section, **with what to look for in each** — because a reading
assignment without a reason is an assignment nobody does.

> Links are to arXiv or the publisher where possible. Where a source is a company engineering
> blog, treat reported numbers as reported: they are real results on their corpus, not
> benchmarks you should expect to reproduce.

---

## §1 — Foundations

**Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (2020)** ·
[arXiv:2005.11401](https://arxiv.org/abs/2005.11401)
The paper that named the pattern. *Look for:* the distinction between RAG-Sequence and
RAG-Token, and note how little of the modern stack this describes — the interesting engineering
all arrived later.

**Anthropic, "Introducing Contextual Retrieval" (2024)** ·
[anthropic.com/news/contextual-retrieval](https://www.anthropic.com/news/contextual-retrieval)
*Look for:* where the fix lives. It is at index time, and prompt caching is what made it
affordable. Also note that they kept BM25 — a widely-cited "dense is enough" assumption did not
survive contact with identifiers.

---

## §2 — The eval set

**Tang & Yang, "MultiHop-RAG" (COLM 2024)** ·
[arXiv:2401.15391](https://arxiv.org/abs/2401.15391)
The dataset this repo's corpus is shaped after. *Look for:* the record schema, and why
`evidence_list` is the field that makes retrieval measurable. Ask yourself what you could
*not* measure without it.

**Es et al., "RAGAS: Automated Evaluation of Retrieval Augmented Generation" (2023)** ·
[arXiv:2309.15217](https://arxiv.org/abs/2309.15217)
*Look for:* the reference-free metrics, and then think hard about what "reference-free" is
buying and costing you. Convenient, and it moves the ground truth into a model.

---

## §3 — System design

**Karpukhin et al., "Dense Passage Retrieval" (2020)** ·
[arXiv:2004.04906](https://arxiv.org/abs/2004.04906)
*Look for:* the bi-encoder architecture and in-batch negatives. The asymmetry between document
encoding (offline, batched) and query encoding (online) is the thing that makes dense retrieval
affordable at all.

**LinkedIn, "Retrieval-Augmented Generation with Knowledge Graphs for Customer Service"
(2024)** · [arXiv:2404.17723](https://arxiv.org/abs/2404.17723)
*Look for:* the reframing. They did not change the retrieval algorithm, they changed what a
retrievable unit *is*. Ask what the natural retrievable unit of your own corpus is.

---

## §4 — Retrieval methods

**Robertson & Zaragoza, "The Probabilistic Relevance Framework: BM25 and Beyond" (2009)** ·
[DOI:10.1561/1500000019](https://doi.org/10.1561/1500000019)
*Look for:* what `k₁` and `b` actually do. Read §3 and then go and change them in notebook 04
and predict the direction before you run it.

**Malkov & Yashunin, "Efficient and robust approximate nearest neighbor search using HNSW"
(2016)** · [arXiv:1603.09320](https://arxiv.org/abs/1603.09320)
*Look for:* why the hierarchy exists. A flat k-NN graph is not navigable — the long-range links
are the whole trick, and notebook 04's ANN section demonstrates what happens without them.

**Khattab & Zaharia, "ColBERT: Efficient and Effective Passage Search via Contextualized Late
Interaction" (2020)** · [arXiv:2004.12832](https://arxiv.org/abs/2004.12832)
*Look for:* the storage multiplier. Late interaction trades storage for latency, and the trade
is 10–100×.

**Cormack et al., "Reciprocal Rank Fusion outperforms Condorcet and individual rank learning
methods" (2009)** · [DOI:10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114)
*Look for:* why rank-based fusion is robust — and then read notebook 04's finding that
equal-weight RRF lost to BM25 alone on our corpus, and work out why both things are true.

---

## §5 — Context

**Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (2023)** ·
[arXiv:2307.03172](https://arxiv.org/abs/2307.03172)
*Look for:* the U-shape, and then note that the magnitude varies by model and task. This is a
paper to *replicate on your own eval set*, not to cite. EX-17.

**Anthropic, "Prompt caching" documentation** ·
[docs.anthropic.com](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
*Look for:* the byte-identity rule for the cached prefix, the two retention windows and their
write multipliers. Notebook 07 prices all of it.

---

## §6 — Evaluation

**Zheng et al., "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena" (2023)** ·
[arXiv:2306.05685](https://arxiv.org/abs/2306.05685)
*Look for:* position bias, verbosity bias and self-enhancement bias — and the controls for
each. Notebook 06 implements probes for two of the three.

**Cohen, "A Coefficient of Agreement for Nominal Scales" (1960)** ·
[DOI:10.1177/001316446002000104](https://doi.org/10.1177/001316446002000104)
*Look for:* why chance-corrected agreement exists. On a skewed set, a judge that always says
"pass" scores 90% raw accuracy. That single fact is why κ is in the release gate.

**Efron & Tibshirani, "An Introduction to the Bootstrap" (1993)**, ch. 6
*Look for:* why *paired* resampling detects smaller true differences than independent samples.
This is the statistical backbone of every delta reported in this repo.

---

## §7 — Cost

**OpenAI, "Prompt caching" model guidance** ·
[platform.openai.com/docs](https://platform.openai.com/docs/guides/prompt-caching)
*Look for:* the counters to monitor. Whether reuse offsets write cost is an empirical question
per workload, not a rule.

---

## §8 — Agents

**Yao et al., "ReAct: Synergizing Reasoning and Acting in Language Models" (2022)** ·
[arXiv:2210.03629](https://arxiv.org/abs/2210.03629)
*Look for:* the interleaving of thought and action, and then ask where the *stop condition*
lives. It is the part the paper spends least time on and production spends most.

**Asai et al., "Self-RAG: Learning to Retrieve, Generate, and Critique through
Self-Reflection" (2023)** · [arXiv:2310.11511](https://arxiv.org/abs/2310.11511)
*Look for:* the critique tokens. This is the most promising direction for the abstention
problem this repo leaves open (EX-18).

**Yan et al., "Corrective Retrieval Augmented Generation" (2024)** ·
[arXiv:2401.15884](https://arxiv.org/abs/2401.15884)
*Look for:* the retrieval evaluator that decides correct / incorrect / ambiguous. Compare its
job to our `sufficiency_check` and note what ours cannot do.

---

## Cross-cutting

**Shah & Bender, "Situating Search" (2022)** ·
[DOI:10.1145/3498366.3505816](https://doi.org/10.1145/3498366.3505816)
*Look for:* the argument against replacing search with generated answers. Read it even if — 
especially if — you disagree. Being able to state the strongest version of the objection to
your own product is the skill this whole repository is about.

**Google, "Machine Learning: The High-Interest Credit Card of Technical Debt" (2014)** ·
[NeurIPS](https://papers.nips.cc/paper/2015/hash/86df7dcfd896fcaf2674f757a2463eba-Abstract.html)
*Look for:* "entanglement" and "undeclared consumers". Both describe exactly what happens when
someone changes your chunking and every downstream BM25 score moves.

---

## How faculty assign these

Reading assignments are published as issues with the `type: reading` and `cohort` labels, using
the [reading assignment template](../../.github/ISSUE_TEMPLATE/reading_assignment.yml). Each one
names 2–3 required readings **with what to look for**, and 2–4 questions students answer as
comments. Those comment threads become the seminar agenda — so a student who has not read
cannot free-ride on the discussion.
