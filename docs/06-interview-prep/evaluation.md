# Evaluation

The round that separates people who have shipped a retrieval system from people who have built
one. Everyone can describe recall. The questions below are about what happens when the number
and reality disagree — which is most of the job.

**Scoring bands:** **✗ misses** · **○ passes a screen** · **● hires at mid** · **★ hires at senior**.

---

## E1 · "Design a metric for a retrieval system whose answers can require two documents"

**Style:** Anthropic, Google, research-adjacent applied panels.

The interviewer is checking whether you notice that per-piece and per-question are different
questions before they tell you.

### Scoring

| | Signal |
|---|---|
| ✗ | Recall@k, and stops |
| ○ | Recall@k plus nDCG, mentions position matters |
| ● | Distinguishes "retrieved some evidence" from "retrieved all required evidence" |
| ★ | Defines both, predicts the gap arithmetically, and says what the gap diagnoses |

### What ★ sounds like

> "Two metrics, and the interesting thing is the distance between them.
>
> **Evidence Recall@k** — of all the gold evidence pieces, what fraction landed in the window.
> Per-piece.
>
> **Full-chain recall** — of all questions, what fraction had *every* required piece in the
> window. Per-question. This is the one that predicts whether the generator can actually answer.
>
> The interesting question is whether the gap between them is more than arithmetic. If pieces
> were retrieved independently at p, a question needing k of them clears at p^k — weighted over
> the real distribution of k, which on our corpus is half the questions needing four or more.
> That predicts 0.4603 against a measured 0.4686. We are *at* independence, so there is no
> correlated-failure structure to hunt: the gap is the arithmetic of needing four pieces at 76%
> each, and nothing else.
>
> I'd say that carefully, because we published the opposite for months — a 21-point shortfall,
> computed over hops instead of evidence pieces and against a question mixture that did not
> exist. The lesson I took is that a derived number needs a command that regenerates it, or
> nobody re-derives it.
>
> I'd report both plus the ratio, because a system that improves per-piece recall while the
> ratio falls has got worse at the thing users care about while its headline number improved."

**Follow-up:** *"Which do you gate a release on?"* — full-chain, with per-piece as a diagnostic.
Gating on the metric that can improve while the product degrades is how you ship a regression
with a green dashboard.

---

## E2 · "Your eval set says 0.89. Users are unhappy. Defend the number or abandon it."

Deliberately confrontational. The failure is defending it.

**✗:** "The metric is objective, so it's an expectations problem."

**★:**
> "I'd abandon it as the primary number until I've checked it still describes production, and
> there are four ways an eval set stops describing production.
>
> **Distribution drift.** It was built eighteen months ago from questions somebody imagined.
> Traffic is now 40% navigational and my set is all factoid. I'm measuring a distribution nobody
> sends. Fix: sample 200 real queries from logs, label them, and treat *that* as the number.
>
> **Aggregation.** 0.89 overall can be 0.95 on the easy 80% and 0.65 on the tail generating every
> complaint. Slice or you are averaging away the problem.
>
> **Metric-product mismatch.** Recall@10 is not what a user experiences. They see rank, and they
> see precision. The right document at rank 9 is a success to my metric and a failure to them.
>
> **Annotation floor.** If gold labels were assigned by someone who didn't know the domain, the
> ceiling on the metric is their accuracy, not the system's.
>
> The honest position is: 0.89 is a real number about a specific question, and the question may
> no longer be the one that matters. That is not the metric lying, it's me having stopped
> maintaining it."

---

## E3 · "Walk me through validating an LLM judge"

**Style:** Anthropic, Scale, Surge, anyone building evaluation infrastructure.

### The ★ answer

