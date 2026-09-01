"""Q&A threads for the questions people ask privately instead of in the category.

The existing Q&A threads answer questions about the *pipeline* — where recall goes, whether a
delta is real, which fusion rule to pick. These four answer questions about the **scorecard
itself**: what a number on it means, and why a number that looks alarming is or is not the thing
to work on next.

They are shaped that way on purpose. A student who cannot read `context_precision` correctly will
mis-prioritise every sprint after that, and the mistake is invisible because the number is right
and only the interpretation is wrong. That failure never shows up as a red test.

Each thread has a confident wrong answer in it before the correct one, because the wrong answers
here are the textbook ones. "Low precision means wasted context, so cut k" and "the system
answers questions it cannot answer, so gate on retrieval score" are both what a competent
engineer says first, and both are refuted by measurements this repository already ships.

Two of the four lean on findings this repository retracted on 2026-09-01. The retractions are
teaching material now, so they are quoted as history rather than hidden.

Every number quoted comes from `.github/eval-baseline.json`, the measurement notes under
docs/09-research/measurements/, or a brief that was read before it was cited.
"""
from __future__ import annotations

CAT = "Q&A"

THREADS = [
{
 "category": CAT, "author": "aarav",
 "title": "context_precision is 0.2433. Is three quarters of my context window wasted?",
 "body": """### The question in one line

A client asked what fraction of what we send the model is actually useful, and the scorecard
says `context_precision` 0.2433. Do I tell them 76% of the context is waste?

### What I have already tried

- Read the docstring in [raglab/metrics.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/metrics.py):
  *"share of packed chunks that carry any gold evidence. The complement is your distractor rate
  -- the slots a gold chunk could have used."* That reading supports the 76% story.
- Checked the metrics page, which says to read it as a budget-efficiency number and never as
  quality alone. That reading does not support it, and I cannot tell which one to give a client.
- Confirmed I am looking at the shipped configuration and not a sweep cell.

### The numbers

```
structural/weighted/cross/k=8 · n=243

evidence_recall     0.7645
full_chain_recall   0.4686
context_precision   0.2433
answer_correct      0.4115
```

### Where

[docs/04-evaluation/metrics.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/04-evaluation/metrics.md)

The reason I care is not academic. If it really is 76% waste then there is a cost story to tell
and a k to cut, and I would rather find that out here than in front of the client.""",
 "replies": [
  {"by": "wei", "body": """Yes, and the fix is cheap. Cut `k`.

At my last place we ran k=4 in production for about eighteen months against a support corpus and
nothing regressed that we could measure. Every extra chunk you pack is another chance for the
model to anchor on the wrong passage, and you are paying for it twice: once in tokens and once in
whatever the distractor does to the answer.

k=8 with a quarter of the slots carrying evidence means six slots doing nothing. Halve it,
re-run, and I would expect `context_precision` roughly to double with very little off the top of
recall. Then you have a real number for the client and a smaller bill."""},
  {"by": "priya", "body": """I ran that before posting a reply, because it is the obvious move
and I wanted to see the cost.

`evidence_recall` for the shipped configuration across k, reranked:

| k | evidence_recall |
|---|---|
| 3 | 0.5024 |
| 5 | 0.6490 |
| 8 | 0.7645 |
| 10 | 0.7874 |
| 20 | 0.8567 |

Going from k=8 to k=3 costs about a quarter of the evidence. That is not "very little off the
top".

The other half of it, from the BM25-alone sweep where `context_precision` is reported per k:

| k | evidence_recall | context_precision |
|---|---|---|
| 5 | 0.6329 | 0.3029 |
| 8 | 0.7118 | 0.2309 |
| 10 | 0.7279 | 0.1948 |

Those are BM25 alone so the levels differ from the shipped arm, but the shape is the point.
`context_precision` moves the opposite way to recall, monotonically, because you chose the
denominator. Cutting k does not find you more evidence. It stops counting the slots you were
using to look."""},
  {"by": "lena", "body": """Worth adding the reason the intuition is so strong here. Liu et al.
measured position sensitivity in long contexts and found accuracy sagging for evidence placed in
the middle of the packed window, which is where "distractors are actively harmful" comes from
rather than merely "distractors are wasteful".

So Wei's instinct has a paper behind it, and if that effect is live on this corpus then the 76%
is worse than waste and Aarav should absolutely be cutting k. It would also mean Priya's recall
table understates the cost of k=8, because the recall she is measuring is retrieval recall and
the reader still has to find the passage inside what you packed."""},
  {"by": "maintainer", "body": """Two good answers and one of them is measuring the wrong system.
Taking them in order, because the mechanism matters more than the verdict.

**What the metric is a statement about.** The denominator is `k`, a number you picked. The
numerator is bounded by the annotation: only chunks in `gold_map` count, so a chunk that
disambiguates an entity or rules out the wrong quarter scores as a distractor because nobody
labelled it. Same pooling caveat the metrics page attaches to nDCG. The figure therefore moves
when you change k even if retrieval is untouched, which is Priya's second table drawn out.

**Lena's paper does not apply, and it is checkable in one line.** Mean `tokens_in` on this
baseline is **884.05**, p95 **1123**. There is no window being filled and no middle for anything
to get lost in. The offline reader is extractive and has no position sensitivity at all, which is
why [EX-17](/fde-academy-lab/advanced-rag-lab/blob/main/docs/03-exercises/catalogue.md) asks you
to point the harness at a real model and *measure* the U-curve rather than cite it.

**The condition under which Wei is right,** and both halves are testable before you act. If
`tokens_in` were near your limit, packing budget is a hard constraint and k is the lever. If your
reader degraded with distractors, precision would buy correctness. The second has been measured
here: across arms spanning `evidence_recall` 0.7118 to 0.7790, every pairwise delta on
`answer_correct` sits **inside the noise band**, and the numerically best answers come from the
numerically worst retriever.

**What to tell the client.** Not "76% waste". Say that at k=8 roughly a quarter of packed slots
carry annotated gold, that the figure falls by construction as k rises, and that the cost
question is marginal recall per thousand tokens —
[EX-16](/fde-academy-lab/advanced-rag-lab/blob/main/docs/03-exercises/catalogue.md), an hour of
work, and a table a client can act on.""",
   "accepted": True},
  {"by": "aarav", "body": """Ran the k sweep against our own rate card rather than quoting
anything from here, which took about forty minutes.

What surprised me was the direction of the conversation once I stopped leading with a percentage.
"A quarter of slots carry evidence" invites "so fix it". The marginal table invites "what would
we buy with the extra tokens", and that is a question the client could actually answer, because
they know what a wrong answer costs them and I do not.

I had already drafted the slide with 76% on it. It would have been the most confident wrong
thing in the deck, and Wei's reply is exactly what I would have said if someone had pushed
back."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "The system answers all 36 unanswerable questions. Why is that not the top priority?",
 "body": """### The question in one line

`false_answers_on_null` is 36 out of 36. The system has never once said "I do not know". Why is
this sitting in the exercise catalogue rather than at the top of the roadmap?

### What I have already tried

- Checked it is not a scoring artefact. `abstention_recall` 0.0000, `abstention_f1` 0.0000,
  `over_refusals` 0. The system answers everything, including the questions built to have no
  answer in the corpus.
- Read a few of the null questions. They name real organisations and real quarters, so they look
  exactly like the answerable ones to me.
- Sliced `answer_correct` by type. null n=36 scores 0.000, which is what you would expect.

### The numbers

```
n=243 · 207 answerable · 36 null by construction

abstention_recall        0.0000
abstention_f1            0.0000
false_answers_on_null    36
over_refusals            0
answer_correct (all)     0.4115
```

### Where

[docs/04-evaluation/metrics.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/04-evaluation/metrics.md)

I am asking because everyone else seems relaxed about this and I cannot work out whether I am
missing something obvious. A confidently wrong answer to a question with no answer is the single
worst output a RAG system can produce, and this one produces it 36 times out of 36.""",
 "replies": [
  {"by": "tomas", "body": """You are not missing anything. This is the failure that generates the
3am page, and it is the only one on the scorecard where the user cannot tell they have been
harmed.

A wrong ranking gets noticed. A confident fabrication about a quarter that does not exist gets
pasted into a client email.

My view is that no further retrieval work should merge until there is a threshold in front of the
generator, even a bad one. Take the top-1 retrieval score, pick a percentile off the answerable
distribution, refuse below it. It will be crude and it will refuse some answerable questions, and
that is a better failure than the current one."""},
  {"by": "wei", "body": """Agreed with Tomás, and it is less work than it sounds.

We shipped precisely this. Top-1 cosine below a fixed cut and the assistant said it could not
find it, with a link to search. Took a sprint, and the null-answer complaints went to nearly
nothing. The distributions separate because a question about something you do not have retrieves
badly, more or less by definition.

Dan, do not overthink this one. Sweep the threshold on your answerable set, pick the knee, and
accept that you will refuse a few questions you could have answered. Ship it, then tune the cut
once you can see the complaint rate on both sides of it."""},
  {"by": "marcus", "body": """The distributions do not separate here, and it has been measured
rather than assumed. From the metrics page:

> We could not find a retrieval-score threshold separating answerable from unanswerable
> questions. Best F1 **0.38** across four signals: top-1 score, score gap between ranks 1 and 2,
> mean of top-k, and score entropy.

Four signals, including the two Tomás and Wei each proposed. There is no knee on that curve to
pick, at any percentile.

One more thing worth flagging before anyone reproduces this. The
[EX-14 brief](/fde-academy-lab/advanced-rag-lab/blob/main/docs/03-exercises/briefs/EX-14-abstention.md)
requires the PR curve over the full eval set, because subsampling moves the null base rate and
inflates precision. That already happened here once and produced a chart that contradicted its
own caption, filed as issue #7. If you sweep on a subsample you will find a threshold that looks
like it works."""},
  {"by": "maintainer", "body": """Dan's question is the right one and the answer has two halves,
because "is it important" and "is it the next thing to do" are different questions with different
answers here.

**It is important.** Nobody is relaxed about it. It is reported at 0.0000 on the front of the
scorecard rather than omitted, which is
[ADR-0007](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0007-report-negative-results.md)
applied to the most embarrassing number we have.

**The tempting fix reads a feature with the wrong sign,** and this is the part worth carrying out
of the repository. The 36 null questions name real entities *using the corpus's own vocabulary*.
The 207 genuine questions paraphrase, because the generator that built them was told to avoid the
source's wording. So the unanswerable questions are lexically **closer** to the corpus than the
answerable ones. Every threshold on retrieval score reads a signal pointing the wrong way, and
tuning does not repair an inverted sign. That is why no signal gets past F1 0.38, and the other three land nearer 0.28.

**The condition under which Wei is right, and it is not hypothetical.** In a support corpus where
users ask in the product's own vocabulary and out-of-scope questions are genuinely
out-of-vocabulary, the sign runs the other way and his threshold works as described. The sign is
a property of how your questions were written, and it is one histogram away from being known.

**What is next** is a signal about *sufficiency* rather than *similarity*: whether the evidence
entails an answer, rather than whether it resembles the question. Issue #10 and
[EX-18](/fde-academy-lab/advanced-rag-lab/blob/main/docs/03-exercises/catalogue.md), open because
it is hard.

Tomás, on the freeze: `over_refusals` is 0 because no abstention gate is switched on — `min_evidence_score` ships
off by default and the support-threshold fallback never fires on this set,
rather than a permissive one. A crude threshold moves that number up while leaving
`false_answers_on_null` near 36, which is harder to argue away than an honest zero.""",
   "accepted": True},
  {"by": "dan", "body": """I had already accepted Wei's answer before Marcus posted. Reading it
back, I did not check a single thing he said against this corpus, and it was persuasive because
it came with a shipped outcome attached.

What I actually did: plotted the top-1 score distributions for the null set against the
answerable set. They overlap almost completely and the null set sits slightly *higher*, which is
the sign inversion arriving as a picture rather than as a sentence. Twenty minutes.

The part that surprised me is that the plot is more convincing than the F1 number. 0.38 reads as
"needs tuning". Two curves sitting on top of each other with the wrong one on the right reads as
"this feature cannot work", and it is the same fact."""},
  {"by": "sofia", "body": """Adding the deployment version, because "not the top priority" is
true of the metric and not automatically true of the product.

In a regulated tenancy you can ship this system today with the abstention gap open, provided the
interface never presents an unsourced claim as an answer. Every response carries its citations,
and a response whose citations do not support it is visibly thin to the person reading it. That
is a product control rather than a model control and it does not need issue #10 solved first.

What you cannot do is put this behind an API that returns a bare string. Then the 36 become
invisible, and the control you were relying on was the citation panel nobody is rendering."""},
 ],
},
{
 "category": CAT, "author": "sofia",
 "title": "What is the difference between the macro and micro evidence recall, and which one is 0.7645?",
 "body": """### The question in one line

The independence note reports two evidence recalls, 0.7645 and 0.7257, labelled macro and micro.
The scorecard reports one. I need to label it correctly in a client-facing summary and I do not
want to guess.

### What I have already tried

- Read the implementation. `evidence_recall_at_k` returns `found / len(gold_map)` for one
  question, so per question it is a fraction of that question's pieces. What I cannot tell from
  the function is how the run aggregates across questions.
- Checked whether the two numbers are different slices rather than different aggregations. As far
  as I can tell both are the full 207 answerable questions, same configuration.

### The numbers

From [docs/09-research/measurements/multi-hop-independence.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/multi-hop-independence.md):

| | value |
|---|---|
| `evidence_recall` (macro) | 0.7645 |
| `evidence_recall` (micro) | 0.7257 |
| `full_chain_recall`, measured | 0.4686 |

### Where

[raglab/metrics.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/metrics.py) and the
independence note.

Small question, and I have been embarrassed to ask it for a fortnight because it feels like
something I should already know.""",
 "replies": [
  {"by": "lena", "body": """It is a fair question and the convention settles it.

IR practice since the TREC evaluations is that recall over a query set is pooled: you count
relevant items retrieved across the whole run and divide by relevant items in total. BEIR follows
the same convention for its recall figures. So the headline number in a scorecard is the micro
rate, and 0.7645 is the micro one.

Which would mean the independence note has the two labels the wrong way round, and that is worth
an issue rather than a discussion reply."""},
  {"by": "marcus", "body": """It is the other way round, and it is decidable from the code rather
than from convention.

```python
def evidence_recall_at_k(retrieved_ids, gold_map, k=None):
    # |gold evidence found| / |gold evidence|, counted per evidence item
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    found = sum(1 for _, cids in gold_map.items() if cids & got)
    return found / len(gold_map)
```

That returns one fraction **per question**. The run then takes the mean of those fractions, so
each question contributes one value regardless of how many pieces it needed. That is the macro
average by definition, and it is 0.7645.

The micro rate pools pieces instead: total pieces found over total pieces required, so a
six-piece question counts six times and a one-piece question counts once. It is 0.7257, and the
independence note says so in the row label and in the command that produces it
(`python scripts/independence.py --measure`).

Lena, the convention you are quoting is real, and it is a convention about document-level recall
over a query set with pooled judgements. The unit here is a piece of evidence inside a question,
and questions carry between one and six of them. The convention does not reach this case, and the
implementation is unambiguous."""},
  {"by": "dan", "body": """Taking Marcus's word for it, since he has read the code and I have
not. But does the difference actually change anything?

Both round to "about three quarters of the evidence retrieved". The gap between them is under
four points, which is smaller than the spread across the fusion arms in the other thread this
week, and nobody there treated four points as decisive. If I had hit this on my own I would have
picked whichever number was in front of me and moved on, and I suspect most people do. What am I
buying by getting the label right?"""},
  {"by": "maintainer", "body": """Dan's question is the one that makes this worth a thread, and
the answer is that the choice already changed a published finding in this repository.

**The mechanism.** Macro gives each question one vote, micro gives each *piece* one vote. They
are identical when every question needs the same number of pieces and diverge in proportion to
how uneven that distribution is. Here it is very uneven:

```
pieces of gold evidence   questions
     1                      21
     2                      59
     3                      21
     4                     100
     6                       6
```

Half the questions need four or more. So micro sitting **below** macro carries information: the
questions with more pieces score worse per piece than the light ones. One number cannot say that
and the pair can.

**Why it decided something.** `full_chain_recall` scores 1.0 only when every piece arrived, so
under independence a question needing `k` pieces resolves at `p^k`, weighted over that
distribution. Which `p`?

| `p` | prediction | measured 0.4686 is |
|---|---|---|
| macro 0.7645 | 0.4603 | **+0.0083** above |
| micro 0.7257 | 0.4007 | +0.0679 above |

Measured full-chain recall sits at or above the prediction under either choice, so the conclusion
survives. That is the only reason this is a footnote rather than a second retraction.

**The retraction it turned on.** Until 2026-09-01 this repository claimed independence predicted
0.6838 and that measured 0.4686 was 21 points below it, which pointed a quarter of roadmap at
hunting a hidden class of structurally hard question. Wrong in several ways at once, and one of
them was that it never said which `p` it used, or that it had put hops in the exponent where the
metric counts pieces. A number whose derivation is not written down cannot be checked.

**Sofia, for the client summary:** *"evidence recall 0.7645, macro-averaged over 207 answerable
questions, mean of the per-question fraction of gold evidence pieces retrieved."* Long, and every
clause is doing work.""",
   "accepted": True},
  {"by": "sofia", "body": """That is going in verbatim, with the piece-count distribution
underneath it, because the client's own corpus almost certainly has a flatter one and the
comparison will be misleading otherwise.

The part I did not expect: I came here to get a label right and left with a diagnostic. Reporting
both numbers costs nothing and the *sign of the gap between them* tells you whether your heavy
questions are being served worse than your light ones. I have three internal dashboards showing a
single recall figure and none of them can answer that.

Also worth saying that my first theory was that the two numbers came from different slices and
someone had leaked the frozen set into a dev run. It was not that. I spent a day on it because
that is the shape of problem I look for first."""},
  {"by": "lena", "body": """Correction accepted, and the way I got there is the useful part.

I reached for the convention because the convention is real and I have quoted it correctly in
other contexts. What I skipped was checking that the unit of analysis matched. TREC-style pooled
recall counts documents against a query; this counts pieces against a question, and a question
owns several. Same word, different denominator.

I have done this often enough now that I am adding it to my own checklist: before quoting a
convention, name the denominator the convention assumes and check it against the one in front of
me."""},
 ],
},
{
 "category": CAT, "author": "priya",
 "title": "Why does the repo ship alpha=0.2 when alpha=0.5 measures better?",
 "body": """### The question in one line

The alpha sweep — `python scripts/run_eval.py --sweep`, tabled in the fusion note — has 0.5
ahead of 0.2 on evidence recall and well ahead on nDCG, and `raglab.TUNED` still ships 0.2. Is there a reason, or is this a stale default nobody
has got to?

### What I have already tried

- Re-ran `python scripts/run_eval.py --compare` on a clean checkout to confirm I was not reading
  a stale table. Same result.
- Checked the paired bootstrap rather than eyeballing the point estimates.
- Looked for a comment in `raglab/` explaining the choice. Did not find one.

### The numbers

`python scripts/run_eval.py --sweep`, at k=8, reranked. (Same table as Priya's Show-and-tell
post *Negative result: I swept alpha from 0.1 to 0.7 and answer_correct never moved* — that
thread is about the order she ran it in; this one is about the default.)

| alpha | evidence_recall | ndcg | answer_correct |
|---|---|---|---|
| 0.1 | 0.7444 | 0.4152 | 0.4156 |
| **0.2** | **0.7645** | **0.4767** | **0.4115** |
| 0.3 | 0.7766 | 0.5047 | 0.4033 |
| 0.4 | 0.7790 | 0.5461 | 0.3992 |
| 0.5 | 0.7790 | 0.5967 | 0.3992 |
| 0.7 | 0.7778 | 0.6102 | 0.3951 |

And the paired bootstrap, delta being 0.5 minus 0.2:

```
w0.2 -> w0.5   evidence_recall  +0.0145   ci (+0.0048, +0.0254)   REAL
```

### Where

[docs/09-research/measurements/fusion-rules.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/fusion-rules.md)

I am happy to open the PR. I would rather understand the reason first, in case there is one.""",
 "replies": [
  {"by": "wei", "body": """Open the PR. A default that is measurably worse than an available
alternative is a defect, and you have the interval to prove it: +0.0145 evidence recall with a
lower bound comfortably off zero, plus twelve points of nDCG which is not close.

The nDCG gap is the one I would lead with. Evidence recall says the gold arrived somewhere in the
top eight. nDCG says where. 0.4767 against 0.5967 means the shipped default is putting evidence
further down the list for no benefit anyone has named.

The only defensible reason to keep 0.2 would be a cost or latency argument, and alpha is a
weighting term. It costs nothing."""},
  {"by": "marcus", "body": """The interval is right and the column Wei skipped is the one that
decides it.

`answer_correct` goes 0.4115 at alpha=0.2 and 0.3992 at alpha=0.5. So the arm that wins on both
retrieval metrics is numerically **behind** on the only metric a user experiences.

Before anyone builds an argument on that: from the same bootstrap run, **every pair on
`answer_correct` is inside the noise band**. Including this one. So the honest statement is that
the two arms are indistinguishable on answer correctness and one of them is better on retrieval,
which is a weaker case for changing than "0.5 is better" but still a case.

What it rules out is the reverse claim. Nobody can say alpha=0.2 is retained *because* it answers
better, and I would not sign a PR description that implied it."""},
  {"by": "tomas", "body": """Then leave it alone.

The baseline in `.github/eval-baseline.json` is cut from the shipped configuration and the CI gate
compares every run against it. Change the default and every headline figure in the README, the
notebooks, the Pages site and the seeded threads is stale in the same commit, and the gate that is
supposed to catch drift is the thing you just moved.

A gain that is real on evidence recall, invisible on answer correctness, and costs a full
re-baseline across the repository is not worth the churn. Freeze the default, put it in the
backlog, revisit when there is a reason to re-baseline anyway."""},
  {"by": "maintainer", "body": """There is a reason, it is administrative rather than technical, and
[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
files it under Consequences in the **Bad** column, which is where it belongs:

> Changing the default would move every headline number in the repository in the same commit as
> a correction, and conflating those two edits would make both harder to review. The honest
> statement is: **alpha=0.2 is retained because the baseline is cut from it and the alternatives
> are inside the noise band on the metrics that matter, not because it is optimal.** Moving the
> default is its own change, with its own re-baseline.

So the PR is welcome, as its own change, carrying the re-baseline. Tomás's reasoning is right and
his conclusion is wrong: the churn is real, which is why this gets its own commit rather than why
it never happens.

**The mechanism worth taking away is Marcus's.** Read *down* the `answer_correct` column in
Priya's table rather than across her rows. It falls gently as the retrieval metrics rise, and
alongside the bootstrap, where every pairwise delta on answer correctness sits inside the noise
band across arms spanning `evidence_recall` 0.7118 to 0.7790, that column is the third corrected
finding in ADR-0015: **no retrieval configuration on this corpus moves answer correctness.** The
system is generation-limited, so tuning alpha optimises a quantity that does not propagate.

**The condition under which Wei is straightforwardly right.** Put a generative reader behind this
and the alpha=0.5 gain has somewhere to go, because a reader that can combine evidence converts
ranking quality into answers in a way the extractive one cannot. Measure it rather than assume
it.

**And the history.** Until 2026-09-01 we claimed alpha=0.2 beat equal-weight RRF, on a mechanism
about the dense leg being the weak one. Both retracted. RRF beats BM25 alone by +0.0624 evidence
recall, ci (+0.0407, +0.0857), the dense leg is the **stronger** one, and alpha=0.2 loses to RRF
on nDCG by −0.0535. The default survived as a number in a baseline file rather than as a measured
winner, and Priya is the first person to ask why in the open.""",
   "accepted": True},
  {"by": "priya", "body": """Opening it as its own PR with the re-baseline, and I will say in the
description that it moves evidence recall and nDCG and does not move answer correctness, with the
interval for each.

Two things surprised me.

The first is that I came in ready to argue about alpha and left having read the `answer_correct`
column properly for the first time. I had looked at that table maybe six times and only ever read
across the row I cared about. The column was the finding.

The second is smaller and worse. My original plan was to change the default and let the eval gate
tell me whether it was fine. The gate would have gone green, because it compares a configuration
against its own committed past and a re-baseline resets exactly that comparison. I would have
taken a green tick as evidence and it would have meant nothing. That gap is named in ADR-0015 and
`--compare` is what closes it, and I had run `--compare` at the top of this thread without
understanding what it was for."""},
 ],
},
]
