"""Math & Theory threads: four derivations, each one attached to a decision somebody made badly.

A derivation thread is worth seeding only if the algebra changes what somebody does on Monday.
So each of these starts from a real proposal — swap the nDCG discount, resample documents to get
a tighter interval, explain a multi-hop shortfall, tune BM25's saturation — and the derivation is
what kills or saves the proposal. The confident wrong answer in each thread is the one a
competent engineer gives, because those are the ones that survive a design review.

Two of the four exist because this repository published a wrong number and had to withdraw it.
The retractions are better teaching material than the corrections were, and they are used as
such rather than hidden: in both cases the arithmetic was right and the inputs were never
checked against the corpus.

Every figure quoted is either in the eval baseline or in a file under docs/ that a reader can
open, and the derived quantities show their working so the reader can redo them.
"""
from __future__ import annotations

CAT = "Math & Theory"

THREADS = [
{
 "category": CAT, "author": "priya",
 "title": "Why 1/log2(i+1) and not 1/i for the nDCG discount, and is the log base load-bearing?",
 "body": """Someone in review looked at the scorecard and said our nDCG "does not punish burying
the answer at rank 8 hard enough". The two numbers side by side do look odd:

| | shipped default `weighted α=0.2, k=8` |
|---|---|
| evidence recall | 0.7645 |
| nDCG | 0.4767 |
| full-chain recall | 0.4686 |

I want to propose swapping the discount to $1/i$, which is steeper and would, I think, make the
metric agree with what the reviewer feels. Before I do that I want to understand three things I
have never been able to answer properly.

1. Why is the discount $1/\\log_2(i+1)$ rather than any other decreasing function?
2. Is the **base** doing work? If I use $\\ln$ instead of $\\log_2$, do my numbers move?
3. What is the **+1** for, beyond stopping $\\log_2 1 = 0$ in the denominator at rank 1?

What I have already done: read the implementation in
[`raglab/metrics.py`](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/metrics.py), which is

```python
dcg += 1.0 / math.log2(i + 1)
ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(items), k) + 1))
```

so the ideal ranking is the gold pieces packed into positions 1..m, capped at k. And I checked
the fusion table, where the dense leg alone scores nDCG 0.6055 against equal-weight RRF at
0.5302 while their evidence recall is 0.7733 and 0.7742. The two metrics are ordering those
configurations differently, and I would like to know whether the discount is the reason before I
go and change it.""",
 "replies": [
  {"by": "wei", "body": """The base is load-bearing and I would not touch it. $\\log_2$ encodes
the examination model the measure was built around — attention roughly halves as you go down the
list, and base 2 is what makes a doubling of rank cost one unit of discount. Move to natural log
and your numbers shift, and worse, they stop being comparable to every published nDCG number in
the literature.

We hit exactly this at my last place. Someone reimplemented the metric with $\\ln$ in a
dashboard, the dashboard disagreed with the offline eval by a constant factor, and it took a
fortnight to find. After that we froze base 2 in the shared library and nobody was allowed to
pass a base argument.

On your actual question: $1/i$ is fine mathematically, it is just harsher. If the reviewer wants
harsher, give them harsher."""},
  {"by": "marcus", "body": """The base does not survive the normalisation, and it is one line of
algebra.

$$\\log_b(x) = \\frac{\\ln x}{\\ln b} \\quad\\Longrightarrow\\quad \\frac{1}{\\log_b(i+1)} =
\\frac{\\ln b}{\\ln(i+1)}$$

So every term of DCG under base $b$ is the natural-log version multiplied by the same constant
$\\ln b$. That constant factors out of the sum, so

$$\\mathrm{DCG}_b@k = \\ln b \\cdot \\mathrm{DCG}_e@k, \\qquad
\\mathrm{IDCG}_b@k = \\ln b \\cdot \\mathrm{IDCG}_e@k$$

and in the ratio it cancels exactly:

$$\\mathrm{nDCG}_b@k = \\frac{\\ln b \\cdot \\mathrm{DCG}_e}{\\ln b \\cdot \\mathrm{IDCG}_e}
= \\mathrm{nDCG}_e@k$$

**nDCG is invariant to the log base.** Raw DCG is not, which is very likely what the dashboard at
Wei's last company was disagreeing about — an unnormalised DCG, or a DCG shown next to an nDCG.
Two systems can never swap places because of the base.

The same argument kills a whole family of worries: any discount multiplied by a positive constant
gives identical nDCG. What changes the answer is a discount with a different **shape**, and
$1/i$ is a different shape, not a rescaling."""},
  {"by": "lena", "body": """There is theory here as well as convention. Wang et al., *A
Theoretical Analysis of NDCG Type Ranking Measures* (COLT 2013), study exactly which discount
functions make NDCG a consistent measure — that is, whether maximising the measure in the limit
recovers the correct ranking — and the standard logarithmic discount is the one that comes out
well. I would read that as settling it: the log discount is the correct choice, and $1/i$ sits
outside the class the theory endorses.

Priya, on that basis I would drop the proposal and tell the reviewer the metric is right."""},
  {"by": "maintainer", "body": """Careful with that one, Lena. The Wang analysis is about a class
of discount functions under complete relevance judgements over the candidate set. Our IDCG is
computed over the gold pieces we happen to have, capped at $k$ — `min(len(items), k)` in the
implementation Priya quoted — which is a different object.

The binding constraint on our nDCG is the judgement set, not the discount. A consistency theorem
stated for fully judged rankings does not transfer to a pooled measure merely because the formula
matches, and using it to close the question here would close it for the wrong reason."""},
  {"by": "maintainer", "body": """Marcus has the algebra, so the base question is closed. The
interesting part of Priya's post is the third one.

**What the +1 does, which is not avoiding a division by zero.** A discount is a weighting over
positions, and its only meaning is the *ratios* between them.

| rank $i$ | 1 | 2 | 3 | 4 | 8 |
|---|---|---|---|---|---|
| $1/\\log_2(i+1)$ | 1.0000 | 0.6309 | 0.5000 | 0.4307 | 0.3155 |
| $1/i$ | 1.0000 | 0.5000 | 0.3333 | 0.2500 | 0.1250 |

The +1 anchors rank 1 at $\\log_2 2 = 1$, so the top position takes the full gain and every other
position is a fraction of it. Remove it and rank 1 has no finite weight for the rest to be a
fraction *of*. The two rows agree at ranks 1 and 3 and nowhere else, so the choice is about how
steeply the middle of the list falls away.

**What the choice is worth.** Four gold pieces, ideal ranking 1,2,3,4, a system that lands them
at 1,2,5,8: $2.3332/2.5616 = 0.9109$ under the log discount against $1.8250/2.0833 = 0.8760$
under $1/i$. Three points of extra severity on a two-rank displacement, nothing like the size of
the disagreement the reviewer is describing.

**The condition under which $1/i$ would be right.** If your interface shows one result and nobody
scrolls, examination probability does collapse faster than logarithmically, and then the response
is to stop using a full-list measure rather than steepen one. Report success@1 or MRR.

**And the real answer to the reviewer.** nDCG cannot see *sufficiency*: a question needing four
pieces scores well from one piece at rank 1 with near-duplicates behind it. That is why full-chain
recall sits beside it, 0.7645 against 0.4686. The discomfort is real and the discount is not where
it lives.

Pooling bias is in [mathematics.md M3](/fde-academy-lab/advanced-rag-lab/blob/main/docs/06-interview-prep/mathematics.md).""",
   "accepted": True},
  {"by": "priya", "body": """Withdrew the proposal and left the discount alone. Reported
full-chain recall next to nDCG on the scorecard instead, which is what the reviewer was reaching
for.

The thing that surprised me came out of doing that. Across the α sweep at k=8, evidence recall is
flat from 0.3 upward — 0.7766, 0.7790, 0.7790, 0.7778 at α = 0.3, 0.4, 0.5, 0.7 — while nDCG
climbs 0.5047 → 0.5461 → 0.5967 → 0.6102 over the same range, and answer correctness drifts down
0.4033 → 0.3992 → 0.3992 → 0.3951.

So the metric that moves most across the sweep is the one nobody was tuning, and the one the user
sees moves the wrong way. I went in wanting to make nDCG stricter and came out understanding that
I had been reading it as though it were a proxy for the answer, which it is not."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "The paired bootstrap gives a much tighter interval if I resample documents. Which one is lying?",
 "body": """I am trying to defend moving the fusion weight from α=0.2 to α=0.5. The evidence
recall delta is +0.0145 with ci (+0.0048, +0.0254), which clears, but it is close enough to the
edge that I wanted a second opinion on the interval.

So I tried resampling differently. Instead of resampling the 243 questions with replacement, I
resampled the retrieved chunks — I have 2,430 chunks in the index and eight in each window, and
it seemed obviously better to bootstrap over the larger pool. The interval came back materially
narrower, comfortably clear of zero.

Two versions of the same comparison and two different degrees of confidence. Before I put either
in a PR I would like to know which one I am allowed to believe, and why.

What I have already checked:

- Both versions compare the same question set, same k, same reranker. One change per comparison.
- The paired version is genuinely paired. I am resampling a list of question ids and reading both
  systems at each id, not resampling each system separately.
- The [evaluation protocol](/fde-academy-lab/advanced-rag-lab/blob/main/docs/04-evaluation/protocol.md)
  says "paired bootstrap over queries, 1,000 resamples". The implementation in `raglab/metrics.py`
  defaults to `n_boot=2000, seed=11` and `run_eval.py` does not pass one, so the scorecard numbers
  are 2,000-resample numbers while the protocol says 1,000.

The last point is probably a docs bug rather than a statistics question, but it is the kind of
thing that makes me distrust my own reading of the rest.""",
 "replies": [
  {"by": "aarav", "body": """Take the tighter one. You have 2,430 chunks and 243 questions, and
an estimate built from ten times as many units is ten times better supported — that is the whole
reason we bootstrap rather than eyeballing means. The interval excludes zero on both readings
anyway, so the direction is not in question and you are arguing about how confident to sound in
the PR description.

Write it up with the narrow interval, note the wide one in a footnote if you want to be scrupulous,
and ship. We have spent longer on this thread than the change took."""},
  {"by": "sofia", "body": """Before anyone answers "which one", I want the question stated
properly, because I do not think the two intervals are estimates of the same thing.

The metric averages over questions. Every row in the eval output is one question. So what is the
document-level resample estimating — the variance of a per-question average under a different
draw of questions, or something else entirely? If the resampling unit is not the unit the metric
averages over, the number that comes back is an interval around a quantity nobody asked for, and
whether it is narrow is beside the point."""},
  {"by": "marcus", "body": """Sofia has it, and the algebra says why.

You are estimating the mean of the per-question differences $d_i = a_i - b_i$ over $n$ questions.
For an i.i.d. sample,

$$\\mathrm{Var}(\\bar d) = \\frac{1}{n}\\mathrm{Var}(d), \\qquad
\\mathrm{Var}(d) = \\mathrm{Var}(a) + \\mathrm{Var}(b) - 2\\,\\mathrm{Cov}(a,b)$$

Pairing is the $-2\\mathrm{Cov}(a,b)$ term. Two configurations of the same retriever agree on
most questions, so that covariance is large and positive and it removes most of the
between-question difficulty variance, which is the variance that swamps everything else. That is
the entire reason a paired test detects a +0.0145 that an unpaired one would call noise.

Now the document resample. Chunks inside one window are not independent draws from your 2,430.
They were selected by the same retriever, conditioned on the same query, and they compete for the
same eight slots. Treating $m$ of them as $m$ independent units divides the variance by an $n$
you do not have, so the interval shrinks by roughly the square root of the fiction. You have the
same opinion back with an inflated denominator under it.

One more thing about the shape of your interval. Per-question evidence recall is gold pieces
found over gold pieces needed, and the piece counts are `{1: 21, 2: 59, 3: 21, 4: 100, 6: 6}`
over 207 answerable questions, so $d_i$ lives on a coarse lattice of halves, thirds, quarters and
sixths. The bootstrap distribution is lumpy. Do not read the endpoints as though the fourth
decimal carried information."""},
  {"by": "maintainer", "body": """Marked Marcus's. The rule it generalises to, and the case where
Dan's instinct is right, because it is right somewhere.

**The resampling unit is the unit you want to generalise over.** Your PR claims that on another
draw of 243 questions the delta would still be positive. Questions are what varies between the
world you measured and the world you are claiming about, so questions are what you resample. The
index does not vary between those two worlds.

**When resampling documents is correct:** when the estimand is a per-document property and the
documents were drawn independently of the retriever, as in annotation precision over a random
pool. The test is whether you could have drawn a different set of those units without changing
anything else. You cannot draw a different top-8 without changing the retriever.

**What the interval does not cover**, which should be stated every time one is quoted
([mathematics.md M6](/fde-academy-lab/advanced-rag-lab/blob/main/docs/06-interview-prep/mathematics.md)):

- *Annotation error.* Not a factor here, gold being true by construction. Elsewhere it is the
  floor under every number you report and the bootstrap cannot see it.
- *Multiple comparisons.* The α sweep alone is six configurations on three metrics, and at 95%
  something clears by luck. That is what the frozen slice is for.
- *Non-stationarity.* The interval assumes these 243 questions look like your traffic.

**And significance is not the shipping criterion.** Every pair in this table is inside the noise
band on `answer_correct`. Your +0.0145 is real and has never been shown to move what a user
experiences. Say both in the PR.

Dan is right about the drift too, and that deserves its own answer below.""",
   "accepted": True},
  {"by": "maintainer", "body": """On the 1,000 against 2,000: the code default is `n_boot=2000`,
`run_eval.py` does not override it, and the prose in the protocol says 1,000. So the scorecard
numbers are 2,000-resample numbers.

It moves no conclusion. More resamples give a slightly more stable percentile of the same
empirical distribution, and by 1,000 the endpoints have long stopped moving in any way that would
change a verdict. But a protocol that does not match the code cannot be audited, and somebody will
eventually reimplement from the prose and get endpoints that differ from ours in the third decimal
for a reason nobody can find. Open it against the
[protocol](/fde-academy-lab/advanced-rag-lab/blob/main/docs/04-evaluation/protocol.md) rather than
changing the default, since the code is the version that has been running."""},
  {"by": "tomas", "body": """Reading this from the on-call side. If the defensible delta is
+0.0145 evidence recall and nothing measurable on answer correctness, then from where I sit the
change has a cost and no observable benefit: a new default to remember, a new number in the
runbook, and a config value that differs from every notebook screenshot in the repo.

I would leave α at 0.2 and write down why. Not because the statistics are wrong, but because a
change nobody can see is a change nobody can validate at 3am when they are trying to work out
whether retrieval is behaving."""},
  {"by": "dan", "body": """Kept the default at 0.2 and wrote the note.

What I actually did: rewrote the comparison with the paired-over-queries interval, added the line
that every fusion pair is inside the noise band on answer correctness, and filed the 1,000 versus
2,000 mismatch as a docs issue.

What surprised me is how convincing the wrong interval was. It was narrower, it was produced by
the same function, it had the same shape, and nothing in the output would have told a reviewer it
was answering a different question. I would have taken Aarav's advice and shipped it, and the
review would have passed, because a reviewer sees the interval and not the resampling unit."""},
 ],
},
{
 "category": CAT, "author": "lena",
 "title": "I cannot reproduce the retracted multi-hop shortfall. Where did the 21 points come from?",
 "body": """I was reading the older version of the multi-hop note, which said the corpus splits
128 single-hop / 61 two-hop / 18 three-or-more, that independence at $p = 0.7645$ therefore
predicts **0.6838**, and that measured 0.4686 is about 21 points below it — so retrieval failures
inside a question are correlated.

I set out to reproduce it and I cannot get near it. The corpus reports gold evidence pieces per
answerable question as

```
pieces   questions
  1         21
  2         59
  3         21
  4        100
  6          6
           ---
           207
```

and the `hops` field is 77 one-hop, 130 two-hop. Neither of those is 128/61/18, although all three
sum to 207.

Doing the obvious calculation over the piece distribution:

$$P(\\text{full chain}) = \\frac{1}{207}\\sum_k n_k\\, p^k, \\qquad p = 0.7645$$

gives **0.4603**, against a measured 0.4686. That is $+0.0083$ *above* independence, not 21 points
below it.

I am fairly sure the correlated-failure story is still the right one and my arithmetic has gone
wrong somewhere. Barnett et al. (CAIN 2024, arXiv:2401.05856) catalogue seven failure points in
production RAG systems and the whole framing there is that failures compound through the pipeline
rather than occurring independently, which is what the retracted paragraph was describing. So I
would expect a shortfall. Where is my error?""",
 "replies": [
  {"by": "wei", "body": """Your arithmetic is fine and your conclusion is the one that is off.
Independence always overestimates multi-hop retrieval — this is one of the few things everybody in
the field agrees on. Chunks that answer the same question sit near each other in the corpus and
near each other in the embedding space, so when the retriever is having a bad day on a question it
is having a bad day on all of that question's evidence at once.

We saw this constantly on our production system. Multi-hop queries did not degrade gracefully,
they fell off a cliff, and the fix was query decomposition rather than anything you can do with
$k$. If your numbers say otherwise, the thing to check is the measurement, because 0.4603 as a
null is almost certainly not the null you want.

Bluntly: a computation that says failures inside a question are independent is a computation with
a bug in it."""},
  {"by": "marcus", "body": """Wei, the sign is wrong, and it is worth being careful about because
it is the crux.

Take a question needing $k$ pieces, $X_j$ the event that piece $j$ is retrieved. If the pieces are
**positively** correlated — the co-location story you are describing, where a retriever that finds
one finds the rest — then

$$P\\!\\left(\\textstyle\\bigcap_j X_j\\right) > \\prod_j P(X_j) = p^k$$

At perfect correlation the retriever gets all of them or none, so full-chain recall would equal
$p = 0.7645$, far *above* the 0.4603 null. Correlated failure inside a question raises full-chain
recall. A shortfall *below* independence needs **negative** dependence.

Which does exist here, and nobody mentions it: at $k=8$ the pieces of one question compete for the
same eight slots, so finding one consumes a slot the next one needed. Two effects with opposite
signs, and the measurement says they roughly cancel here.

One caveat on Lena's null, in her favour. `evidence_recall` 0.7645 is the mean over questions of a
per-question fraction, so using it as a per-piece marginal weights every question equally rather
than every piece equally. The
[multi-hop note](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/multi-hop-independence.md)
reports the micro rate too, pieces found over pieces total, 0.7257 — and the null at that rate is
0.4007, which measured clears by +0.0679.
Both choices of $p$ put the measurement at or above independence, so the conclusion does not turn
on which one you pick."""},
  {"by": "marcus", "body": """Separately, I went and found where 0.6838 came from, because a
number that specific is usually arithmetic on something rather than invention.

Take the retracted mixture exactly as written — 128 one, 61 two, 18 three — and exponentiate at
$p = 0.7645$:

$$\\frac{128(0.7645) + 61(0.7645)^2 + 18(0.7645)^3}{207}
= \\frac{97.856 + 35.652 + 8.043}{207} = 0.6838$$

That reproduces the retracted figure to four decimals. So the formula was right, the value of $p$
was right, and every step of the arithmetic was right. The mixture was the only wrong input, and
it was wrong in the direction that mattered most: 128 single-piece questions of 207 where the
corpus has 21. That one substitution is nearly the whole 21 points.

For completeness, exponentiating the real `hops` distribution instead of pieces:

$$\\frac{77(0.7645) + 130(0.7645)^2}{207} = 0.6514$$

Also not the metric. `full_chain_recall` requires every gold **piece**, and a two-hop question here
routinely carries four of them, so the exponent is `len(gold_map)` and never `hops`."""},
  {"by": "dan", "body": """I quoted the 21-point version in a design review last week. Somebody
asked why our multi-hop numbers were weak and I said independence predicts 0.68 and we measure
0.47, so the failures are correlated, and it landed well because it sounded like we had done the
work.

I had not done the work. I had read a confident sentence in a doc and repeated it, which is the
same thing I did with Wei's reply at the top of this thread before Marcus posted."""},
  {"by": "maintainer", "body": """Marked Marcus's reconstruction. Three things, the third being
the one to carry away.

**Two different independence questions were conflated, and only one of them was measured.**

- *Between the pieces of one question.* Does retrieving piece 1 tell you anything about piece 2?
  `full_chain_recall` against $p^k$ tests that, and the answer here is no: +0.0083 at the macro
  rate, +0.0679 at the micro rate.
- *Between the legs of the retriever on one question.* Does the lexical leg fail where the dense
  leg fails? Also measured, and the dependence is enormous: P(lexical misses | dense misses) =
  0.9684, Jaccard 0.8762, 92 of the 95 dense-leg misses also missed by BM25.

Wei is describing the second, which is why it feels so solid, and it is also why fusion adds so
little here ([ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)).
It says nothing about the first.

**The condition under which the retracted conclusion would have been right.** If the mixture were
128/61/18, then 0.6838 is the right null and 0.4686 is a genuine 21-point shortfall demanding an
explanation. Given its inputs the reasoning was sound, which is what made it survive: everyone who
read it checked the argument and not the inputs.

**A weighted average is only as good as the distribution it is weighted over, and that distribution
has to come from a query.** This one was never read off the corpus, and it summed to 207, which is
what made it look checked. So there is now
[`scripts/independence.py`](/fde-academy-lab/advanced-rag-lab/blob/main/scripts/independence.py),
one command, and `tests/test_measurements.py` fails if the docs drift from the corpus. Full
retraction at the bottom of the
[multi-hop note](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/multi-hop-independence.md).

Dan — the recovery is the useful half. Go back to that review and correct it.""",
   "accepted": True},
  {"by": "lena", "body": """Reran it and the mechanism is what Marcus says.

The part that unsettles me is my own near-miss. I had already half-decided the exponent should be
`hops`, since that is the field with "hop" in the name and the retracted text talked about hops.
That path gives 0.6514, which is close enough to 0.6838 that I would have read it as confirmation,
written "reproduced, small discrepancy from rounding" and moved on.

So the check that felt like verification would have reproduced a retracted number off the wrong
variable. Nothing about that was carefulness on my part. What saved me was running the calculation
the metric actually implements first, getting an answer that disagreed with the doc, and posting
instead of assuming the error was mine.

Withdrawing the Barnett citation too. It is a taxonomy of where production systems fail, and I
was using it as though it made a claim about statistical dependence between gold pieces, which it
does not."""},
 ],
},
{
 "category": CAT, "author": "tomas",
 "title": "What do BM25's k1 and b actually model? Deciding whether to freeze them or open them for tuning",
 "body": """Ops question with a maths answer underneath it, so posting it here.

The lexical leg has the worst nDCG on the board:

| leg, k=8, cross-encoder | evidence recall | nDCG |
|---|---|---|
| BM25 alone | 0.7118 | 0.3639 |
| Dense (LSA) alone | 0.7733 | 0.6055 |

and its context precision falls away as we widen: 0.3029 at k=5, 0.2309 at k=8, 0.1948 at k=10.

Someone wants to open $k_1$ and $b$ for tuning. My instinct is to freeze both and write down why,
because a parameter that can be tuned will be tuned, at some point by somebody at 2am who is
trying to fix an unrelated incident, and I would rather that door were shut.

But I do not want to freeze them out of superstition. So: what do these two actually **model**?
Not "$k_1$ controls saturation and $b$ controls length normalisation", which is what every answer
I can find says and which tells me nothing about when a value is wrong. If they encode assumptions
about a corpus, I want to know which assumptions, so I can say whether ours holds and put that
sentence in the runbook next to the frozen values.""",
 "replies": [
  {"by": "wei", "body": """Set $b = 0$ and you can freeze the rest.

Length normalisation is a leftover from TREC newswire collections, where documents ranged from a
paragraph to a full wire report and you genuinely had to correct for it. Modern setups do not look
like that. We dropped $b$ to 0 on our production index and recall went up immediately, and it
stayed up. The 0.75 default came out of TREC-era tuning on collections none of us have ever seen,
and everybody has copied it since without re-deriving it.

$k_1$ I would leave at 1.2. That one does real work."""},
  {"by": "dan", "body": """That matches what I had read, that 0.75 is a convention rather than a
derived value, and I have never seen anyone justify it beyond citing the person who cited it
before them. If dropping $b$ raised recall on a live index I would take that as settled evidence
and stop there.

Tomás, if you want a reason for the runbook, "measured in production and recall went up" is a
better one than most of what is written in ours. I would set $b = 0$, leave $k_1$ at 1.2, freeze
both, and spend the argument on the reranker instead, which from the k sweep looks like where the
movement actually is."""},
  {"by": "lena", "body": """Both parameters are derived, and the derivation answers Tomás's actual
question, so it is worth writing out.

**$k_1$ comes from the 2-Poisson model.** A document is drawn either from an "elite" distribution
for term $t$, meaning the document is about $t$, or from a background one. The log-likelihood ratio
between the two, as a function of the term count, is approximately

$$\\frac{tf}{tf + k_1}$$

Multiply by $(k_1 + 1)$ so a single occurrence scores exactly 1, and the term weight is

$$\\frac{tf\\,(k_1+1)}{tf + k_1}$$

which rises from 1 and flattens toward an asymptote of $k_1 + 1$. Two facts make $k_1$
interpretable rather than a knob:

- **The ceiling is $k_1 + 1$.** No term contributes more than that, however often it appears.
- **$tf = k_1$ is the half-saturation point.** Substitute it and you get $(k_1+1)/2$, exactly half
  the ceiling.

So $k_1$ is *the occurrence count at which a term has spent half the evidence it will ever be
allowed to spend*. At the default 1.2, against a ceiling of 2.2:

| $tf$ | 1 | 2 | 3 | 5 | 10 | 100 |
|---|---|---|---|---|---|---|
| weight | 1.0000 | 1.3750 | 1.5714 | 1.7742 | 1.9643 | 2.1739 |

**$b$ is an interpolation.** The denominator carries $1 - b + b\\frac{|d|}{\\mathrm{avgdl}}$, a
convex combination of 1 (ignore length) and $|d|/\\mathrm{avgdl}$ (correct fully for it). $b$ is
the mixing weight between "length says nothing about relevance" and "a document twice the average
length needs twice the term count to score the same"."""},
  {"by": "marcus", "body": """Worth adding what $b = 0$ costs, because "recall went up" is not the
whole event.

$b = 0$ asserts that a document ten times longer with ten times the occurrences is ten times the
evidence. The mechanism by which recall rises is that long documents flood the top-k — they have
more chances to contain any query term — so a gold chunk that was at rank 12 arrives at rank 8
behind four long distractors. Recall@k goes up, precision goes down, and if you only reported the
first one you would call that a win.

This repository has the same trade visible one $k$ step at a time on the lexical leg: context
precision 0.3029 at k=5, 0.2309 at k=8, 0.1948 at k=10, while evidence recall goes 0.6329 → 0.7118
→ 0.7279. Buying recall with precision is the easiest thing in retrieval to do by accident.

The other half is that $b$ means something different here from what it meant on Wei's index. We
retrieve 2,430 structural chunks, not 484 documents. $|d|/\\mathrm{avgdl}$ is a ratio between
*chunk* lengths, and chunks produced by one splitter have a far narrower length spread than the
documents they came from. There is much less for $b$ to correct, which is why the effect Wei
measured is real and why it will not reproduce at the same size here."""},
  {"by": "maintainer", "body": """Marked Lena's. Tomás asked which assumptions the parameters
encode, so here they are as runbook sentences.

- **$k_1$ encodes**: "beyond roughly $k_1$ occurrences, repeating a term is not further evidence."
  Wrong where repetition genuinely scales with relevance, which is rare in prose and occasionally
  true in tabular text.
- **$b$ encodes**: "longer units are longer because they cover more ground, not because they are
  more relevant." Wrong where length carries authority, and wrong the other way on a bimodal index.

**The condition under which Wei is right**, because he is describing something real. On a
single-field index of near-uniform length units, length carries no relevance signal and $b$ toward
0 is correct, and after chunking that is nearer to true than most people expect. What does not
transfer is the document-level case in
[mathematics.md M1](/fde-academy-lab/advanced-rag-lab/blob/main/docs/06-interview-prep/mathematics.md):
4,000-word reference pages beside 80-word error-code stubs, where no single $b$ serves a bimodal
length distribution and the real answer is to stop treating it as one corpus.

**And the question Tomás actually asked.** BM25's nDCG of 0.3639 is not primarily a $k_1$ or $b$
problem. The questions here are paraphrase and inference over prose, and the lexical leg
contributes on the exact-identifier slice, which is real and small. Saturation tuning will not
convert a leg answering a narrower question into the stronger one. Freeze both with the two
sentences above as the reason, and give the lexical leg its own eval slice.

Dan — "it raised recall in production, so it is settled" is the move to unlearn. Recall alone
cannot tell a better ranking from a wider net.""",
   "accepted": True},
  {"by": "tomas", "body": """Frozen, with the two runbook sentences above and Marcus's
chunk-length point written in beside the values. That is what I came here for — a reason a future
me can act on, sitting next to the numbers it explains.

The surprise was in the k sweep on the way there. BM25 evidence recall at k=3 is 0.4972 with the
cross-encoder and 0.3269 without it. The reranker is worth more than any argument in this thread
about the scoring function underneath it, and I had been treating it as the optional stage because
it is the expensive one.

Also filed a check that asserts the configured $k_1$ and $b$ match the values in the runbook, so
the freeze is a test rather than a note somebody has to read."""},
 ],
},
]
