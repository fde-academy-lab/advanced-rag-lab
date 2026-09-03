"""Exercise threads: brief, approach, submission, peer review, correction, accepted answer.

Every number quoted is one this repository actually produces. Invented benchmark figures are
worse than none — they teach a reader to trust the shape of a claim rather than its provenance.
"""
from __future__ import annotations

CAT = "Exercises & Submissions"

THREADS = [
{
 "category": CAT, "author": "maintainer",
 "title": "EX-01 · Establish the baseline you are allowed to argue with",
 "body": """**Difficulty** ★☆☆☆☆ · **Seam** ① retriever · **Time** 45 min · **Notebook** `01`

### Setup
`raglab.quickstart()` gives you a corpus of 484 documents, 2,430 chunks and a 243-question
eval set with a frozen 15% slice. Nothing is tuned.

### Task
Produce the baseline table. BM25 alone, dense alone, and the two fused with equal-weight RRF,
each at k = 5, 8 and 10. Report Evidence Recall, full-chain recall and context precision.

### Acceptance
- Nine rows, three metrics each.
- A paired bootstrap interval on every comparison you draw a conclusion from.
- One sentence naming which comparison you cannot draw a conclusion from, and why.

### The trap
You will be tempted to report the configuration that scored highest and call it the baseline.
A baseline is not the best configuration — it is the **honest, untuned** one you will later
have to beat. Pick it before you see the numbers, and say in your reply which you picked and
when you decided.

Reply with your **approach first**. Code after.""",
 "replies": [
  {"by": "dan", "body": """**Approach.** Run `quickstart()` three times with `fusion=` set to
`bm25`, `dense`, `rrf` and loop k over (5, 8, 10). Collect into a dataframe, call
`metrics.paired_bootstrap` on each pair.

I'll take **BM25 at k=8** as the baseline, decided now, before running anything — it is the
configuration with the fewest moving parts, and k=8 is what the context budget actually allows
(notebook 05 shows 8 chunks × ~300 tokens fits alongside the prompt and answer).

Expectation: RRF beats both single legs. That is what every hybrid-search post says."""},
  {"by": "priya", "body": """Your approach is right but there is a bug waiting for you in the
loop. `quickstart()` refits the LSA embedder every call — that is ~40 s each time and, worse,
the latent space is re-derived, so your dense numbers will move slightly between runs for
reasons that have nothing to do with k.

Build the index once and vary only the retrieval config:

```python
bundle, idx, pipe = raglab.quickstart(verbose=False)
for fusion in ("bm25", "dense", "rrf"):
    for k in (5, 8, 10):
        pipe.cfg = retrieve.RetrievalConfig(n_candidates=100, k=k, fusion=fusion)
        ...
```

Otherwise you are measuring the embedder's seed as well as the retriever."""},
  {"by": "dan", "body": """That was exactly it — thank you. Rebuilt with one index. Results,
all at rerank=cross:

| fusion | k | evidence_recall | full_chain | ctx_precision |
|---|---|---|---|---|
| bm25 | 5 | 0.6329 | 0.3188 | 0.3029 |
| bm25 | 8 | 0.7118 | 0.4348 | 0.2309 |
| bm25 | 10 | 0.7279 | 0.4589 | 0.1948 |
| rrf | 8 | **0.7742** | 0.4638 | 0.2469 |

`bm25 -> rrf` at k=8 is **+0.0624**, ci (+0.0407, +0.0857) — real.

Baseline stands as declared: **BM25, k=8, evidence recall 0.7118.** RRF beats it, which is what
I expected, and I am recording the baseline as the untuned one rather than the winner.

**What surprised me.** Nothing yet, which is making me suspicious."""},
  {"by": "wei", "body": """Nothing surprising because nothing was tested. You have confirmed
what every hybrid-search post says, which is the least informative outcome available — if the
experiment can only come back one way, it is not an experiment.

Also: the brief asked for **dense alone** and you have not reported it. Three of your nine rows
are missing and they are the three that matter."""},
  {"by": "marcus", "body": """Wei is right about the missing rows but I think the mechanism is
already clear. RRF is a **voting rule that treats both voters as equally credible**, and our
dense leg is LSA — a truncated SVD over TF-IDF, fifty years old. It is obviously the weak leg
here. What Dan has measured is fusion succeeding *despite* a weak second voter, because k=60
dampens how much any single top hit counts.

Dan, I would predict dense alone lands well below BM25, somewhere around 0.55–0.62. Worth
running to close it out but I do not think it changes the conclusion."""},
  {"by": "dan", "body": """Ran it. Marcus, this is not what either of us expected:

| fusion | k | evidence_recall | ndcg |
|---|---|---|---|
| bm25 | 8 | 0.7118 | 0.3639 |
| **dense** | 8 | **0.7733** | **0.6055** |
| rrf | 8 | 0.7742 | 0.5302 |

The dense leg **beats BM25** — +0.0616 evidence recall, ci (+0.0382, +0.0870) — and it beats
everything on nDCG including the fused system.

`dense -> rrf` is **+0.0008**, ci (−0.0101, +0.0109). Inside the noise band.

So the sentence in my last reply — "RRF beats it, which is what I expected" — was true and
useless. RRF beats the leg I happened to compare it against. It does not beat the *better* leg,
and on ranking quality it is worse than that leg on its own."""},
  {"by": "priya", "body": """This is the answer to the brief's third acceptance criterion, and
it is worth stating precisely because it is easy to say loosely.

**The comparison you cannot draw a conclusion from is `dense` vs `rrf`.** +0.0008 with an
interval of (−0.0101, +0.0109) is not a small difference. It is *not a difference*. Reporting it
as "RRF is slightly ahead" would be reporting the sign of noise.

And the consequence is a decision, not a footnote. Shipping RRF over dense-alone means a second
index, a second retrieval path and a fusion rule in the query hot path, bought with a number
whose interval contains zero. The dense leg alone is a simpler system that measures the same.

Marcus's mechanism is the standard one and it is not what happened here. The condition for
fusion to pay is not "comparable leg strength" — it is **complementarity**: the legs have to
fail on *different* queries. Two retrievers that fail together carry one signal between them.
Cormack's RRF paper fuses TREC runs, which are mature systems that are good in *different ways*;
that property is doing more work in the paper than the equal-weighting is.

Nobody in this thread ran the check that would have settled it in advance: the per-query overlap
of the two legs' failures. Disjoint failures, fusion is worth a lot. Nested failures, worth
nothing. It is one line of pandas and it is the measurement the aggregate table cannot
substitute for.""", "accepted": True},
  {"by": "marcus", "body": """Yes — I had the mechanism from the literature and applied it
without checking the premise it rests on. "LSA is old, therefore LSA is the weak leg" is not an
argument, it is a vibe with a date on it.

The reason it is the *stronger* leg here is the corpus: Client Zero's questions are paraphrase
and inference over incident prose, where the question and the passage share meaning and almost
no vocabulary. BM25 scores term overlap; there is very little for it to score. Where BM25 does
win is exact identifiers — `PagerDuty-4471`, `ap-southeast-2` — which are out-of-vocabulary for
a latent model. That slice is real and small, and the aggregate hides it in both directions."""},
  {"by": "maintainer", "body": """Marked Priya's reply as the answer.

Four things this thread did right, for anyone reading it later. Dan declared the baseline
**before** seeing the numbers. Priya caught a methodology bug at the approach stage rather than
after a week of work. Wei was blunt and correct about the missing rows — three of nine, and the
three that decide the question. And Marcus was wrong in the most useful way available: he
brought the textbook mechanism, predicted a number, and the prediction was refutable.

The general lesson is the one Dan wrote himself: **"RRF beats it" is true and useless if "it" is
not the strongest alternative.** A comparison against a weak baseline confirms nothing, and it
is the most common shape of a result that survives review and should not have.

One piece of history, because you will find the old version in course material that predates
this thread. This repository previously published the *opposite* finding — "equal-weight RRF
loses to BM25 alone", with a mechanism about fusing strong legs with weak ones. It was wrong, it
was quoted in about twenty places, and it stood for months. What let it survive is structural:
the eval gate compares one configuration against its own history and never against alternatives,
so nothing in the system was capable of noticing. The retraction is
[ADR-0015](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
and the fix is `python scripts/run_eval.py --compare`, which is one command precisely because a
claim you cannot re-run is a claim nobody will re-run.

This is the first of the findings in this repository that contradict the received wisdom. You
will meet the others in EX-09 and EX-14."""},
 ],
},
{
 "category": CAT, "author": "maintainer",
 "title": "EX-02 · Break the tokenizer on purpose",
 "body": """**Difficulty** ★★☆☆☆ · **Seam** ② index · **Time** 1 h · **Notebook** `01`, `04`

### Setup
The corpus contains incident reports full of identifiers: `ERR_CONN_RESET`,
`ERR_TLS_HANDSHAKE`, `SVC-4471`. The eval set has a slice of queries that name them directly.

### Task
Rebuild the FTS5 index with the **default** `unicode61` tokenizer — that is, delete the
`tokenchars '_-'` argument in `store.py` — and measure what happens to the identifier slice
specifically, not to the overall average.

### Acceptance
- Recall on the identifier slice, before and after, with an interval.
- The overall average, before and after.
- An explanation of why those two numbers move by very different amounts.

### The trap
Reporting the overall average only. The whole point of this exercise is that the average barely
moves while a slice you care about collapses — and if you only look at the average you will ship
this bug, which is precisely what happened here (issue #1).""",
 "replies": [
  {"by": "sofia", "body": """**Approach.** Patch the tokenizer string, rebuild, and split the
eval set into `identifier` and `everything else` using the question metadata. Expect the
identifier slice to drop hard and the average to drop by roughly (slice size / total) × that
amount.

Prediction before running: identifier slice loses 20–30 points, overall average loses 3–4."""},
  {"by": "sofia", "body": """Ran it.

| slice | with `tokenchars '_-'` | default unicode61 | Δ |
|---|---|---|---|
| identifier queries | 0.81 | 0.34 | **−0.47** |
| everything else | 0.76 | 0.76 | −0.00 |
| **overall average** | 0.7645 | 0.7104 | −0.054 |

Under-predicted the slice damage badly. The mechanism is worse than "the token is split":
`ERR_CONN_RESET` becomes `err` / `conn` / `reset`, and all three are *common words in this
corpus* — every incident report contains them. So the identifier does not merely fail to match,
it matches **everything**, and BM25's IDF term rates all three as low-information. You have
turned a high-precision query into a high-recall one.

The 5-point average drop is the kind of number that gets waved through in a review."""},
  {"by": "tomas", "body": """This is the part that should worry people operationally. A 5-point
average regression looks like noise on a dashboard. The user-visible symptom is "search is
broken for error codes", which is the highest-urgency query class you have, and no aggregate
metric would have paged anyone.

Two things follow. Slice-level alerting, not just aggregate. And the tokenizer belongs in the
index version string, so a tokenizer change forces a reindex rather than silently producing a
corpus that is half one scheme and half the other.""", "accepted": True},
  {"by": "lena", "body": """Worth adding the general principle: this is a **vocabulary mismatch**
between the analyzer at index time and the analyzer at query time, and it is the oldest bug in
information retrieval. Any change to the analyzer chain — stemming, case folding, diacritic
removal, tokenization — silently invalidates every document indexed before it.

The literature's standard answer is to store the analyzer configuration as part of the index
identity, which is exactly what Tomás just described. `store.py` already does that with
`embedder_tag`; the tokenizer should be in the same string."""},
  {"by": "maintainer", "body": """Answer marked. This exercise exists because it is real: it is
issue #1, and it was found by a failing slice rather than by anyone reading the schema.

The comment above the FTS5 table in `store.py` is deliberately long for this reason. It is not
documenting the syntax, it is documenting the *reason*, so that the next person to touch that
line knows what they are choosing between."""},
 ],
},
{
 "category": CAT, "author": "maintainer",
 "title": "EX-09 · Try to reproduce comparison starvation, and fail",
 "body": """**Difficulty** ★★★☆☆ · **Seam** ① retriever, ⑦ eval · **Time** 2 h · **Notebook** `02`

### Setup
"Comparison starvation" is the claim that when a question compares two entities, retrieval
returns evidence for the more-prevalent one and starves the other, so the answer is confidently
half-supported.

### Task
Build a comparison slice from the eval set and test the claim. Measure per-entity evidence
recall within each comparison question, not just whether the question was answered.

### Acceptance
- The prevalence ratio between the two entities in each comparison pair.
- Per-entity recall, and the gap between them.
- A verdict, with an interval.

### The trap
This is a **negative-result exercise**. If you find the effect, check your slice construction
before you believe it. Full credit is available for a clean refutation with a mechanism, and
that is the likelier outcome here.""",
 "replies": [
  {"by": "lena", "body": """**Approach.** Liu et al. and the long-context literature motivate
this, but the cleanest formulation is from the multi-hop QA work: the retriever optimises a
single relevance score against the query as a whole, so an entity that is rarer in the corpus
contributes less to that score and gets fewer slots in the top-k.

I'll compute prevalence per entity, bucket comparison questions by prevalence ratio, and look
for a correlation between the ratio and the recall gap. Expect a clear positive correlation."""},
  {"by": "lena", "body": """**It does not reproduce.** Prevalence ratio across comparison pairs
in this corpus is ≈ 1.0 — the two entities in any given comparison appear about equally often.
There is no starvation because there is no imbalance to starve on.

Recall gap between the two entities: indistinguishable from zero, interval spanning it.

I checked whether I had built the slice wrong. I had not. The corpus is generated from a fact
graph that emits organisations on a balanced schedule — 24 orgs across 6 quarters — so entity
prevalence is uniform *by construction*."""},
  {"by": "aarav", "body": """So the finding is "our synthetic corpus does not have the property
that causes the problem". That is a limitation of the corpus, not a result about retrieval, and
I would not put it in front of a client as either."""},
  {"by": "marcus", "body": """Half right, and the half you are missing is the useful half.

You are correct that this is not evidence that comparison starvation is false in general. It
cannot be — the corpus lacks the precondition.

But "our test set cannot exhibit the failure we are testing for" is an extremely valuable
finding about the *test set*, and it generalises: most eval sets people build are balanced by
construction, because balanced generators are easier to write. So a whole class of real
failures is invisible to them, and everyone concludes the failure is rare.

The actionable output is not "starvation is a myth". It is: **an eval set built by a balanced
generator cannot measure imbalance failures, and you must inject the imbalance deliberately.**
That is now issue #14 — an adversarial eval slice with prevalence ratios out to 20:1.""",
   "accepted": True},
  {"by": "lena", "body": """Agreed, and that reframing is the exercise. I have rewritten my
submission's conclusion as: *the effect is untestable on this corpus, the precondition is
absent by construction, and here is the corpus change that would make it testable.*

Which, now that I write it out, is a much better answer than "confirmed, r = 0.6"."""},
  {"by": "maintainer", "body": """Marked. Aarav's objection was the right objection and it is
worth reading in full rather than skipping to the correction — a result that depends on an
artefact of your test data *is* dangerous in front of a client, and someone had to say so.

Grading note: Lena's submission scores **exemplary**, not because the hypothesis was confirmed
but because it was refuted with a mechanism and converted into a concrete change to the eval
set. A clean negative result with a mechanism is full credit. This one earned more than that
because it produced work."""},
 ],
},
]
