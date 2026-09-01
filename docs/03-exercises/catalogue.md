# Exercises

Twenty-two exercises, graded by difficulty, each mapped to a notebook and to the skill an
interview panel probes. **Every exercise is submitted the same way**, and that workflow is
half the point of doing them here rather than in a scratch file.

## How to submit

```bash
git checkout -b exercise/EX-04-yourname
# work, measure, commit
python scripts/run_eval.py            # paste this into your submission
make test && make strip
git push -u origin exercise/EX-04-yourname
```

Then open an [Exercise submission issue](../../issues/new?template=exercise_submission.yml).
Faculty review the branch; the issue is where the conversation and the grade live.

> **The one rule that matters.** Every claimed improvement carries a 95% interval from
> `metrics.paired_bootstrap`. A delta inside the noise band is reported as *inside the noise
> band* — not rounded up into a win. Submissions that skip this are returned unread, because
> the habit is the thing being taught.

**Difficulty:** 🟢 warm-up · 🟡 core · 🔴 hard · ⚫ open-ended research

---

## Section 1 — Foundations

### 🟢 EX-01 · Attribute ten failures
**Notebook 01** · ~30 min · *Skill: fault isolation*

Take ten questions the baseline gets wrong. For each, run the fault-isolation tree and record
the owning stage. Produce the distribution.

**Acceptance criteria**
- A table of ten rows: qid, owning stage, the trace evidence that decided it
- The distribution as a chart
- One paragraph: given this distribution, what would you do in week one, and what would you
  explicitly *not* do?

**Stretch:** the tree's default branch fires on some cases. Explain why, and say whether the
pipeline or the rubric is at fault.

---

### 🟡 EX-02 · Find the N where the ceiling stops moving
**Notebook 01** · ~45 min · *Skill: sizing a first stage*

Sweep `n_candidates` and find the point where `Recall@N` flattens. Then argue for an operating
point using latency and cost, not just recall.

**Acceptance criteria**
- The sweep, plotted, with the chosen N marked
- The marginal recall per 100 additional candidates, as a table
- The latency cost of your choice from `costs.latency_model`
- One sentence a client would accept for why not simply N=1000

---

### 🔴 EX-03 · Break the funnel on purpose
**Notebook 01** · ~1 h · *Skill: knowing what each metric is blind to*

Construct a configuration where **answer correctness stays flat while Evidence Recall@N drops
by more than 10 points.** Then construct the reverse.

**Acceptance criteria**
- Both configurations, with numbers
- An explanation of the mechanism in each direction
- Which production symptom each corresponds to in the metric-selection matrix

---

## Section 2 — The eval set

### 🟡 EX-04 · Manufacture an eval set for a new domain
**Notebook 02** · ~2 h · *Skill: the thing clients actually need*

Add a new document family to `corpus.py` (regulatory filings, product manuals, meeting minutes
— your choice) and generate questions for it through the SEED → FILTER → MAINTAIN pipeline.

**Acceptance criteria**
- At least 20 new questions across ≥3 types, with gold evidence that resolves
  (`test_every_gold_anchor_resolves_under_the_shipped_chunking` must pass)
- The filter drop-rate per gate, reported
- At least two *planted flaws* that your filters catch, with the catch demonstrated
- Baseline metrics on the new slice, and one sentence on why they differ from the existing slices

---

### 🔴 EX-05 · Make starvation reproduce
**Notebook 02** · ~1.5 h · *Skill: reading a decision matrix as a hypothesis*

Notebook 02 fails to reproduce comparison starvation because the corpus is balanced. Make it
reproduce by deliberately unbalancing the corpus, then show the per-entity quota lever
recovering the loss.

**Acceptance criteria**
- The prevalence ratio you engineered, and the starvation it produced
- Full-chain recall before/after the quota packer, with an interval
- A statement of the condition under which a client corpus would show this

---

### 🟡 EX-06 · Null questions for a real corpus
**Notebook 02** · ~45 min · *Skill: the cheapest eval improvement there is*

Write 15 null questions for a corpus you actually work with. Not this one.

**Acceptance criteria**
- The 15 questions, each with one line on *why* the corpus cannot answer it
- Which of the four null-generation patterns each uses (absent entity, absent relation,
  absent time period, absent identifier)
- What your current system does with them

---

## Section 3 — System design

### 🟡 EX-07 · Chunking bake-off on your own corpus
**Notebook 03** · ~2 h · *Skill: choosing a strategy from corpus shape*

Run all seven strategies against a corpus of your own (or an unbalanced variant of this one).
Report recall, storage multiplier, index cost, and unresolvable gold spans.

**Acceptance criteria**
- The seven-row table
- The corpus profile that drove the decision tree, derived from measurement
- A one-paragraph recommendation naming what it costs

---

### 🔴 EX-08 · Implement a new chunking strategy
**Notebook 03** · ~2 h · Seam ① · *Skill: extending a system through its seams*

Add an eighth strategy to `chunking.STRATEGIES`. Candidates: sliding-window with sentence
alignment, proposition-level chunking, table-aware chunking, or LLM-decided boundaries.

