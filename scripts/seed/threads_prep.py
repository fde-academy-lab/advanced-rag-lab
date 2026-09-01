"""Interview Prep threads.

Each is built from a question somebody was actually asked, the answer they actually gave, and
the specific reason it did not land. The critique names a mental model from
interview-bank/mental-models.md so the fix is a procedure rather than a better paragraph.
"""
from __future__ import annotations

CAT = "Interview Prep"

THREADS = [
{
 "category": CAT, "author": "priya",
 "title": "Asked 'why is your recall number trustworthy?' and I froze. What was he actually after?",
 "body": """Fourth round, staff-level infra role. I had just said our evidence recall was 0.76.
He asked, flatly:

> "Why should I trust that number?"

I said something about having a held-out set and using bootstrap intervals. He nodded and moved
on and I could tell it had not landed.

What was he actually asking? It felt like a trap and I could not find the shape of it.""",
 "replies": [
  {"by": "dan", "body": """That does sound like a trap. Was he questioning your competence, or the
methodology?"""},
  {"by": "marcus", "body": """Neither — he was checking whether you know what your number
*cannot* tell him, and "held-out set plus bootstrap" is the answer of someone who has read about
evaluation rather than run one.

The bootstrap gives you variance from **query sampling**. That is one of at least four sources
of error in a retrieval number, and it is usually not the largest. The other three:

**Annotation error.** If your gold labels are wrong, every resample is wrong identically. On most
real eval sets this is the ceiling and nobody measures it.

**Multiple comparisons.** Test twenty variants at 95% and one clears by chance. If you tuned
against the same set you are now reporting on, your interval is a fiction.

**Non-stationarity.** The interval assumes your query sample represents the traffic you care
about. It almost never does.

A staff interviewer asking "why should I trust that" is asking you to enumerate those unprompted.
Answering with the mechanism you *did* use, rather than the ones you did not, reads as not
knowing they exist."""},
  {"by": "wei", "body": """Adding the thing that would have turned this from a stumble into the
best answer of the round.

You had a genuinely strong card and did not play it: your gold evidence is **true by
construction**. The corpus is generated from a fact graph, so there is no annotator and therefore
no annotation-error floor. That is a property almost no candidate can claim, and it directly
answers "why should I trust it".

So the answer is:

> "Three reasons and one caveat. The eval set is generated from a fact graph, so gold evidence is
> true by construction — no annotator, no annotation-error floor, which is usually the ceiling on
> a number like this. Fifteen percent is frozen and was touched once. And every comparison
> carries a paired bootstrap interval over queries.
>
> The caveat is that it is a synthetic corpus, so the number describes that corpus and not
> retrieval in general. Where an effect fails to reproduce because the corpus lacks the
> precondition, we say so rather than reporting it as a finding."

That last paragraph is what makes the first three credible. A candidate who only lists strengths
is describing marketing.""", "accepted": True},
  {"by": "priya", "body": """The caveat being the thing that makes the rest credible is the part I
would not have got to on my own.

I have written it out and timed it — 55 seconds, which leaves room for the follow-up. Which I
assume is "so how would you evaluate on a real client corpus where none of that holds?" """},
  {"by": "aarav", "body": """That is exactly the follow-up, and it is the whole reason the
question gets asked in a deployment-heavy role. The answer is the one-week eval set: logs first,
manufacture second, adversarial slice third, and check the set discriminates before trusting
anything it says.

If three configurations you *know* differ score the same, the set is too easy and you have
measured nothing. That check takes an hour and saves the engagement."""},
  {"by": "maintainer", "body": """Marked Wei's.

The mental model that fires here is **name the denominator** — but at one level up from usual.
Normally it applies to *their* number. Here it applies to yours: n, unit of analysis, slice, and
then the sources of error the interval does not cover.

Worth internalising the general pattern: **a question shaped like a challenge is usually a
request for your limitations.** "Why should I trust that" is not adversarial. It is an invitation
to demonstrate you know where your own method stops working, and candidates who hear it as an
attack defend the number instead of characterising it.

Full treatment at
[docs/06-interview-prep/evaluation.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/06-interview-prep/evaluation.md)
E4, and the drill is `python interview-bank/practice.py --id E4`."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "'How would you cut our RAG bill by 60%?' — I said quantisation and he looked disappointed",
 "body": """Startup, senior engineer role, and the question was concrete:

> "Our RAG costs us about $40k a month. How would you cut that by 60%?"

I talked about quantising the vectors and using a smaller embedding model. He asked what fraction
of the bill that was and I did not know. Round ended shortly after.

In hindsight I answered a storage question when he asked a cost question. What should the
structure have been?""",
 "replies": [
  {"by": "tomas", "body": """You optimised the part you knew how to optimise. Extremely common and
the interviewer sees it instantly, because your first move told him which layer you actually work
at.

Before proposing anything: **ask where the money goes.** In almost every RAG system it is
generation tokens, by a distance. Embedding and storage are rounding errors at $40k/month unless
something is badly wrong."""},
  {"by": "wei", "body": """Right, and I would put numbers on it because that is what makes it an
answer rather than a hunch.

Typical split at that scale: **generation 70–85%**, retrieval infrastructure 5–15%, embedding and
storage under 5%. So the honest first sentence is:

> "I would want the breakdown first, because if it looks like a typical RAG bill then vectors and
> storage are under 5% and I could get them to zero without hitting your target."

Then the levers, in order of how much they move:

1. **Output tokens.** Usually the single largest line and the least examined. Shorter answers,
   stricter formats, a cap. Cheapest change on the list.
2. **Prompt caching.** Requires byte-identical prefixes, which makes context block ordering a
   cost decision. We measured a cache hit rate go 4% → 71% and cost per query down **58%** by
   moving a timestamp out of a system prompt. That one change is most of a 60% target.
3. **Model routing.** Not every query needs the big model. Route on a measured signal, not a
   guess.
4. **Rerank routing.** Run the cross-encoder only where the first-stage score gap is small — that
   is where reranking changes the outcome. Most of the rerank cost, small measured quality loss.
5. *Then* quantisation and storage, which is where you started.""", "accepted": True},
  {"by": "dan", "body": """The timestamp thing is almost funny. Five characters at byte 58 costing
two thirds of an inference budget.

Rewritten answer opens with "I would want the breakdown, and here is what I would expect it to
look like" — which also demonstrates I know the shape without having seen their data."""},
  {"by": "aarav", "body": """That is the move. Naming the expected distribution before they show
you theirs is a strong signal, and it has a second benefit: if their breakdown is *not* typical —
say embedding is 40% — you have just found the actual bug in the first two minutes, and that is a
much better outcome for both of you than a generic cost-reduction plan."""},
  {"by": "sofia", "body": """One caution on lever 3. Model routing changes answer quality per
segment, and if you route on cost alone you will quietly degrade a segment nobody is measuring.

Any routing proposal should come with "and I would measure quality per route", or you have
converted a cost problem into a quality problem that surfaces two months later as churn."""},
  {"by": "maintainer", "body": """Marked Wei's.

Two models fire here and they fire in order. **Whose budget** — name what each proposal spends
and saves. Then **name the denominator** — 60% of *what*, and what is the composition.

Dan's diagnosis of his own answer is correct and worth stating generally: **you answered the
question you knew how to answer.** Everyone does this under pressure, and the defence is the
ordering habit — ask for the composition before proposing a change to any component.

Cost model with the four token categories is notebook `07`. The cache incident is in the
Debugging Clinic."""},
 ],
},
{
 "category": CAT, "author": "sofia",
 "title": "The question I was not ready for: 'what would you have to see to abandon this design?'",
 "body": """Design round. I had walked through a permission-aware retrieval architecture and I
thought it went well — pre-filter, ACL as a column, query-time evaluation against source of
truth. She listened, then asked:

> "What would you have to see to abandon this design?"

I said something about revisiting if requirements changed, which is a non-answer and I knew it as
I said it.

I have never been asked this before and I suspect it is a strong question. What is it testing?""",
 "replies": [
  {"by": "lena", "body": """It is the strongest question on this thread and it tests exactly one
thing: whether your design is a **belief** or a **preference**.

A belief has falsifiers. A preference does not, which is why "I would revisit if requirements
changed" is a non-answer — it names no observation, only a hypothetical change of subject.

For your design specifically, three real falsifiers:

**The selectivity fallback never fires, or always fires.** You proposed filtered ANN with a
fallback to exact search below some filter selectivity. If in production it always falls back,
you have built a filtered index that is never used and should just do exact search. If it never
fires, your threshold is wrong or your ACL groups are less selective than modelled.

**Per-group recall variance is small.** Your whole argument for pre-filtering over post-filtering
rests on restricted users being badly served by post-filter k-collapse. If you measure per-ACL-
group recall and it is flat, that argument is not load-bearing here and post-filter's simplicity
wins.

**Permission-change latency turns out not to matter.** You pay a lookup per query to avoid a
stale-permission window. If the client's permissions change quarterly and their audit tolerance is
24 hours, you bought something nobody wanted with latency everybody pays.""", "accepted": True},
  {"by": "sofia", "body": """That third one stings, because I did not check it. I assumed the
stale-permission window was unacceptable because it *sounds* unacceptable, and I never asked how
often permissions actually change.

Which is the same error as tuning without measuring, just wearing a compliance hat."""},
  {"by": "marcus", "body": """It is precisely that error and it is worth naming as a class:
**assuming a requirement is binding because it is stated in strong language.** "Permissions must
be accurate" is not a latency requirement. "Revocation must take effect within N minutes" is, and
N is a number somebody has to say out loud.

Ask for N. If nobody can produce it, that is itself the finding — you are about to spend
engineering on an unquantified fear."""},
  {"by": "wei", "body": """Practical note: I now open design rounds by saying what would falsify
my choice, unprompted, before they ask. It changes the dynamic of the whole round — the
interviewer stops probing for weaknesses because you have handed them the list, and the
conversation moves to which falsifier is most likely, which is a far more interesting discussion
and one you are ready for."""},
  {"by": "maintainer", "body": """Marked Lena's. The model is **what would make this false**, and
Sofia's thread is the clearest demonstration of it in this category.

Wei's habit — volunteering the falsifiers before being asked — is the senior move and it costs
nothing. A design presented with its own kill criteria reads as engineering. A design presented
as correct reads as advocacy, and interviewers respond to advocacy by attacking it.

Falsifiers for the design decisions in this repository are in the ADRs, each under a "what would
change this decision" heading. ADR-0011 covers this one."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "How do I talk about a synthetic-corpus project without it sounding like a toy?",
 "body": """I want to use this project in interviews but I am worried about the obvious
objection: it is a made-up corpus, so how is it evidence of anything?

I do not have a good answer beyond "well, the engineering is real". Which is true and sounds
defensive.""",
 "replies": [
  {"by": "dan", "body": """Same worry. My instinct is to not mention that the corpus is synthetic
unless asked."""},
  {"by": "wei", "body": """Do not do that. If it comes out under questioning — and it will, because
"where did the data come from" is a standard follow-up — you have converted a neutral fact into
something you were hiding.

Lead with it, and lead with why it is a *choice*."""},
  {"by": "aarav", "body": """Say more about the framing? "It's a choice" is the part I cannot make
sound like anything other than a rationalisation."""},
  {"by": "lena", "body": """The framing is not that synthetic is as good as real. It is that
synthetic buys you a property real data cannot, and you traded deliberately.

> "The corpus is generated from a fact graph, which means gold evidence is true by construction.
> There is no annotator, so there is no annotation-error floor under any number — when a metric
> moves, the system changed rather than the labelling. On a real corpus your ceiling is your
> annotator's accuracy and you usually cannot measure it.
>
> The cost is that some effects cannot be measured at all. Two of our three headline findings are
> exactly that — an effect that did not reproduce because the corpus lacks the precondition. We
> report those as findings about the eval set rather than about retrieval."

That second paragraph is what makes it not a rationalisation. You are naming what you gave up.""",
   "accepted": True},
  {"by": "marcus", "body": """And there is a sharper version for a senior room, which is to point
out that **the objection applies to their eval set too, and they probably have not noticed.**

Most eval sets are built by a generator, because generators are easier to write than annotation
projects. A balanced generator cannot measure imbalance failures, so a whole class of real
failures is invisible to it and everybody concludes the failure is rare.

Saying that turns the question around without being combative — you are not defending your
corpus, you are describing a property of eval sets, and theirs is in scope."""},
  {"by": "priya", "body": """Used a version of this last week. The interviewer's reaction was to
ask how we would detect a construction error — a fact placed in a document the fact graph does not
record — which nobody had asked me before and which is a genuine hole.

Answer is that it is silent, because there is no annotator to disagree, and the test is manual:
sample gold pairs and check by hand that the fact is present in the cited chunk. Nobody has done
it. Being able to say "that is a real gap and here is the test nobody has run" went down better
than any prepared answer would have."""},
  {"by": "maintainer", "body": """Marked Lena's, and Priya's follow-up is the reason this thread is
worth reading twice.

The pattern: **the strongest answer about a limitation is one that names a limitation the
interviewer did not.** It cannot be faked, because you can only do it if you have thought about
where your own thing breaks.

Priya's construction-error point is documented in
[client-zero.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/00-orientation/client-zero.md)
and is now the reason that section exists."""},
 ],
},
]
