"""Interview Prep and Reading Club — answers critiqued, papers argued with."""
from __future__ import annotations

THREADS = [
{
 "category": "Interview Prep", "author": "dan",
 "title": "Critique my answer: 'how would you separate a retrieval failure from a generation failure?'",
 "body": """Got asked this in a phone screen last week and I do not think I answered it well.
Here is roughly what I said, verbatim as best I remember:

> "I'd look at whether the right documents were retrieved. If they were and the answer is still
> wrong, it's the generator. If they weren't, it's retrieval."

The interviewer said "okay" and moved on, which I have learned is not a good sign. What is
missing?""",
 "replies": [
  {"by": "aarav", "body": """It is not wrong, it is just the definition restated. You have told
them what the two cases *are*, not how you would tell them apart in a system where you do not
have gold labels sitting there. In a screen that reads as knowing the vocabulary."""},
  {"by": "wei", "body": """Concretely, here is what I would have wanted to hear, and the
difference is that every step is something you could do on Monday.

**Ground it in an artefact.** "I'd take the twenty failing queries and, for each, check whether
the gold evidence is in the packed context." That is a script, not a principle.

**Name the case your rule misses.** Evidence retrieved *and* generator correct, but the answer is
still wrong — because the evidence was in the context and got lost. Position matters; a fact at
the middle of a long context is measurably less likely to be used than the same fact at the
start. So "retrieved" is not the same as "used", and your two-way split has a third case in it.

**Give the measurement that separates them.** Answer accuracy **conditioned on** correct
retrieval. If that is high, retrieval is your bottleneck and generation work is wasted. If it is
low, you can fix retrieval forever and nothing improves.

That last number is the whole answer, and it takes one line to compute."""},
  {"by": "marcus", "body": """Adding one thing that would move it from a good answer to a senior
one: say what you would do when the two cases are *entangled*.

They usually are. A generator that hedges when evidence is thin looks like a generation failure
and is caused by retrieval. A retriever tuned against a judge that rewards long answers looks
like a retrieval win and is caused by the judge.

So the honest version of the answer ends with: "and I'd want to check that my judge is not
producing the distinction — if the judge scores an abstention as a wrong answer, then a
retrieval failure and a generation failure are indistinguishable to my metric by
construction."
""", "accepted": True},
  {"by": "dan", "body": """The conditioned-accuracy number is the thing I did not have. I have
now run it on our eval set — answer accuracy given full-chain retrieval is 0.71 against 0.41
overall, so retrieval is the bottleneck here by a distance.

Which also means my rewrite of the answer can end with an actual number instead of a method. I
think that is the difference the interviewer was listening for."""},
  {"by": "maintainer", "body": """Marked Marcus's, though Wei's is the body of the answer and
should be read first.

The pattern worth extracting: Dan's original answer was **correct and unfalsifiable**. Nothing in
it could have been wrong, which is why the interviewer said "okay" and moved on — there was
nothing to follow up on. An answer that names a specific measurement invites the next question,
and the next question is where the marks are.

Fuller treatment in
[docs/06-interview-prep/evaluation.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/06-interview-prep/evaluation.md)."""},
 ],
},
{
 "category": "Reading Club", "author": "lena",
 "title": "Lost in the Middle (Liu et al., 2023) — does the U-curve survive on our corpus?",
 "body": """**Paper:** *Lost in the Middle: How Language Models Use Long Contexts*, Liu et al.,
TACL 2024 (arXiv 2307.03172).

**Claim:** model performance on retrieving a fact from context is highest when the fact is at
the beginning or end, and degrades in the middle — a U-shaped curve over position.

**Why it matters here:** if true, packing order is not cosmetic. Putting your best chunk in
position 4 of 8 is throwing away accuracy for free.

**What I want to test:** the paper uses much longer contexts than our 8-chunk window. Does the
effect appear at our scale, or is it a long-context phenomenon that does not apply below some
threshold?

Method: fix the retrieved set, permute gold evidence position across all 8 slots, measure answer
correctness at each position. n=243, so each position gets the full set.""",
 "replies": [
  {"by": "dan", "body": """Naive question — if we know the U-curve exists, why not always put the
top-ranked chunk first and the second-ranked last, filling the middle with the rest? Is there a
reason not to?"""},
  {"by": "lena", "body": """Not naive, and it is roughly what people do. Two reasons it is not
free.

It fights **prompt caching**. Cache hits require byte-identical prefixes; if your ordering
depends on this query's ranking, your prefix changes every query and you cache nothing. There is
a real cost tradeoff between optimal ordering and cache hit rate, and at scale the cache usually
wins.

And the U-curve is a statement about *average* behaviour over a benchmark. Applying it as a rule
assumes your model and your context length sit on the same curve, which is exactly what I am
trying to test rather than assume."""},
  {"by": "lena", "body": """Results. Answer correctness by gold position, 8-slot window:

| position | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| correct | 0.44 | 0.43 | 0.41 | 0.40 | 0.40 | 0.41 | 0.42 | 0.43 |

There is a curve and it is the right shape — ends above middle — but the amplitude is **0.04**,
and the paired interval on position 1 vs position 5 is [−0.01, +0.09]. It does not clear the
noise band.

So: consistent in direction with the paper, not established at this scale and this window.

Honest reading — we cannot confirm it here, and we also cannot refute it. n=243 across 8
positions is underpowered for a 4-point effect. What I *can* say is that at an 8-chunk window
the effect is small enough that ordering for cache-hit rate is the better trade, which is the
decision the experiment was actually for."""},
  {"by": "wei", "body": """That is the right conclusion and it matches what I have seen. The
paper's effect is large at 20+ documents and shrinks fast as the context gets shorter — which
makes sense mechanically, since the middle of an 8-item list is not far from either end in
attention terms.

The place it bites in production is not chunk ordering, it is **multi-turn conversation history**
where the relevant turn ends up buried in the middle of a long transcript. Same phenomenon,
different context, and much larger effect because the distances are much larger.""",
   "accepted": True},
  {"by": "marcus", "body": """One methodological note for anyone repeating this: Lena permuted
position with the retrieved set held fixed, which is the right design. The wrong design — and
the common one — is to compare naturally-occurring positions, where position correlates with
retrieval score, and you end up measuring score rather than position.

Holding the set fixed and permuting is what makes this a clean experiment rather than an
observational one."""},
  {"by": "maintainer", "body": """Marked Wei's, for connecting the finding to where it actually
costs money.

Reading Club standard, demonstrated here: the output of reading a paper is not a summary. It is
a **test on our corpus**, a number, and an honest verdict — which includes "underpowered, cannot
confirm or refute" when that is what the data says. Lena's conclusion is the least satisfying of
the three possible outcomes and it is stated plainly, which is the point.

Notebook `05` has the position-sensitivity cell if you want to re-run it."""},
 ],
},
]
