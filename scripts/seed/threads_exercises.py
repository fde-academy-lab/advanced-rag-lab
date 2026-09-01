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
  {"by": "dan", "body": """That was exactly it — thank you. Rebuilt with one index. Results:

| fusion | k | evidence_recall | full_chain | ctx_precision |
|---|---|---|---|---|
| bm25 | 5 | 0.7301 | 0.4074 | 0.3512 |
| bm25 | 8 | **0.7645** | 0.4686 | 0.2433 |
| bm25 | 10 | 0.7802 | 0.4938 | 0.2031 |
| rrf | 8 | lower than bm25 at every k | | |

**RRF lost.** To BM25 alone. At every k. I re-ran it twice because I assumed I had wired the
fusion backwards.

Baseline stands as declared: BM25, k=8, evidence recall 0.7645.

**What surprised me.** All of it. I expected the hybrid to win and it is not close."""},
  {"by": "wei", "body": """You have the fusion wired backwards. In production hybrid always
beats either leg — that is the entire reason people run two retrievers. Check that your dense
leg is actually returning results and not silently falling back to an empty list; a fusion of
[good, empty] scores like a degraded version of good, which is exactly your symptom."""},
  {"by": "marcus", "body": """Wei — I checked Dan's numbers against my own run and the dense leg
is returning results. It is just weak: on its own it scores materially below BM25 on this
corpus.

This is not a bug, it is arithmetic. Equal-weight RRF is a **voting rule that treats both
voters as equally credible**. Fuse a strong leg with a weak one at equal weight and the result
moves toward the weak one. RRF's scale-invariance is a virtue when the legs are comparable and
a liability when they are not, because it discards the one signal — the score distribution —
that would have told you to down-weight the weak leg.

Dan, run it with `fusion="weighted", alpha=0.2` and you should see the expected result return.
α = 0.2 means "20% dense", which is roughly the credibility that leg has earned here.

"Hybrid always wins" is true when both legs are strong. It is a statement about a condition,
not a law.""", "accepted": True},
  {"by": "dan", "body": """`weighted, alpha=0.2` → evidence recall **0.7891**, up from 0.7645,
interval [+0.008, +0.041] so it clears the noise band. Holds on the frozen slice.

So the hybrid does win — just not at equal weight. Adding to my notes: *the fusion rule and the
fusion weight are two different decisions, and the blog posts only ever discuss the first.*"""},
  {"by": "maintainer", "body": """Marked Marcus's reply as the answer.

Three things this thread did right, for anyone reading it later. Dan declared the baseline
**before** seeing the numbers, which is the only way a baseline means anything. Priya caught a
methodology bug at the approach stage rather than after a week of work. And Wei was confidently
wrong in a completely reasonable way — "hybrid always wins" is what the literature says, and
the useful move was Marcus naming the *condition* under which it is true rather than just
saying "no".

This is the first of the three findings in this repository that contradict the received
wisdom. You will meet the other two in EX-09 and EX-14."""},
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