**Acceptance criteria**
- Registered in `STRATEGIES`, produces stable chunk ids, passes `test_corpus.py`
- Measured against at least three existing strategies
- Storage and index-cost columns next to the recall column

---

### 🔴 EX-09 · Survive an encoder upgrade
**Notebook 03 + 04** · ~1.5 h · *Skill: interview Q3, executed*

Simulate an encoder swap that goes wrong in **three** different ways (mixed-version index,
prefix asymmetry, dimension truncation). For each, produce the diagnostic that identifies it.

**Acceptance criteria**
- Three broken configurations, each with the measured recall drop
- The diagnostic that isolates each, in the order a strong candidate runs them
- A runbook entry: what you would check first at 2am, and why

---

### 🔴 EX-10 · Prove permission isolation
**Notebook 03** · ~1 h · *Skill: interview Q4's "prove it" bullet*

Extend `assert_persona_isolation` into a property-based test that runs over the whole eval set
and every persona, and wire it into CI.

**Acceptance criteria**
- The test, passing, in `tests/`
- A deliberately broken configuration that the test **catches** (demonstrate the failure)
- The k-collapse measurement for the broken configuration
- A one-paragraph note on what the test does *not* cover (caches, traces, result counts)

---

## Section 4 — Retrieval methods

### 🟢 EX-11 · BM25 by hand
**Notebook 04** · ~30 min · *Skill: knowing what you are tuning*

Compute BM25 for one query against three chunks **on paper**, then verify against
`retrieve.bm25_scores`. Vary `k₁` and `b` and predict the direction before you run it.

---

### 🟡 EX-12 · The analyzer audit
**Notebook 04** · ~45 min · *Skill: the cheapest silent bug in enterprise search*

Find three more tokenizer settings that change what is searchable in this corpus. For each,
quantify the recall impact on the affected query class.

**Hint:** think about case folding, diacritics, stemming, and what happens to `v1.2.3`,
`2024-Q3`, and `ACME/Northwind`.

---

### 🔴 EX-13 · Route α by query class
**Notebook 04** · ~2 h · Seam ④ · *Skill: the honest next step after a global α*

Notebook 04 finds a single global α is a compromise. Build a router that picks α per query
class and measure whether routing beats the best global value.

**Acceptance criteria**
- The router (text-only features — **no gold labels**)
- Router precision/recall reported as its own metric
- Routed vs best-global, with an interval, on dev and on frozen
- A statement on whether the second system is worth its own maintenance

---

### 🔴 EX-14 · Beat the reranker
**Notebook 04** · ~3 h · Seam ⑤ · *Skill: fit, verify, and be honest*

Improve `ProxyCrossEncoder`. Add features, change the model class, or replace it with a real
cross-encoder if you have the dependency.

**Acceptance criteria**
- Fitted on **dev only**; frozen slice looked at once
- Evidence recall *and* full-chain recall, each with an interval
- Added latency measured, not estimated
- If your gain does not clear the noise band, **say so** — that is a passing submission

---

### ⚫ EX-15 · Make the dense leg earn its keep
**Notebook 04** · open-ended · Seam ② · *Skill: understanding why embeddings work at all*

The offline LSA encoder is the **stronger** leg here — +0.0616 evidence recall and +0.2416 nDCG
over BM25 — and fusing the two buys nothing, because 96.8% of the questions the dense leg misses
are missed by BM25 as well. Fusion pays when the legs fail on *different* queries, and these
fail together.

So the exercise is not "close a gap". It is: **make the two legs fail differently, and measure
whether fusion starts paying.** Swap in a real sentence encoder, or improve LSA without one —
better vocabulary, n-grams, term weighting, dimension routing, corpus augmentation — and then
re-run the diagnostic rather than the aggregate table.

**Acceptance criteria**
- Dense-only evidence recall, before and after, sliced by query class
- The failure overlap before and after: `python scripts/failure_overlap.py`. This is the number
  that decides the question, and it starts at 0.9684
- An explanation of the mechanism — *why* your change moved the overlap, not just the recall
- Whether fusion separates from the better single leg once it does

---

## Section 5 — Context

### 🟡 EX-16 · Price your own k
**Notebook 05** · ~1 h · *Skill: turning a knob into a purchase*

Produce the marginal-full-chain-recall-per-1k-tokens table for your own latency and cost
envelope, and mark the operating point on a frontier.

---

### 🔴 EX-17 · Measure position sensitivity for real
**Notebook 05** · ~2 h · *Skill: measuring rather than citing*

The offline reader has no position sensitivity. Point the same harness at a real model
(Bedrock or Claude) and measure the U-curve on this eval set.

**Acceptance criteria**
- The gold chunk forced into position 1, mid, and last — identical evidence set
- The spread, with an interval
- Whether edge-interleaving recovers it, measured
- Cost of the experiment, reported

---

### ⚫ EX-18 · Solve abstention
**Notebook 05 + 06** · open-ended · Seam ⑧⑨ · *Skill: the hardest open item in the repo*