> "A judge is a model, so it needs the same treatment as any other model: a labelled set it has
> never seen, an agreement number, and a bias audit.
>
> **Agreement.** Human-label a few hundred, compute Cohen's κ, and report the marginals with it —
> κ on a skewed label distribution is brutal for reasons that have nothing to do with judge
> quality. 85% agreement can be κ = 0.17 if both raters are following an 90/10 base rate.
>
> **What the disagreement is made of** matters more than its size. κ = 0.62 with disagreement
> spread evenly is a noisy judge, and noise averages out over a few hundred examples — usable for
> a gate. κ = 0.62 with disagreement concentrated on one class, say the judge marking abstentions
> as wrong answers, is a *biased* judge, and bias does not average out. It systematically moves
> the number the gate reads. Same κ, opposite decisions.
>
> **Bias probes**, run deliberately: position bias — does it prefer the first answer when you
> swap the order? Length bias — does it prefer longer? Self-preference — does it prefer output
> from its own family? Each is a specific experiment, not a vibe.
>
> **Drift.** The judge is a hosted model that changes underneath you. I'd rerun the frozen human
> slice on a schedule and alert on the judge's disagreement with its own past self, which catches
> drift that a single κ never will.
>
> And when the κ comes back low, my first suspicion is the **rubric**, not the raters. Raters
> disagree where the instructions are silent. Publishing the confusion matrix usually shows all
> the disagreement in one cell, and that cell names the ambiguous rubric line."

---

## E4 · "How do you know an improvement is real?"

