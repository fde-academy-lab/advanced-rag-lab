"""Show and tell: four pieces of finished work, two of which found nothing.

ADR-0007 gives a negative result full credit, and a category that only ever carries wins turns
that policy into a poster. So two of these four report a thing that did not happen, and they are
written the way a negative result has to be written to be worth anything: the mechanism that
explains why the expected effect is absent, and the condition under which it comes back.

The other two are wins with an honest denominator. In both, the number the author first wanted
to report is the wrong number, and the thread is mostly about how they found that out.

Show and tell is not an answerable category, so nothing here is marked as an answer. The
resolution is the last thing the author did, not a tick.

Every figure quoted is one the repository produces, or is read out of a file the post links to.
"""
from __future__ import annotations

CAT = "Show and tell"

THREADS = [
{
 "category": CAT, "author": "priya",
 "title": "Negative result: I swept alpha from 0.1 to 0.7 and answer_correct never moved",
 "body": """**What I built.** A sweep over the weighted-fusion alpha — `python
scripts/run_eval.py --sweep`, `k=8`, `rerank=cross`, n=243, everything else at the committed
baseline. Alpha is the weight on the dense leg, so 0.1 is nearly all lexical and 0.7 is mostly
dense.

**This is not the thread about which alpha to ship.** That is *Why does the repo ship alpha=0.2
when alpha=0.5 measures better?* in Q&A, and it has the answer. This one is about the order I did
it in: I ran the sweep first and worked out the noise band afterwards, which is backwards, and it
is why this is a post rather than a pull request.

| alpha | evidence_recall | ndcg | answer_correct |
|---|---|---|---|
| 0.1 | 0.7444 | 0.4152 | 0.4156 |
| 0.2 | 0.7645 | 0.4767 | 0.4115 |
| 0.3 | 0.7766 | 0.5047 | 0.4033 |
| 0.4 | 0.7790 | 0.5461 | 0.3992 |
| 0.5 | 0.7790 | 0.5967 | 0.3992 |
| 0.7 | 0.7778 | 0.6102 | 0.3951 |

**What I expected.** A peak somewhere, with a defensible reason to move the shipped default off
0.2.

**What I got.** Two columns that climb and one that does not. `evidence_recall` rises about three
and a half points and then flattens from 0.4 onward. `ndcg` rises by almost twenty points and is
still rising at the right-hand edge. `answer_correct` drifts *down* across the whole sweep,
and every pairwise comparison on it comes back inside the paired-bootstrap band.

So the metric I would report to a client moves a lot, and the metric the client actually cares
about does not move at all, in either direction, anywhere in the range I swept.

**The awkward part.** The shipped default is alpha 0.2, which is the second-worst row in this
table on `ndcg` and the second-worst on `evidence_recall`. It is also, by a margin that is not
real, the best row but one on the only end-to-end number. I cannot tell whether the default is
right, and after a day of sweeping I know less about it than I thought I did when I started.""",
 "replies": [
  {"by": "wei", "body": """Ship 0.5 and stop worrying about it.

Twenty points of `ndcg` is not nothing, and `evidence_recall` agrees with it. `answer_correct`
here is a string match against a gold string, which is the noisiest thing on the scorecard and
the one furthest from anything you control. When the retrieval metrics and the end-to-end metric
disagree, the retrieval metrics are the ones telling you about your retriever.

We had exactly this shape on the incident assistant at my last place. Ranking quality improved
for two quarters before the answer-side numbers caught up, and if we had gated on the answer
metric we would have shipped none of it. Take the ranking win now and let the generator catch
up."""},
  {"by": "marcus", "body": """That reasoning holds when the ranking win reaches the generator, and
on this sweep it does not, for a reason that is visible in a column Priya left out.

`full_chain_recall` is **0.4686** at alpha 0.2 and **0.4686** at alpha 0.5. The same number.
Equal-weight RRF and dense alone both sit at 0.4638. Across four configurations that differ by
thirteen points of `ndcg`, the share of questions where *every* required piece of gold evidence
survives into the packed context is pinned.

`evidence_recall` is per piece. A question with four gold pieces contributes four chances to look
good on it and one binary outcome on the chain. Alpha is buying pieces on questions that were
already going to fail, which is exactly the movement `evidence_recall` is built to reward and
`full_chain_recall` is built to ignore.

`answer_correct` needs the chain. So the flat column is not noise swamping a real effect. There
is no effect at the stage that feeds the generator, and the sweep says so."""},
  {"by": "lena", "body": """Worth naming why 0.2 was chosen in the first place, since it explains
the shape of the table better than the table does.

The note in my reading file *said* the dense leg was the weaker of the two, and that was the
whole argument for giving it a fifth of the vote rather than half. Under that reading the sweep
is a story about handing progressively more weight to the worse retriever, which would account
for `answer_correct` drifting down from 0.4156 to 0.3951 as alpha rises.

Except `rrf.md` now carries a **Corrected 2026-09-01** banner saying both halves of that were
false. Before I lean on the version I remember, somebody check whether the shape of this table
needs the old story at all.

It would also mean the `ndcg` column is measuring the wrong thing rather than measuring a real
improvement, which is a convenient conclusion and I want somebody to check it before I lean on
it."""},
  {"by": "marcus", "body": """That note was retracted on 1 September. Please do not carry it
forward, because I wrote the original and it was wrong.

Measured, at k=8 after the cross-encoder:

```
BM25 alone         evidence_recall 0.7118   ndcg 0.3639
Dense (LSA) alone  evidence_recall 0.7733   ndcg 0.6055
```

The dense leg is the **stronger** one on both. So alpha 0.2 gives a fifth of the weight to the
better retriever, and the reason the `ndcg` column climbs as alpha rises is that you are
progressively undoing that.

The other retraction from the same day belongs here too, since somebody will reach for it: the
claim that equal-weight RRF loses to BM25 alone is also withdrawn. The paired bootstrap has
bm25 to rrf at **+0.0624 evidence_recall, ci (+0.0407, +0.0857)**. RRF wins, and it is not
close."""},
  {"by": "maintainer", "body": """The mechanism underneath all of this is the failure-overlap
diagnostic, which is the number that makes the flat column stop being surprising.

Of the 207 answerable questions, the dense leg misses 95 and the lexical leg misses 102. **Both
miss 92 of them.** P(lexical also misses | dense misses) is 0.9684, Jaccard 0.8762.

Fusion of any kind is a rule for combining two votes. When one voter is wrong, the other is
wrong on the same question 97 times in 100, so there is almost nothing for the weighting to
arbitrate. You can spend a day choosing how loudly each leg speaks and the set of questions that
end up answerable barely changes.

**The condition under which Wei's advice is right, and it is a real condition.** The overlap is
this high because a cross-encoder sits downstream and repairs the ordering. Take it away and the
fusion rule carries the whole result: at k=3 without the reranker, BM25 alone gets 0.3269
evidence recall and RRF gets 0.4517. Twelve points, from the fusion rule alone. Priya's sweep is
flat because something downstream is already doing the work, not because fusion weights never
matter."""},
  {"by": "dan", "body": """Asking the blunt version, because I have read the thread twice and
still cannot tell what it concludes.

Is the shipped default wrong? Everything above says alpha 0.2 gives most of the weight to the
weaker retriever, scores second-worst on two of the three columns, and rests on a premise that
has since been retracted. That reads like we have been running the worse setting for months.

But it also says the only column anybody ships against is flat, which reads like it does not
matter and we should leave it alone. Those cannot both be the takeaway, and if I had to put one
of them in a handover note today I would pick the wrong one."""},
  {"by": "priya", "body": """Neither, and I think that distinction is the whole finding.

The default is not wrong. It is **undetermined** on this eval set, and those are different
results with different next steps. A wrong default gets changed. An undetermined one gets a
measurement plan.

What I actually did: left alpha at 0.2, and wrote down the thing I should have written down
before I started sweeping. If alpha is a real lever, the observation is that per-query win rate
between the legs moves as I turn it, and the failure overlap comes down from 0.9684. Neither
happens here. Until it does, `ndcg` moving is a fact about the ranked list and not about anybody
being better served.

The day was not wasted, but it would have been a morning if I had computed the band first."""},
 ],
},
{
 "category": CAT, "author": "tomas",
 "title": "I moved our release gate off the aggregate and onto the question_type slice",
 "body": """Picked this up because it has been on the standup's blocked list for two weeks with
nobody's name on it. Here is what I have, which is less than a diagnosis and more than the
dashboard was showing.

The headline `answer_correct` is 0.4115 over 243 questions. Underneath it:

| question_type | n | evidence_recall | full_chain | answer_correct |
|---|---|---|---|---|
| comparison | 46 | 0.748 | 0.391 | **0.848** |
| inference | 95 | 0.769 | 0.621 | 0.579 |
| temporal | 66 | 0.769 | 0.303 | **0.091** |
| null | 36 | — | — | 0.000 |

Weight those four by n and you land back on the headline 0.4115, which is worth doing by hand
because it makes the point better than any amount of arguing. Four numbers go in: 0.848, 0.579,
one that is essentially zero, and zero. The mean of them lands somewhere none of the four is, and
reads as a system that is mediocre everywhere rather than one that is excellent on one shape of
question and absent on another.

**The part I did not expect.** Look at the `evidence_recall` column. Temporal and inference are
both 0.769, identical to three places, and inference scores 0.579 on answers where temporal
scores 0.091. Whatever is wrong with the temporal slice, the retriever is finding the same share
of the gold evidence on it as on the slice that mostly works.

Comparison makes it stranger. Its `full_chain` is well below inference — 0.391 against 0.621 —
and it has the **highest** `answer_correct` in the table at 0.848. So neither recall column
orders the slices the way the answer column does: answers run comparison > inference > temporal,
evidence recall has inference and temporal tied above comparison, and full-chain runs inference
> comparison > temporal.

**What I want to do about it**, and I know this is my usual instinct: freeze the release gate on
the temporal slice until somebody explains it. Talk me out of that if it is the wrong shape.""",
 "replies": [
  {"by": "wei", "body": """This one has a known answer and you do not need a diagnosis to start.
Temporal questions need temporal retrieval. Dense and lexical similarity both treat "Q2 2024" and
"Q2 2023" as nearly the same string, so you get the right document and the wrong period, every
time, and no amount of reranking fixes it because the reranker is scoring the same similarity.

The fix is a date filter in front of the retriever: parse the period out of the query, restrict
the candidate set to chunks whose date field falls inside it, then rank within that. We shipped
it on the incident assistant and the temporal complaints stopped inside a sprint.

I would do that before spending another week on the slice. It is a day of work and it addresses
the thing everyone already believes is happening."""},
  {"by": "marcus", "body": """It addresses the thing everyone believes is happening, and Tomás's
table is evidence against that thing happening.

A date filter improves which candidates reach the reranker. The metric that measures which
candidates reach the reranker is `evidence_recall`, and on the temporal slice it is 0.769,
against 0.769 on inference and 0.748 on comparison. The temporal slice is not the outlier there.
It is the outlier on the answer column alone.

So the proposal fixes a stage where this slice already performs like the slices that work, and
the failure is downstream of it. You could implement it perfectly and move `evidence_recall` on
the slice from 0.769 to 1.0, and the model would still have both quarters sitting in the packed
context and still have to choose between them.

**Your fix is the right one when the evidence is not being retrieved.** Here it is."""},
  {"by": "lena", "body": """There is a third possibility that nobody has checked and it is in the
scorer, not the system.

Read `answer_correct` in
[/fde-academy-lab/advanced-rag-lab/blob/main/raglab/metrics.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/metrics.py).
It splits the gold answer on `[^a-z0-9$%.]+`, keeps tokens longer than two characters, takes the
first six, and requires that 0.6 of them appear in the response.

Now read how temporal questions are generated in
[/fde-academy-lab/advanced-rag-lab/blob/main/raglab/corpus.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/corpus.py).
A whole family of them asks whether growth sped up or slowed between two quarters, and the gold
answer is the single word `accelerated` or `slowed`. One key token, threshold 0.6, so the
response has to contain that literal token. A model that says "growth decelerated" or "it fell"
has answered the question correctly and scores zero.

That is **50 of the 66** temporal questions carrying a one-token gold answer, which I counted
rather than estimated. I would fix the scorer before touching anything else."""},
  {"by": "maintainer", "body": """Lena's reading of both files is right and the conclusion does
not follow yet, for a reason worth being precise about.

Two of the three candidates you would reach for are not candidates here, and the reason is in
`generate.py`'s first paragraph. **The default reader is extractive.** It selects supporting
sentences from the packed evidence and emits them with their citations; it "cannot hallucinate",
which also means it cannot compose, cannot paraphrase, and cannot produce a word that appears in
neither chunk. "The model picked the wrong period" and "the model failed to compose two dated
pieces" both describe a generative reader we are not running.

So the scorer strictness Lena found and the extractive reader **compound** rather than compete:
50 of 66 temporal questions need one literal token, and the only way to emit it is for a
retrieved sentence to contain it. That is why ADR-0015 calls this system generation-limited.

What the cross-tab would still tell us is *how much* of the 0.091 the one-token gold answers
account for — gold-answer shape on the temporal slice against per-question outcome. That is an
afternoon and it is the next thing anybody should do here.

The one thing not to do is the fix Lena proposed in the order she proposed it. **Changing a
scorer to make a number go up is the single change whose success cannot be validated by the
number going up.** If the scorer is genuinely too strict, that is established by hand-labelling a
sample of temporal responses and showing the scorer disagrees with the labels, and then the
scorer change is defensible on evidence that exists independently of it.

For context on the first candidate: this slice is the repository's worked instance of FP6 in
[CS-03](/fde-academy-lab/advanced-rag-lab/blob/main/concepts-and-case-studies/case-studies/CS-03-seven-failure-points.md),
which names it "right document, wrong quarter". That is a hypothesis with a citation, not a
measurement."""},
  {"by": "aarav", "body": """From the client-facing side, the reconstruction at the top of this
thread is the deliverable regardless of how the diagnosis lands.

"Answer correctness 41%" and "84% on comparisons, 58% on inference, 9% on anything with a date in
it" describe the same system, and the second one is the only version a buyer can act on. Nobody
buys a 41% system. Plenty of people buy a system that is excellent on two of their three question
shapes if they are told which third to route elsewhere.

I have started leading with the slice table in scoping calls and it has changed what the
conversation is about."""},
  {"by": "tomas", "body": """What I did in the end, having been talked out of the freeze.

The gate now reads the slice rather than the aggregate. A release cannot drop `answer_correct` on
any single `question_type` slice, which would have caught this the week it appeared instead of
averaging it into a number that looked merely mediocre. Freezing the release would have stopped
work on the one part of the system that is provably fine.

I also stopped asking for a diagnosis before the cross-tab. I have been treating "nobody has
explained it" as a reason to hold, and on this one nobody had explained it because nobody had
spent the afternoon. The cross-tab is mine for Thursday.

The thing I will keep from this: `evidence_recall` 0.769 on both temporal and inference told me
more by being **equal** than any single low number would have. I nearly did not put the two rows
next to each other."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "Negative result: I tried to build the abstention gate and all I have is a control that passes",
 "body": """I volunteered for this at standup after the abstention row got explained to me, so I
owe the thread a result. The result is that I did not ship it, and I think the reason is more
useful than the gate would have been.

Where the committed baseline sits, on the 36 null questions:

```
abstention_recall        0.0
abstention_f1            0.0
false_answers_on_null     36
over_refusals              0
answer_correct, nulls  0.000
```

The system answers all 36 and has never once declined anything.

**What I built first.** Not the gate. A control: a function that ignores its input and returns
the `INSUFFICIENT_EVIDENCE` sentinel for every question. Marcus's warning at standup was that the
cheap way to satisfy an abstention instruction is to decline more often everywhere, and I wanted
to know what "everywhere" scores before I had a real candidate to be pleased with.

Score the control against the same scorecard and, without reading a single document:

| | baseline | always-abstain control |
|---|---|---|
| `abstention_recall` | 0.0 | **1.0** |
| `false_answers_on_null` | 36 | **0** |
| `over_refusals` | 0 | 207 |
| `answer_correct` | 0.4115 | 0 |

Two of the four numbers in this table improve, both to their best possible value — and the two
that get worse are the two nobody was watching. The control is a constant function, and on the
metrics that were supposed to tell me the gate worked it is a clean sweep.

**Where I stopped.** I had a real candidate half-written and no way to show it beat that. So I
have a control, a reason not to trust the row, and no gate.""",
 "replies": [
  {"by": "aarav", "body": """I think you have talked yourself out of a day of work.

Nobody is going to ship the always-abstain function, so its scores do not really matter. Put the
instruction in the prompt, watch `false_answers_on_null` come down from 36, watch `over_refusals`
stay near zero on the answerable set, and if both hold you have the thing. Clients ask "does it
make things up" and that pair of counts is the answer to their question.

Perfect is doing a lot of work in this thread and the current state is a system that fabricates
an answer to every single unanswerable question that has ever been put to it. Almost anything is
an improvement on that."""},
  {"by": "lena", "body": """There is a standard method for this and it has been studied for
years. Selective prediction: attach a confidence to every prediction, sweep a threshold over it,
and plot risk against coverage. The curve tells you what each operating point costs, and you
choose the point where risk crosses whatever the product can tolerate. Reported this way, the
result is a curve rather than a single pair of counts, which is what makes it defensible.

Dan, you already have the input. Threshold on the top retrieval score, sweep it across the range,
read the operating point off the curve. That is an afternoon and it gives you something with an
interval on it rather than an argument about which counts to trust."""},
  {"by": "marcus", "body": """The method transfers when the setup does, and two things in the
setup here are different in ways that matter.

Selective prediction as usually reported has a calibrated score over a closed label set, and the
risk-coverage curve is estimated from thousands of held-out points. What Dan has is free text
from a generator and a retrieval score whose distribution over the 36 nulls **nobody has ever
plotted**. It may separate them cleanly. It may not. That is a measurement, and it is the
measurement that decides whether the method applies at all, so it cannot be assumed by choosing
the method.

The second problem is the arithmetic. The recall arm of `abstention_f1` is estimated on 36
points and the precision arm on 207. If Dan sweeps a threshold on those 36 nulls and then reports
his chosen threshold's score on the same 36, he has fitted and reported on one set. Holding out
gives him 18 to fit on. At 18 points, a threshold that looks best is frequently the one that got
lucky, and there is no second eval set here to catch it."""},
  {"by": "tomas", "body": """The operational half nobody has raised. If the gate ships, a refusal
is a 200 with a body, and there is no alert on `over_refusals` anywhere.

The failure I expect to get paged for arrives six weeks after the gate ships, when somebody
tightens a threshold for a good reason and the system starts quietly declining a rising share of
answerable questions. That looks like healthy traffic on every
dashboard we have. Latency fine, error rate fine, cost slightly down because the responses got
shorter.

Whatever ships, `over_refusals` on the 207 answerable goes on the dashboard next to
`false_answers_on_null`, and the alert is on the ratio between them rather than on either
alone."""},
  {"by": "maintainer", "body": """Dan has found something real and it is worth naming precisely,
because "the metric is bad" is not it.

`abstention_f1` is a metric over a decision this system does not make. With `over_refusals` at 0
and `abstention_recall` at 0.0, the system occupies **one corner of the confusion matrix**, and
one point is not a curve. Every method for choosing an operating point, including Lena's, assumes
you can move along a curve and read off what each position costs. The gate itself exists —
`ExtractiveGenerator(min_evidence_score=θ)` — and it is **off by default**, which is why the
baseline sits in one corner. Turning it on is one argument.

**But the sweep has been run.** Notebook 05 §5.6 collects the top packed evidence score per
question over the full eval set at the real base rate, sweeps θ, and plots the two distributions.
They overlap across the interquartile range. Best F1 on that threshold is **0.38**, and three
other retrieval-side signals sit nearer chance.

So the operating point Lena would read off that curve is not one anybody should ship, and the
reason is not that the curve is missing. It is that no line through that score separates the two
populations — the nulls name real entities in the corpus's own vocabulary while the genuine
questions paraphrase, so the unanswerable ones sit *closer*. The honest finding is that
abstention here needs a different signal, not a better threshold on this one.

Aarav is right that the urgency is real, and wrong about what his pair of counts would prove.
The control in the original post settles that: `false_answers_on_null` at 0 with `over_refusals`
near 0 also describes a function that read nothing."""},
  {"by": "dan", "body": """What I actually did, which is smaller than the gate and I think worth
more.

The run now emits the top retrieval score per question into the results rows. That is four lines
and it costs nothing, and it means the distribution Marcus and the maintainer both asked for can
be plotted from the next run rather than requiring a run of its own. The gate is unshipped and
the branch is up.

The thing I got wrong, and it is the same thing I got wrong at standup: I took a confident answer
about the fix before anybody had established what was broken. Wei's prompt instruction might well
work. I have no way to tell, and neither does anyone else, until that distribution exists.

Writing the control first is the only part of this I would repeat exactly. It took twenty minutes
and it is the reason I did not spend a week reporting a number that a constant function
beats."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "Cut the prompt cache bill on C1 and nearly sent a client the wrong number",
 "body": """Ran C1, cleared both bars, and wrote the client a line about it. The line was wrong in
three separate ways and I only found the third one because Priya read my working. Posting all
three, because the fix in C1 is easy and the reporting around it clearly is not.

**What the simulator gave me**, 200 requests, four configurations:

| configuration | cache_hit_rate | mean full-rate tokens billed |
|---|---|---|
| assembler as given | 0.2612 | 154.04 |
| correct volatility order | **0.8176** | **38.07** |
| timestamp deleted instead | 0.7942 | 42.16 |
| stable blocks moved too | 0.6969 | 63.23 |

The fix is the one the
[brief](/fde-academy-lab/advanced-rag-lab/blob/main/lab-simulator/units/C1-cache-barrier/BRIEF.md)
says it is. A timestamp sitting early in the prefix invalidates everything after it, so it moves
after the retrieved chunks rather than being deleted, and the feature that needs it survives.

**The line I wrote.** "Prompt restructuring cut cost per query by 58%."

I did not measure that number. It comes out of
[ADR-0012](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0012-prompt-block-ordering.md),
measured on a different system that went from 4% to 71% hit rate. My simulator went from 0.2612
to 0.8176 on 200 synthetic requests. Two systems, two hit rates, and I had quietly borrowed the
one with the more quotable percentage attached.

That is the first way it was wrong, and it is the one I am least comfortable about, because I
would have said out loud that I do not do that.""",
 "replies": [
  {"by": "wei", "body": """Before the reporting argument, the engineering one. Look at rows two
and three of your own table. Moving the timestamp gets 0.8176 and deleting it gets 0.7942. That
gap is about two points of hit rate and four tokens.

Deleting is one line and cannot be got wrong later. Moving it means every future prompt change
has to preserve an ordering invariant that a reviewer has to know about, and somebody will break
it in six months and nobody will notice for another six, which is exactly how the original
incident happened.

I would delete the timestamp and put the two points of hit rate in my pocket."""},
  {"by": "maintainer", "body": """The two configurations differ by a capability, and the metric
cannot see capabilities. That is the trap the unit is built around, and it is worth stating in
full because it recurs everywhere.

Row three has deleted the field that answers "as of when?". The simulator has no column for
questions the system can no longer answer, so a feature removal shows up as a small cost win and
nothing else. The bill went down because the product got smaller, and if the only instrument is
the bill, that is indistinguishable from an optimisation.

**And Wei's argument is correct under a condition that is easy to check.** If nobody asks the
system as-of questions, the timestamp is dead weight and deleting it is the better fix, cheaper
to hold and impossible to regress. The ordering rule is over-engineering for a system that does
not need the field. The mistake is deciding that from the cost column instead of from the query
logs.

On the enforcement half of Wei's worry, ADR-0012 is not asking reviewers to remember anything.
There is a test asserting the first N tokens of the assembled prompt are identical across two
different queries, and it would have caught the original timestamp on the day it landed."""},
  {"by": "priya", "body": """Second way it is wrong, and this is the one I found while trying to
reproduce your before-and-after in the eval harness rather than the simulator.

The committed baseline reports `cost_usd` 0.0039, and you cannot use that as the "before" of a
caching claim. From
[/fde-academy-lab/advanced-rag-lab/blob/main/raglab/pipeline.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/pipeline.py):

```python
row["cost_usd"] = rates.cost(row["tokens_in"], row["tokens_out"])
```

Two positional arguments. `Rates.cost` takes four, and `cache_read` and `cache_write` both
default to zero. So every `cost_usd` on the scorecard is priced as though no cache exists at all,
in both arms of any comparison you run there. It is a correct number for what it measures and it
is structurally unable to show a caching saving, in either direction.

Not a bug. It is just not the instrument for this claim. The specific line is
`pipeline.py`'s `row["cost_usd"] = rates.cost(row["tokens_in"], row["tokens_out"])` — two
arguments where the rate card takes four. The general version is the four-category note in
[costs.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/costs.py)'s docstring: *"kept
separate because you cannot optimise what your dashboard has already summed into one number."*
I had read both and understood neither until I hit this."""},
  {"by": "marcus", "body": """Third way, which follows from what Priya just quoted. `costs.py`
keeps four categories separate and explains why in the module docstring: you cannot optimise what
your dashboard has already summed into one number.

```
input         new prompt tokens
output        generated tokens
cache_write   reusable prefix processed and stored
cache_read    that prefix reused on a later request
```

Aarav's table has one column, "full-rate tokens billed", which is the merge of exactly the
categories that behave differently. Two things it cannot show.

**Writes are not free.** `cache_write_multiplier` is 1.25 for the five-minute cache and 2.0 for
the hour. At a 0.8176 hit rate, roughly one request in five is still paying a premium to write
the prefix, and that premium is on the input side of a saving being reported as a percentage of
everything.

**Output is untouchable.** The baseline is `tokens_in` 884.05 and `tokens_out` 82.21. At the
placeholder rates, that is 884.05 × 3.00 against 82.21 × 15.00 per million-token unit, so output
is roughly a third of the per-query bill and no amount of cache work moves it. A saving quoted
against the whole bill and delivered only on part of it will be missed by the margin between
those."""},
  {"by": "sofia", "body": """Adding the tenancy version, since a client will ask it within one
meeting of seeing this.

ADR-0012 has the sentence that matters: volatility is relative to the cache key. A field that
changes between tenants and never within one is stable per tenant and volatile globally, so it
belongs before the barrier if the cache is keyed per tenant and after it if it is not.

Which means the ordering you just measured is not a property of the prompt. It is a property of
the prompt **and** the cache key, and if the deployment shape changes from one tenant to shared,
the correct ordering changes with it and the hit rate falls without anybody touching the
assembler. Worth stating in the note, because otherwise the first multi-tenant deployment reads
as a regression."""},
  {"by": "aarav", "body": """What I sent in the end.

Not a percentage. The two configurations, the byte-58 mechanism, and the sentence from
`costs.py` about the rate card being illustrative and needing real numbers before anybody quotes
it. The client's own rates are not the placeholder ones and their input-to-output ratio is
nothing like 884 to 82, so my percentage would not have survived contact with their invoice
anyway.

The reply I got asked which of their query shapes have a stable prefix at all, which is a much
better question than the one I had teed up, and it is now the first thing on the scoping call.

What I would keep: reporting the four categories separately even when three of them are "not
recorded". Writing "not recorded" three times is what made me go and look at `pipeline.py`, and I
had been about to write one confident number instead."""},
 ],
},
]