No retrieval-score threshold separates answerable from unanswerable here (best F1 0.38). Build
something that does.

**Directions worth trying:** a cheap sufficiency call with a strict schema; answer-type
checking; a trained classifier over pair features; an NLI-style entailment check; a
two-stage contract where the model must name the evidence span before asserting.

**Acceptance criteria**
- Abstention precision/recall on the full null set with the real base rate
- The cost per query of your approach
- What it does to over-refusal on answerable questions — the failure nobody measures
- An honest statement of what it still gets wrong

---

## Section 6 — Evaluation

### 🟡 EX-19 · Calibrate a judge against humans
**Notebook 06** · ~2 h (needs two people) · *Skill: interview Q6*

Two people label the same 100 examples against the faithfulness rubric. Compute human–human
agreement, then judge–human agreement, then compare.

**Acceptance criteria**
- Both κ values
- The disagreements read and categorised: judge bug vs ambiguous rubric
- At least one rubric revision, with the κ before and after
- The rubric versioned and fingerprinted

---

### 🔴 EX-20 · Build a third bias probe
**Notebook 06** · ~1.5 h · *Skill: treating the evaluator as a component that regresses*

Notebook 06 probes verbosity and position. Add a probe for self-preference, scale compression,
or leniency on grounding — and make it fail on a judge you deliberately weaken.

---

## Sections 7–8 — Cost and agents

### 🟡 EX-21 · Cost model for a real client shape
**Notebook 07** · ~1 h · *Skill: interview Q5*

Take a real (or realistic) traffic profile and produce the blended cost, the levers in order,
and the residual after the free ones. Then write the paragraph you would say to Finance,
including what you refuse to trade.

---

### ⚫ EX-22 · Fix evidence retention
**Notebook 08** · open-ended · Seam ⑥⑩ · *Skill: the metric almost nobody instruments*

Make the loop run long enough that working evidence exceeds the packing budget, measure the
retention gap, then close it — by carrying a compacted summary between turns, reserving slots
for early gold, or a better packer.

**Acceptance criteria**
- The gap, before and after
- Cost delta of the fix
- Whether the fix helps or hurts single-shot performance (it should not change it at all —
  if it does, you changed something you did not mean to)

---

## The capstone

### ⚫ CAP-01 · The build brief
**Notebook 09** · a full working session

Run the deck's build brief end to end on a corpus of your choosing: harness first, baseline,
three measured improvements, frozen-slice check, rubric self-assessment, decision record.

Post the decision record in
[Discussions → Show & Tell](../../discussions/categories/show-and-tell). It is the single most
useful artefact you will produce here — see [PORTFOLIO.md](../07-career/portfolio.md) for why it is also
the one to put in front of an interviewer.

---

## Difficulty index

| ID | Title | Level | Notebook | Seam | Interview link |
|---|---|---|---|---|---|
| EX-01 | Attribute ten failures | 🟢 | 01 | — | Q1 scoping |
| EX-02 | Find the N where the ceiling flattens | 🟡 | 01 | ③ | sizing |
| EX-03 | Break the funnel on purpose | 🔴 | 01 | — | metric selection |
| EX-04 | Manufacture an eval set | 🟡 | 02 | ① | Q1, eval-set design |
| EX-05 | Make starvation reproduce | 🔴 | 02 | ⑥ | reading a matrix |
| EX-06 | Null questions for a real corpus | 🟡 | 02 | — | abstention |
| EX-07 | Chunking bake-off | 🟡 | 03 | ① | chunk sizing |
| EX-08 | New chunking strategy | 🔴 | 03 | ① | extension |
| EX-09 | Survive an encoder upgrade | 🔴 | 03+04 | ② | **Q3 debugging** |
| EX-10 | Prove permission isolation | 🔴 | 03 | ③ | **Q4 enterprise** |
| EX-11 | BM25 by hand | 🟢 | 04 | — | fundamentals |
| EX-12 | The analyzer audit | 🟡 | 04 | ③ | silent bugs |
| EX-13 | Route α by query class | 🔴 | 04 | ④ | Q2 segments |
| EX-14 | Beat the reranker | 🔴 | 04 | ⑤ | fit/verify |
| EX-15 | Make the dense leg earn its keep | ⚫ | 04 | ② | encoder choice |
| EX-16 | Price your own k | 🟡 | 05 | ⑥ | budgets |
| EX-17 | Measure position sensitivity | 🔴 | 05 | ⑦ | measuring vs citing |
| EX-18 | Solve abstention | ⚫ | 05+06 | ⑧⑨ | **the open problem** |
| EX-19 | Calibrate a judge | 🟡 | 06 | ⑨ | **Q6 epistemics** |
| EX-20 | A third bias probe | 🔴 | 06 | ⑨ | Q6 |
| EX-21 | Cost model for a client | 🟡 | 07 | — | **Q5 economics** |
| EX-22 | Fix evidence retention | ⚫ | 08 | ⑥⑩ | agent evaluation |
| CAP-01 | The build brief | ⚫ | 09 | all | the whole panel |