The statistics probe. See
[mathematics.md M6](mathematics.md#m6--why-a-paired-bootstrap-and-what-exactly-is-being-resampled)
for the derivation; this is the applied framing.

> "Paired bootstrap over queries, 1,000+ resamples, report the interval not just the mean.
>
> **Paired** because query difficulty varies enormously and that variance swamps the
> between-system variance I care about. Resampling the differences removes it — a query both
> systems ace contributes zero and adds no noise. Unpaired comparison on the same query set
> produces intervals several times wider, which is how a real improvement gets called
> insignificant.
>
> **Queries, not documents**, because the query is the unit of independence. Documents within one
> result list were selected by the same retriever; resampling them understates variance and gives
> intervals that are too narrow, which is the more dangerous error.
>
> Three things the bootstrap does **not** cover, and I'd say so unprompted. It assumes the gold
> labels are right — if annotation is wrong, every resample is wrong identically. It says nothing
> about multiple comparisons; test twenty variants at 95% and one clears by chance, so either
> correct for it or hold a frozen slice you touch once. And it assumes your queries represent
> production, which they usually don't.
>
> Also: significance is not the shipping criterion. An interval of [+0.001, +0.09] excludes zero
> and spans 'invisible' to 'large' — that is a reason to collect more queries, not to ship. And a
> +0.5% recall that costs 340ms p50 is a regression wearing a win's clothing."

---

## E5 · "Your metric went up. Convince me you didn't game it."

Rarely asked directly, frequently asked as *"what could have caused this that isn't real
improvement?"* Strong candidates have a list.

| Way the number moves without the product improving | How to catch it |
|---|---|
| Tuned against the test set, even once | Frozen slice, touched at the end. If it was touched, say so and treat the number as dev-only |
| k increased | Recall rises trivially with k. Report k, and report context precision alongside — it falls |
| Eval set changed in the same PR | One change per PR. This is the reason for the rule |
| Easy queries added / hard ones dropped | Per-slice counts in the report, not just per-slice scores |
| Near-duplicates in gold — retrieve one, credited for several | Dedupe gold by content hash |
| Judge changed, or its prompt changed | Version the judge and its prompt; a judge change is a metric change |
| Averaged over a different denominator (abstentions excluded) | State n explicitly on every row |

> "The structural answer is that the eval set and the system must not change in the same commit.
> If they do, the delta is uninterpretable and no amount of statistics repairs it."

---

## E6 · "You have one week and no labelled data. Go."

**Style:** consulting, forward-deployed, startup panels.

> "Day one, logs. If there's any query history, that's the highest-value thing in the building.
> Sample 200 stratified by class, label them myself — a day of my time buys a number I can trust
> more than a month of anything else.
>
> Day two to three, manufacture from the corpus. Generate questions whose answers live in known
> documents, so gold evidence is true by construction and there's no annotation-error floor. The
> trap: generated questions echo the source's wording, so lexical retrieval wins trivially and
> the set measures nothing. Paraphrase, refer to entities by descriptor rather than name, and add
> glossary documents bridging the vocabulary registers.
>
> Day four, the adversarial slice — multi-hop chains, near-duplicate distractors, and
> unanswerable questions. That last category is the one everyone skips and it is the one that
> catches the failure that costs money.
>
> Day five, check it discriminates. Run three configurations you *know* differ in quality. If
> they all score the same, the set is too easy and measures nothing — that check takes an hour
> and saves the whole exercise.
>
> Then freeze 15% and do not look at it again until the end."

---

## E7 · Rapid rounds

| # | Question | The ★ move |
|---|---|---|
| **E7** | *"MRR vs nDCG?"* | MRR is nDCG's degenerate case: one relevant document, binary. Use MRR when there's exactly one right answer (navigational). Use nDCG with graded judgements. Volunteering the expected MRR of a random ranker — $H_N/N$, ≈ 0.0075 at N=1000 — shows you know what a floor looks like |
| **E8** | *"How do you evaluate an agent?"* | On the **trace**, not just the answer. Evidence retention across steps, whether each step was justified by the previous result, whether it stopped when it had enough, and escalation rate. An agent reaching the right answer through three wrong turns will not keep doing so, and answer-only scoring cannot see that |
| **E9** | *"Precision or recall?"* | Neither in isolation — it depends on what happens downstream. With a reranker after you, recall at N is what matters and precision is the reranker's job. With a fixed context budget and no reranker, precision at k is what matters because irrelevant chunks displace relevant ones. Name the downstream stage and the question answers itself |
| **E10** | *"Abstention — how do you measure it?"* | Precision and recall of the abstention decision separately, against a set containing genuinely unanswerable questions. Then the honest finding: we could not find a retrieval-score threshold that separates answerable from unanswerable — best F1 **0.38** across four signals — because null questions name real entities in the corpus's own vocabulary while real questions paraphrase, so the unanswerable ones are lexically *closer*. Any score threshold reads a feature with the wrong sign |

---

## The thing to bring

Everything above is answerable from theory. What almost no candidate brings is a case where
they measured something and it came out **against** them, with the mechanism.

Three are available from this repository, and each has the follow-up structure interviewers
reward — a result, a mechanism, and the condition under which the expected outcome returns:

1. **Fusion does not separate from its better single leg here.** Dense alone 0.7733 against
   equal-weight RRF 0.7742 — +0.0008, ci (−0.0101, +0.0109) — and on nDCG the unfused leg wins by
   0.075. Because fusion pays only when the legs fail on *different* queries, and here they fail
   together. Returns when the legs are complementary; the diagnostic is the per-query overlap of
   failures, not the aggregate table.
2. **Comparison starvation does not reproduce.** Because the corpus is balanced by construction —
   prevalence ratio ≈ 1 — so the precondition is absent. Which is itself a finding *about eval
   sets*: a balanced generator cannot measure imbalance failures, and most generators are
   balanced because they are easier to write.
3. **No retrieval-score threshold separates answerable from unanswerable.** Best F1 0.38. Because
   the unanswerable questions are lexically closer to the corpus than the answerable ones.

4. **No retrieval configuration moves answer correctness.** Evidence recall spans 0.7118 → 0.7790
   across five configurations — real, 9.4% relative — while `answer_correct` stays inside the
   noise band on every comparison, and the best answers come from the worst retriever. The system
   is generation-limited. Returns when retrieval is the binding constraint, which is an
   assumption almost nobody checks before spending a quarter on it.

Saying "we measured that and it went the other way, here's why" is the single most credible
thing you can do in an evaluation round. It cannot be bluffed, and interviewers know it.

**There is a fifth, and it is the strongest one to have ready.** Finding 1 above previously read
*"equal-weight RRF loses to BM25 alone"*. It was wrong, it was quoted in about twenty places, and
it stood for months. What caught it was re-running the comparison; what let it stand was an eval
gate that compares one configuration against its own history and never against alternatives — so
nothing in the system was capable of noticing. The fix was a command
(`run_eval.py --compare`) and a retraction ([ADR-0015](../01-architecture/adr/0015-correct-the-fusion-finding.md)).

If you are asked *"tell me about a time you were wrong"*, this is the shape interviewers are
listening for: not a mistake and an apology, but a mistake, the structural reason it survived,
and the change that makes the class of mistake detectable. Have the mechanism ready, not the
contrition.
