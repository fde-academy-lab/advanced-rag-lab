"""Ideas: four proposals from the extension-points page, argued the way a proposal should be.

An idea is not a wish. The four threads here model the four states a proposal can be in after
somebody competent has read it: **redirected** (the intervention is aimed at the wrong stage of
the pipeline), **narrowed** (the idea is fine and the plan starts with the wrong step),
**rejected** (the metric it moves is not a constraint here and the metric it damages is), and
**bounded** (a cheap measurement decides whether the expensive build is worth starting).

Two things they are built to teach.

The first is that an idea earns its place by carrying four items: the hypothesis, the metric and
slice it would move, the size of effect that would count as a win, and what it costs. A proposal
missing the third item cannot be finished, because there is no number at which you stop. The
replies push on exactly that, and the pushback is the content.

The second is that this repository has retracted two findings, and both retractions are alive in
these threads because people still repeat the retracted version from memory. Watching a
confident, wrong, previously-published claim get corrected in public is worth more than reading
the corrected claim on its own.

Every figure quoted is one the repository produces, and the links point at the note that
produced it.
"""
from __future__ import annotations

CAT = "Ideas"

THREADS = [
{
 "category": CAT, "author": "priya",
 "title": "Idea: RAPTOR over the temporal slice — a proposal, not another diagnosis",
 "body": """Extension 8 on the [extension points
page](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/extension-points.md), aimed at
one slice rather than at the corpus.

**The slice.** Temporal questions, n=66, from the committed baseline:

| slice | n | evidence_recall | full_chain_recall | answer_correct |
|---|---|---|---|---|
| comparison | 46 | 0.748 | 0.391 | 0.848 |
| inference | 95 | 0.769 | 0.621 | 0.579 |
| temporal | 66 | 0.769 | 0.303 | **0.091** |

Nine percent. Every other slice is at least six times that.

**Hypothesis.** Temporal questions ask what changed between two points in time, and flat
chunking has no unit that represents a span. Cluster chunks, summarise the clusters, recurse,
and retrieve at whichever level the question needs. A question about a quarter gets a node that
is about the quarter.

**Metric and slice.** `full_chain_recall` on the 66 temporal questions. Nothing else, and I would
treat a gain on the other two slices as a warning rather than a bonus.

**Effect that would count.** +10 points on that slice, 0.303 to at least 0.40, with an interval
clear of zero on the paired bootstrap. Below that I would not keep the tree.

**Cost.** Index-time model calls that get repaid on every corpus refresh, a tree to keep fresh,
and the provenance problem the page already flags: a summary node is retrievable but not
citable, so R1's promise that a marker resolves to something a human can check gets harder.

**What I have not done.** I have not worked out where in the pipeline the 0.091 is lost.
Retrieval is the part I know how to change, so it is the part I proposed changing.""",
 "replies": [
  {"by": "wei", "body": """Build it. We ran a summarisation tree over two years of release notes
at my last place and quarter-scale questions went from unusable to the thing the support team
opened first. The mechanism you describe is the one we saw: the chunk that answers "what changed
in Q3" does not exist until you make it, and no amount of reranking finds a document that is not
in the index.

Two implementation notes from that build. Summarise with the cluster's date range in the node
text, or the tree is useless for exactly the questions you built it for. And re-summarise on a
schedule rather than on every write, because the refresh cost is what kills these."""},
  {"by": "lena", "body": """Seconding, with the paper. Sarthi et al. report the gains on
long-form narrative sets where the answer is distributed across a document that nobody would
chunk flat. That is a strong result and it is the closest published thing to Priya's slice.

The tree also gives you something the flat index cannot: a retrieval unit whose size matches the
question's scope. A question about a quarter and a question about one incident currently compete
for the same eight slots at the same granularity."""},
  {"by": "marcus", "body": """Hold on. Look at the first column of Priya's own table.

`evidence_recall` on temporal is 0.769. On inference it is also 0.769. The retriever finds the
same fraction of gold evidence on both slices, and `answer_correct` differs by a factor of six
between them, 0.091 against 0.579.

RAPTOR moves the first column. Whatever produces the 0.091 is downstream of a number that is
already equal to the slice where correctness is fine.

The
[fusion note](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/fusion-rules.md)
made the same point across the whole corpus: evidence recall spans 0.7118 to 0.7790 across five
fusion arms and every pairwise comparison on `answer_correct` sits inside the noise band. The
numerically best answers came from the numerically worst retriever. The system is
generation-limited on this corpus, and a better index is a lever that is already close to
exhausted."""},
  {"by": "tomas", "body": """The cost line also needs a second sentence. "Index-time model calls
repaid on every refresh" is a per-refresh bill, and it is also a new failure mode with a pager
attached: the tree can be stale in a way the flat index cannot, because a summary node keeps
answering confidently from last month's clusters after the leaves under it changed.

Whoever builds this owes a freshness metric before they own the tree, and the metric has to be
per-node rather than per-index."""},
  {"by": "maintainer", "body": """Wei's experience is real and the mechanism he names is real.
The condition it needs is the part that does not hold here.

A summarisation tree pays when the answer does not exist as a contiguous span anywhere in the
corpus, so retrieval genuinely cannot return it at any k. That is a **retrieval** deficit, and
Priya's slice does not have one: 0.769 evidence recall on temporal is the same rate as the slice
that answers 0.579 correctly. The evidence is arriving. Something after retrieval is failing to
turn it into a right answer, and a new index level cannot reach that.

So the next action is a diagnostic, and it is cheap. Split the 66 temporal questions on whether
`full_chain_recall` was 1.0, and read `answer_correct` inside each half. That gives three
outcomes and they point at three different quarters of work:

- correctness near the floor even where the whole chain arrived, and the problem is generation
  or the judge, and no index change touches it
- correctness fine where the chain arrived, and the 0.303 full-chain rate is the target, which
  is a packing and budget question before it is a chunking one
- too few questions in one half to say, which is itself the finding, and the answer is a bigger
  temporal slice before any of this

Priya, run that before you write a clusterer, and keep the proposal. If the second outcome comes
back, this thread is already the design review."""},
  {"by": "priya", "body": """Reading the temporal questions by hand while the split runs, and
the thing that surprised me is not in the data.

I picked the intervention I knew how to build. I have chunked things and I have never touched a
generator, so I wrote a chunking proposal about a slice whose chunking column was the only one
that looked healthy. The number I anchored on, 0.091, is three columns away from the thing I
proposed to change, and I had the table in front of me the whole time.

Rewriting it as two proposals with the diagnostic between them, and I will post the split as a
measurement note rather than as a comment here so it can be re-run."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "Idea: teach the thing to say it does not know, and the embarrassing question underneath",
 "body": """Asking the naive version first because I genuinely do not know the answer.

The corpus has 243 questions. 207 are answerable and 36 are unanswerable by construction. The
baseline scorecard says:

```
abstention_recall        0.0
abstention_f1            0.0
false_answers_on_null    36
over_refusals             0
```

We answer all 36 of them. Confidently, with citations, in the same format as a correct answer.

**The embarrassing question.** Why is `over_refusals 0` printed next to that as if it were good
news? A system that never refuses gets a perfect over-refusal score for the same reason a system
that never predicts positive gets perfect precision on the empty set.

**The idea**, extension 10 on the research page: self-critique. Generate, then have the model
judge whether the retrieved evidence supports what it just wrote, and re-retrieve or abstain if
it does not.

**Metric and slice.** `abstention_f1` over the 36 nulls, with `over_refusals` on the 207
answerable reported beside it every time. Neither on its own means anything.

**Effect that would count.** The page sets the bar at abstention F1 above 0.38 and calls this
the highest-value open item in the repo.

**Cost.** An extra model call per query. Mean `tokens_in` is 884.05 with p95 1123, so a critique
pass over the same context roughly doubles the input side of the bill, and adds a component that
can regress on its own.""",
 "replies": [
  {"by": "lena", "body": """Self-RAG, Asai et al. 2023, is exactly this and it is further along
than you think. The model emits reflection tokens during generation that say whether retrieval
was needed, whether the passage supports the claim, and whether the output is useful. You get
the critique inline rather than as a second pass, so the cost story is better than doubling.

The reported gains on their evaluation are large and they hold on the open-domain sets. This is
one of the cleanest results in the retrieval literature over the last few years."""},
  {"by": "dan", "body": """That settles it then, and it is more tractable than I expected if the
critique comes inline. Scoping it as a two-week piece:

1. wire the reflection tokens into the generate step
2. threshold on the support token
3. abstain below the threshold
4. re-run the baseline and report `abstention_f1` against the 0.38 bar

Week one is 1 and 2, week two is 3 and the re-run. If it lands above 0.38 we ship it and close
EX-18, and if it lands under we have a threshold to tune rather than a design to rethink, which
is the good kind of not-yet. Anyone want to review the wiring before I start?"""},
  {"by": "marcus", "body": """Dan, the measurement you would put between step 0 and step 1 has
already been run, and it deletes most of the plan rather than confirming it.

**No signal we compute separates the 36 nulls from the 207 answerable.** Best F1 **0.38** across
four of them — top-1 score, the rank-1-to-rank-2 gap, the mean of the top-k, and score entropy —
and the metrics page says so with the mechanism attached: the nulls *name real entities in the
corpus's own vocabulary* while the genuine questions paraphrase, so the unanswerable ones come
out lexically **closer** to the corpus. Any threshold on retrieval score is reading a feature
with the wrong sign, and no amount of tuning repairs a sign.

That matters for your step 1, because a critique layer has to learn the separation from
something. If the retrieval signal carries none — and it does not — a second model call over the
same eight chunks is looking at the same undifferentiated evidence the first one saw. You would
be paying twice for one view.

Which leaves the question the repository actually has open: whether a **sufficiency** signal —
does this evidence *entail* an answer — carries what a similarity signal cannot. That is issue
#10 and nobody has measured it. It is the only part of this idea that is genuinely unknown, and
it is worth more than the four steps around it.

Second point, on reporting. 36 items is a small denominator, and no interval has ever been put
on that 0.38 — the repository publishes the point estimate and nothing around it. Decide now how
you will report it, and pre-commit to the interval rather than the point."""},
  {"by": "tomas", "body": """And the direction nobody has said out loud. `over_refusals` is 0
today, which means every abstention you add is a brand new way for this thing to fail in front
of a user, and it is a failure mode the current system is structurally incapable of.

I am not arguing against it. I am arguing that the gate has to move at the same time. Gate on
both numbers or you will trade 36 confident wrong answers for some unknown number of "I could not
find that" against evidence that was sitting in the context.

Also make the abstention message name what was missing. A refusal that says nothing is a support
ticket; a refusal that says which entity or date it could not find is a search the user can
redo."""},
  {"by": "maintainer", "body": """Lena's summary of the paper is accurate and the setup is the
part that does not carry over.

Self-RAG's reflection tokens come from a model **trained to emit them**, on data built for that
purpose. The training set is the contribution. The inference-time loop is the cheap half, and
bolting the loop onto a model that was never trained for it gives you a second generation pass
that shares the first pass's priors, including the prior that produced the confident answer you
are asking it to doubt. A critic with the same beliefs as the author agrees with the author.

The condition under which the published result transfers is that you have supervision for the
critique step, or can afford to make it. That is the same conclusion Marcus arrives at from the
other side: his separation check is asking whether the supervision already exists for free in
the scores.

One caution on the target, and it points the opposite way to the obvious one. These 36 nulls are
not the easy end of the abstention problem — they are adversarial by construction. They are
on-topic, in-vocabulary, and they retrieve confident well-ranked evidence, which is exactly why
similarity-based abstention cannot touch them. Real unanswerable questions are ones where plausible evidence
exists and does not support the claim. An abstention F1 measured only on constructed nulls will
read higher than the same system scores in production, so treat 0.38 as a floor on a friendly
set rather than as the finish line."""},
  {"by": "dan", "body": """Right, and my two-week plan had no measurement in it.

Four build steps, one re-run at the end, and the re-run was there to confirm the thing rather
than to decide anything. I accepted the first confident answer in the thread and started
scheduling. Lena's answer was correct about a different question from the one I asked, and I could not tell
the difference because I did not know enough to ask which setup it came from.

Rewritten:

- **Day one:** read the result that already exists rather than reproducing it — best F1 0.38,
  and the nulls are lexically *closer* to the corpus than the answerable questions. The branch I
  had written as "if they separate" is closed, and I was going to spend a day closing it again.
- **Day two:** build the sufficiency check as a **standalone component** — does this evidence
  entail an answer — and report its precision and recall against the 36 before wiring it into
  anything. That is EX-18's acceptance criteria and it is the first genuinely unmeasured step.
- **Only then:** the critique layer, and only if the standalone number justifies it.
- **Either way:** `abstention_f1` and `over_refusals` reported together, on 36 and 207
  respectively, and I will say plainly that no interval has been put on either.

Posting the standalone numbers whichever way they come out."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "Idea: a semantic answer cache in front of the assembler",
 "body": """Extension 5 on the research page. Framing it the way I would frame it to a client,
because that is the framing it has to survive.

**The idea.** Embed the incoming query. If it is within a similarity threshold of a query already
answered, serve the stored answer and skip retrieval, packing and generation entirely.

**Hypothesis.** On a realistic traffic mix, at least a quarter of queries hit the cache at a
threshold that keeps the false-hit rate under one percent. Those are the page's numbers and they
are a reasonable bar.

**Metric.** Mean cost per query and p95 latency, plus the cache's own hit rate and false-hit
rate.

**Effect that would count.** Cutting mean cost per query by a third.

**Cost.** One embedding per incoming query, a store with an eviction policy, and a threshold
constant that has to be refitted whenever the question mix moves.

**On the risk.** The page flags that a near-miss serves a confidently wrong answer, and calls
this the one extension that can make quality worse while every dashboard improves. I take the
point and I think it is a threshold-tuning problem. Set the threshold conservatively, measure
the false-hit rate, tighten until it is under one percent, ship.

The reason I am proposing it now rather than later is that it is a story a client understands in
one sentence, and it is small.""",
 "replies": [
  {"by": "priya", "body": """Strongly in favour. The assembler and the generate step are the
expensive part of the pipeline and everything upstream of them is comparatively free, so cutting
them out entirely for a quarter of traffic is the biggest single lever on the bill that I can
see.

I would build the cache before the threshold work, honestly. Get the hit rate measured on real
traffic and then decide what the threshold has to be, rather than arguing about the constant
before we know whether anything hits at all."""},
  {"by": "sofia", "body": """This crosses the ACL prefilter and I do not think it can be built as
described.

[ADR-0011](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0011-prefilter-acl.md)
filters candidates by persona before retrieval. The corpus has four: analyst, counsel,
finance_partner, support_engineer. The same question from counsel and from support_engineer is
the same embedding and a different reachable corpus, so a cache keyed on the query vector serves
one persona's evidence to another. That is a disclosure, and it is reportable.

The fix is a cache partition per persona, and it is not optional. It also divides your hit rate
by four before you start, which I think changes the economics enough that the proposal should be
re-costed. Partition it and I would support this."""},
  {"by": "marcus", "body": """Before the partitioning argument, the numerator.

Baseline, n=243: `cost_usd` mean **0.0039**, p95 0.0046. `latency_ms` mean **34.62**, p95 42.99.

A third off 0.0039 is 0.0013 of a dollar per query. To turn that into a line an engineer's week
is worth, you need volumes this system has never been measured at, and if those volumes existed
the cost profile at that scale is the thing to measure first.

Now the denominator of the risk. `false_answers_on_null` is 36 out of 36 and `abstention_f1` is
0.0. The failure this cache introduces is a confidently wrong answer served to a query that was
nearly the same as a different one, and the system has no mechanism anywhere that catches a
confidently wrong answer. We are proposing to add a new source of the one failure we cannot
detect, to save a tenth of a cent."""},
  {"by": "wei", "body": """The dashboard warning on that page is not theoretical and I want to
put the shape of it on record, because it took us a long time to see.

We shipped semantic caching. Hit rate climbed over the first month exactly as designed, and the
cost graph did what the business case said it would. Complaints climbed at the same time and
nobody connected the two for a while, because the cache dashboard had hit rate, latency saved
and cost saved on it, and there was no panel that could have shown the problem. A false hit is
invisible from inside the cache: the query matched, the answer was served, the latency was
excellent.

We found it through a support escalation about an answer that referenced a contract the customer
had never signed. It was a real answer, correctly generated, for a different customer's nearly
identical question."""},
  {"by": "maintainer", "body": """Rejecting this one, and writing the reason out properly so the
next person to propose it reads this thread instead of re-arguing it.

**One.** The metric it moves is not a constraint here. Mean cost per query 0.0039, mean latency
34.62 ms. The win side of the ledger is a number nobody is asking about.

**Two.** The metric it damages is the one we are worst at. We answer all 36 unanswerable
questions and abstain from none. The characteristic failure is fluent wrongness, and a near-miss
hit is a machine for producing more of it.

**Three**, which decides it. The proposal's falsifier is the false-hit rate, and you cannot
measure one without labelled near-miss pairs: close in embedding space, different correct
answers. We have no such set, building it is most of the work here, and the moment you have it
you are holding a labelled set of confusable queries that is worth more spent on abstention.

**The condition under which this is right**, so it can be reopened rather than re-argued: real
traffic with a measured repetition rate, a working abstention path so a wrong cached answer has
something in front of it, and cost per query named as a constraint by somebody. With those three
it is a good idea. Here it is a good idea aimed at nothing.

Sofia's partitioning point is correct and it is not the reason. It fixes the disclosure and
leaves both earlier objections where they were. An objection can be right, fixable, and still not
the one that decides the question. Marking extension 5 **not now**, linking this thread."""},
  {"by": "aarav", "body": """Taking the rejection, and the part I want to write down is what I
was about to do.

I picked this because it explains in one sentence. It has a diagram, it has a number that goes
down, and a client nods at it. What I was actually going to sell was a saving of a tenth of a
cent per query, presented as architecture, on a system whose measured problem is that it answers
questions it should refuse.

What I will take to the client instead is the 36. That is a sentence too, it is shorter, and it
is about something they would care about if they knew it was true."""},
 ],
},
{
 "category": CAT, "author": "lena",
 "title": "Idea: learn alpha per query class instead of shipping one global compromise",
 "body": """Extension 3 on the research page, and the sweep in
[notebook 04](/fde-academy-lab/advanced-rag-lab/blob/main/notebooks/04_retrieval_methods_and_reranking.ipynb)
is the argument for it. A single global alpha is fitted to the average query and there is no
average query.

The alpha sweep at k=8, alpha being the dense weight:

| alpha | evidence_recall | ndcg | answer_correct |
|---|---|---|---|
| 0.1 | 0.7444 | 0.4152 | 0.4156 |
| 0.2 | 0.7645 | 0.4767 | 0.4115 |
| 0.3 | 0.7766 | 0.5047 | 0.4033 |
| 0.4 | 0.7790 | 0.5461 | 0.3992 |
| 0.5 | 0.7790 | 0.5967 | 0.3992 |
| 0.7 | 0.7778 | 0.6102 | 0.3951 |

The shipped default is 0.2. The fusion note already says which queries each leg wins: exact
identifiers such as `PagerDuty-4471` and `ap-southeast-2` go to the lexical leg, paraphrase and
inference over incident prose go to the dense one. Those are different queries and they are
being served by one constant.

**Hypothesis.** A router that picks alpha per query class beats the best global alpha by at least
3 points of evidence recall on the 207 answerable, and the gain holds on the frozen slice.

**Metric and slice.** `evidence_recall` at k=8, reported per class as well as overall, because a
router that helps every class equally is a router that has learned nothing about class.

**Effect that would count.** +3 points over the best global alpha, interval clear of zero.

**Cost.** A classifier, which is a second system with its own precision and recall, and its own
failure concentration. The page's warning is the right one to watch: the router's errors landing
on exactly the queries that needed help.""",
 "replies": [
  {"by": "dan", "body": """This should pay well, because the two legs are so unequal here.

Repeating what I took from the deck material, and I have since learned both halves of it were
retracted — see the maintainer's reply below:

> The dense leg is the weak one on this corpus, so a global alpha of 0.2 is us holding the weak
> leg down, and per-class weighting is how you stop paying for it on the queries where it is
> useless. Equal-weight RRF loses to BM25 alone here for the same reason. Give a weak voter a
> full vote and you get a worse result than not asking it.

Leaving it up rather than editing it out, because it is the reasoning I actually had."""},
  {"by": "maintainer", "body": """Both of those sentences were published in ADR-0007, with the mechanism in ADR-0003, and both
were retracted on 1 September. They are the two most-repeated wrong things in this repository, and
Dan is repeating them in good faith from material we shipped, which is why the correction goes
here rather than in a footnote.

Measured, at k=8 after the cross-encoder:

| arm | evidence_recall | ndcg |
|---|---|---|
| BM25 alone | 0.7118 | 0.3639 |
| Dense (LSA) alone | 0.7733 | 0.6055 |
| Equal-weight RRF | 0.7742 | 0.5302 |

- `bm25 → dense`, evidence recall **+0.0616**, interval (+0.0382, +0.0870). Real.
- `bm25 → rrf`, evidence recall **+0.0624**, interval (+0.0407, +0.0857). Real.

The dense leg is the **stronger** one, and RRF beats BM25 alone rather than losing to it. LSA, a
truncated SVD over TF-IDF, wins because the questions are paraphrase over incident prose where
the passage and the question share meaning and almost no vocabulary, and BM25 scores term
overlap. The corpus decides it, not the method.

[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
carries the correction. Lena, note that your own proposal has alpha as the **dense** weight, so
the shipped 0.2 is four fifths lexical, which is four fifths of the weaker leg."""},
  {"by": "marcus", "body": """Separately from the retraction, there is a ceiling on this and it
is already computed. `scripts/failure_overlap.py`, on the 207 answerable at k=8:

```
dense leg misses                95
lexical leg misses             102
both miss                       92
only dense misses                3
only lexical misses             10

P(lexical also misses | dense misses)   0.9684
Jaccard of the two failure sets         0.8762
```

Thirteen questions of 207 are recoverable by any fusion rule at all, because on the other 92 both
legs have already failed and no weighting of two wrong answers produces a right one. Thirteen of
207 is about six points, and that is the **oracle** figure: a router that is perfect, on a
weighting scheme that actually surfaces those thirteen inside k=8.

Your hypothesis asks a learned classifier to capture roughly half of a theoretical maximum that
assumes both of those. And your setup import is the thing to be careful about: per-class
weighting pays on corpora where the legs fail on different queries. At a conditional of 0.9684
these two legs fail on the same queries."""},
  {"by": "lena", "body": """I want to push back on the method rather than the conclusion, because
this is the same move as the independence claim retracted on 1 September.

The independence claim took a distribution, did arithmetic on it, and published "independence
predicts 0.6838, a 21-point shortfall" as a finding. It was wrong, and it was wrong in a way that
was invisible precisely because arithmetic feels safer than measurement. Deriving a six-point
ceiling from an overlap table and treating the proposal as settled by it is the same shape of
reasoning, one retraction later, in a thread where we have just finished correcting two other
things people believed because they were written down."""},
  {"by": "marcus", "body": """That is a fair challenge and the distinction matters, so let me be
precise about it.

The retracted claim was a **finding** stated as a result, and its input distribution was
fabricated: 128 single-hop, 61 two-hop, 18 three-plus, numbers that were never counted. The
corrected version uses the real distribution of gold pieces per question, predicts **0.4603**
against a measured 0.4686, and lands **+0.0083** above it. The
[note](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/multi-hop-independence.md)
carries both. So the arithmetic was never the problem; the unmeasured input was.

What the overlap table gives here is a **ceiling**, not a finding, and the difference is what you
can do with it next. A finding you either believe or you do not. A ceiling is falsifiable in one
afternoon, and here is the run:

Sweep the six alpha values already in the table. For each of the 207 answerable questions, record
whether **any** alpha retrieves gold evidence that alpha=0.2 misses. Take the union. That is a
per-query oracle, measured rather than derived, and it is the strict upper bound on every router
anyone could build over this grid, because no classifier beats knowing the answer.

If the oracle clears 3 points, your proposal is alive and the classifier is the next question. If
it does not, no router clears the bar, and the classifier is a second system built to chase a
gain that is not in the grid. Either way it costs a sweep and no model."""},
  {"by": "lena", "body": """Taking that, and taking the correction above it, which is the more
uncomfortable one: my proposal's motivation was the two retracted sentences. I did not quote
them, and I built the case on the prior they came from.

Narrowed version, replacing the one in the post:

- **Hypothesis.** The per-query oracle over the existing alpha grid beats alpha=0.2 by at least
  3 points of evidence recall on the 207 answerable.
- **Metric and slice.** `evidence_recall` at k=8, plus the count of questions where any alpha
  recovers gold that 0.2 misses, which is the number that explains the result either way.
- **Effect that would count.** 3 points. Below it the classifier does not get written, and that
  is the outcome I am now expecting given the 0.9684.
- **Cost.** One sweep. No classifier, no router, no second system to evaluate.

And the condition under which the original idea comes back, so it is on the record: legs with a
materially lower failure Jaccard than 0.8762. EX-15 swaps LSA for a real sentence encoder, and if
the legs become complementary the whole argument reopens with different numbers. At which point
somebody should re-run the overlap before proposing the router, rather than after."""},
 ],
},
]
