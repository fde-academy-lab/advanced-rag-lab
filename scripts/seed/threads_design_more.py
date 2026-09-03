"""Three more Design Reviews: a plan that is too big, a cache key, and an eval set.

The existing four in this category all review a *system*. These three review the things that
decide whether the system review was worth having: how much you are allowed to build before you
have measured anything, what the cache is keyed on, and whether the eval set can produce a single
instance of the failure it was commissioned to catch.

Each is shaped the same way. Somebody posts a design with its own cost named. Somebody answers
with the textbook rule, correctly stated and wrong here. Somebody else brings a number the rule
does not survive. The resolution names the mechanism and the condition under which the textbook
answer comes back, and the author returns with what they actually did.

Design Reviews is an open discussion category rather than Q&A, so nothing here is marked as an
answer. That is deliberate for these three in particular: two of them end with the author holding
a decision the thread narrowed rather than made.

Every figure is one the repository produces, out of the committed baseline, the C1 cache
simulator, ADR-0012, ADR-0015 or `raglab/costs.py`. Where an observation has no committed number
behind it, it is written in words.
"""
from __future__ import annotations

CAT = "Design Reviews"

REPO = "/fde-academy-lab/advanced-rag-lab/blob/main"

THREADS = [
{
 "category": CAT, "author": "marcus",
 "title": "Design review: two quarters of retrieval work before anything ships, and I want to be argued out of it",
 "body": f"""Posting the plan rather than the architecture, because I think the plan is the part
that is wrong and I cannot see where.

### The situation

Internal incident assistant for a support organisation. About 90,000 runbooks, post-incident
reviews and closed tickets. Sixty engineers who currently search a wiki. One of me, plus half of
somebody else, and a director who has asked for a date.

### The plan as it stands

| Phase | Weeks | What lands |
|---|---:|---|
| 1 | 8 | Ingest, structural chunking, two indexes, ACL model |
| 2 | 4 | Hybrid fusion, per-corpus alpha sweep |
| 3 | 4 | Cross-encoder trained on our own click data |
| 4 | 4 | Agentic decomposition for the multi-hop questions |
| 5 | 4 | Eval set, harness, release gate |

Week 24 before anybody outside the team types a question.

### What my own plan costs

- **Nothing is measurable until week 20.** The harness is in phase 5 because building it needs
  the labelled set, and the labelled set needs somebody to look at real queries, and there are no
  real queries until something ships. I know that is circular and I have not broken it.
- **Two indexes from phase 1** means a consistency problem I own for the life of the system,
  bought before I have any evidence that fusion helps here.
- **Alpha is per corpus.** Phase 2 produces a number that has to be refitted whenever the corpus
  moves, and the corpus moves weekly.

### What I want challenged

Not the components. Each one is defensible on its own and I can cite the material for all five.
What I want attacked is the ordering, and specifically whether the phases that are furthest from
a user belong at the front. I have written a plan whose first falsifiable moment is week 20,
which by the standard in [R2's decision template]({REPO}/lab-simulator/units/R2-fusion-decision/BRIEF.md)
is not a plan at all.""",
 "replies": [
  {"by": "wei", "body": """I would keep phases 1 to 3 and cut phase 4, and I do not think the
ordering is wrong.

We shipped almost exactly this system, at roughly your corpus size, for a support org of about
the same shape. The lexical-only baseline was unusable on the questions people actually asked,
because engineers paraphrase and runbooks do not. Fusion plus a reranker was the single biggest
jump we ever measured on that system, and it was not close.

The reason to do it early is that retrieval is the part you cannot retrofit cheaply. Chunk ids,
index identity and the second index all reach into everything downstream, and adding a second
retriever to a live system a year in is a migration rather than a feature. The eval harness is
the opposite: it plugs into whatever is already there.

So my objection to your plan is that phase 5 is four weeks and should be one, not that it is
last."""},
  {"by": "priya", "body": f"""I want to put a number against that, because I believed the same
thing three weeks ago and spent a week sweeping alpha before I ran the comparison that would have
told me not to bother.

This repository's arms at `k=8` after the cross-encoder, 243 questions:

| Arm | evidence_recall | nDCG | answer_correct |
|---|---:|---:|---:|
| BM25 alone | 0.7118 | 0.3639 | **0.4156** |
| Dense alone | 0.7733 | **0.6055** | 0.3992 |
| Equal-weight RRF | 0.7742 | 0.5302 | 0.4033 |
| Weighted alpha=0.2 | 0.7645 | 0.4767 | 0.4115 |
| Weighted alpha=0.5 | **0.7790** | 0.5967 | 0.3992 |

Evidence recall spans 0.7118 to 0.7790 and that span is real under a paired bootstrap.
`answer_correct` is **inside the noise band on every pair**, and the numerically best answer
correctness sits on the numerically worst retriever.

That is the whole of phases 2 and 3, measured, and it moves the number a user feels by nothing.
[ADR-0015]({REPO}/docs/01-architecture/adr/0015-correct-the-fusion-finding.md) is the writeup,
including that it took a public retraction to notice, because the eval gate only ever compared a
configuration against its own history."""},
  {"by": "aarav", "body": """Then the plan is three weeks, not twenty-four.

One index. Fixed `k`. An off-the-shelf cross-encoder over the top 50. Provenance blocks so a
citation resolves. Put it in front of ten engineers in week four and let them break it. The
director gets a date they can believe, and you get the thing your plan is missing, which is
queries.

I would also cut phase 5 for v1. Measurement is what you add once there are real users and real
failures to measure against, and building a labelled set before you know what people ask is how
you end up with 300 questions about the wrong thing."""},
  {"by": "tomas", "body": """Agreed on the first paragraph and hard against the second.

The harness is the one item on that list you cannot add later, because the day you add it you
have no before. Every number you produce after week 12 is a number about a system nobody
characterised, and the first time somebody asks whether last month's chunking change helped, the
honest answer is that it is unknowable.

It is also cheap. The harness in this repository runs 243 questions against 2,430 chunks and the
corpus builds in about 0.7 seconds. Four weeks is Marcus costing a labelled set, not a harness,
and those are separable: stand the harness up in week one against thirty questions you write
yourself, and grow the set as real queries arrive.

The other two things I would put in week one, from having retrofitted both:
content-addressed chunk ids, and a versioned index behind an alias. Wei's scaling breakdown in
this category — *what actually changes when you move from 500 docs to 5 million* — has both in
the column that does not change, and the retrofit cost us a two-day outage window for what was a
five-line decision on day one."""},
  {"by": "maintainer", "body": f"""The mechanism, because the phase list is a symptom of it.

Retrieval work moves the metric a user feels only while retrieval is the binding constraint.
On this corpus it is not, and the baseline says so in two adjacent numbers: `full_chain_recall`
0.4686 against `answer_correct` 0.4115. The evidence for the full chain is in the window and the
reader is losing it after it arrives. Every hour spent widening the pool is spent on the side of
the pipeline that is already ahead.

**The condition under which Wei is right** is exactly the one this corpus fails: when
`answer_correct` tracks `evidence_recall` across arms. On his corpus it plainly did, and the
tickets-versus-paraphrase description is the reason to expect it. The way to find out which
corpus you have is two arms and an afternoon, not two quarters.

Worth knowing what the cheap levers are before committing a quarter to the expensive one.
Evidence recall on the shipped configuration goes 0.7645 at `k=8`, 0.7874 at `k=10`, 0.8567 at
`k=20`. That is a larger movement than any fusion rule in Priya's table and it is a config line.
The reranker is the other one: without it, `k=8` drops to 0.6486 on RRF.

So the review is not asking you to build less. It is asking that the first measurable moment
land in week two,
and the ordering after that is decided by what week two says rather than by
[the deck]({REPO}/docs/02-curriculum/README.md)."""},
  {"by": "marcus", "body": """What I did, and what surprised me.

Shipped in week three. One index, `k=10`, the off-the-shelf reranker, provenance blocks,
content-addressed ids and an alias. Thirty questions I wrote myself on day two, grown to about a
hundred by week six from the query log.

The surprise was the shape of the failures rather than the rate. I had assumed the wrong answers
would be *retrieval* wrong, and most of them were not. The runbook that came back was the right
runbook and the wrong revision, and the answer was a clean, cited, confident summary of a
procedure we stopped using in March. That is the same shape as the temporal slice here: evidence
recall 0.769, and answer correctness 0.091 on 66 questions, against 0.848 on the comparison
slice.

Two quarters of fusion work would not have touched a single one of those, and I would have
finished it before finding out.

The part I keep coming back to is Aarav's cut. He was right that my labelled set would have been
about the wrong thing, and wrong that the answer was to build it later. The answer was to build
it small, early, and against the failures rather than against the corpus, which is a different
mistake from the one I was making and I nearly swapped one for the other."""},
 ],
},
{
 "category": CAT, "author": "sofia",
 "title": "Design review: 40 tenants, one assistant, and I think the cache key is the whole design",
 "body": """Before I build. The retrieval side is unremarkable and I am not asking about it.

### Shape

- **40 tenants.** Three of them are most of the traffic. The tail is long and quiet, and some
  tenants go hours between questions.
- Each tenant has its own **rubric block**: tone, escalation contact, jurisdiction, the phrases
  legal will not allow. Roughly 700 tokens. Changes when their account manager says so, which is
  not on our deploy cycle.
- Shared system prompt and few-shot examples, about the same size again.
- The bill is the reason this review exists. Per-query cost is the number the commercial model is
  built on and it is currently a guess.

### Proposed design

Prompt cache **keyed per tenant**, and the tenant block placed at the very top of the prompt,
above the shared system prompt.

Both choices are for the same reason. Tenant A's rubric must not be reachable from tenant B's
request under any failure of any component, and putting the tenant identity first and keying on
it means an isolation failure requires two independent things to go wrong rather than one.

### What my own design costs

- **Forty cold caches instead of one.** The quiet tenants may never warm at all, and I have not
  worked out what the retention window does to them.
- The shared system prompt is duplicated inside 40 distinct prefixes, so the part of the prompt
  that is identical for everybody is the part I am paying to store 40 times.
- A rubric edit invalidates one tenant, which is the one good property in the list.

### What I want challenged

Whether per-tenant keying buys the isolation I think it buys, or whether I am paying for it in
two places and getting it in neither.""",
 "replies": [
  {"by": "dan", "body": f"""[ADR-0012]({REPO}/docs/01-architecture/adr/0012-prompt-block-ordering.md)
answers the second half directly and I think it goes against you.

The rule is that blocks are ordered by volatility, most stable first, and that a single volatile
byte anywhere in the prefix invalidates everything after it. The tenant block changes from
request to request, because consecutive requests come from different tenants. So it is volatile,
so it goes after the barrier, below the retrieved chunks and next to the timestamp.

Do that and the shared system prompt plus the few-shots become one global prefix that every
request in the system shares. One cache, warm within seconds of a deploy, and the quiet tenants
stop being a problem because there is nothing tenant-shaped in the cached part at all.

The production figure in that ADR is a hit rate of 4% to 71% and cost per query down 58%, from
moving one timestamp out of byte 58. Same move, bigger block."""},
  {"by": "priya", "body": """These are the C1 unit's own four configurations over its
200-request trace — I did not run Sofia's layout, because that unit's assembler is fixed. But the
last row transfers, and I do not think Dan's version wins.

| Configuration | hit rate | mean full-rate tokens billed |
|---|---:|---:|
| assembler as given | 0.2612 | 154.04 |
| correct volatility order | 0.8176 | 38.07 |
| timestamp deleted instead | 0.7942 | 42.16 |
| **stable blocks moved too** | **0.6969** | **63.23** |

The last row is the one that matters here. That configuration applies the rule harder than
necessary, moving blocks that did not need to move, and it costs twelve points of hit rate
against getting the ordering right. Moving a 700-token block that is perfectly stable within a
tenant is that row.

So: keep the tenant block early, keep the per-tenant key, and the numbers say you are fine. I
would ship Sofia's design as posted."""},
  {"by": "marcus", "body": f"""Priya, the table transfers less far than it looks, and the reason
is in the harness that produced it rather than in the numbers.

[`C1/check.py`]({REPO}/lab-simulator/units/C1-cache-barrier/check.py):

```python
CACHE_KEY_INCLUDES = ("tenant_id",)
TENANTS = ("acme-eu", "acme-us")
...
seen: dict[str, list[str]] = {{t: [] for t in TENANTS}}
```

So it *does* model a keyed cache, and Sofia's per-tenant keying is the design it already
assumes — which is why the tenant block belongs before the barrier under that key, and Priya's
reading of the last row is right.

What it does not model is **eviction**. `seen` is an unbounded per-tenant list of prior prefixes,
so a prefix written at request 3 is still a hit at request 200, and the trace is 200 requests
across two *hot* tenants with no idle time in it. Sofia's risk is forty tenants of which
thirty-seven are quiet. Those four rows cannot show a quiet tenant's segment going cold, because
nothing in the instrument ever goes cold.

The same limit is in the general cache too: `PromptCache(ttl_requests=None)` evicts nothing by
default, and when a TTL is set it counts in *requests* on one global clock, so a tenant's entry
ages at the rate of everybody else's traffic rather than its own."""},
  {"by": "maintainer", "body": """Two separate things are being argued and the answers are in two
different places, which is why the thread keeps sliding between them. The ordering answer is one
paragraph of ADR-0012. The isolation answer is the `hashlib.sha1(prefix_text.encode())` line
Marcus quoted upthread, and it is not in any ADR at all.

**On ordering.** Volatility is relative to the cache key. The tenant block changes between
tenants and never within one, so it is stable per tenant and volatile globally. Under a per-tenant
key it belongs before the barrier; under a global key it belongs after. Dan's rule is correct and
his premise is the thing under review, which is why applying the rule first and choosing the key
afterwards gets it backwards. **Choose the key, then order relative to it.** Dan is right the
moment the key is global, and that is a decision rather than a fact about the prompt.

**On isolation, which is the question Sofia actually asked.** The key does not buy it. A prefix
cache is content-addressed: the lookup above hashes the prefix *text*. Two tenants share an entry
only when their prefix bytes are identical, and once the rubric block differs they are not. Adding
a per-tenant key on top of a content-addressed lookup is a second lock on the same door, and it is
paid for by losing the shared stable segment.

The isolation question is about what goes **into** the prefix, not what the lookup is keyed on.
If tenant B's rubric can reach tenant A's prompt, it reached it at assembly time and the cache is
downstream of a bug that already happened."""},
  {"by": "tomas", "body": """The operational half, because both proposals break the enforcement
that ADR-0012 ships with.

That ADR's test asserts that the first N tokens of the assembled prompt are identical across two
different queries. In a multi-tenant system that test is either vacuous or wrong depending on
which two queries the fixture happens to pick, and it will not tell you which. It has to be
parameterised by the key: **identical across two queries of the same tenant, and different across
two tenants.** The second half is the isolation assertion Sofia wants, and it belongs in the test
suite rather than in the key.

Alerting has the same problem. ADR-0012 says put cache hit rate on the dashboard and alert on a
drop of more than ten points week over week. Aggregate hit rate in this design is three tenants'
hit rate wearing a hat. The tail can go to zero and the aggregate will not move enough to fire.
Per-tenant hit rate, or the alert is decorative.

This failure is silent by construction. Right answers, working feature, larger bill, six weeks
later."""},
  {"by": "sofia", "body": f"""What I built, and the part I did not see coming.

Two segments before the barrier. A global one (system prompt, rubric shell, few-shots) that is
byte-identical for all 40 tenants, then a per-tenant one (banner, rubric). Retrieved chunks, time
and question after. No per-tenant cache key at all, because the maintainer's point stands: the
lookup already keys on the bytes, and the isolation I wanted is an assembly-time assertion, which
is now two tests.

The surprise is the tail, and it inverts the rule for part of the estate.

For a tenant with hours between questions, the per-tenant segment is never warm when it is
needed. Every request writes it and no request reads it, and a write is not free:
`cache_write_multiplier` in [`costs.py`]({REPO}/raglab/costs.py) is 1.25 for the five-minute
retention and 2.00 for the hour, against a read at 0.10. So for those tenants the segment is
costing 12.5 times what reading it would, forever, to buy a hit that never arrives.

For them the correct ordering is Dan's: push the tenant block after the barrier, keep only the
global segment cacheable, and take the smaller win reliably. Which means the ordering is a
function of the tenant's traffic shape and not of the prompt, and I now have two assemblers
selected by a threshold I am going to have to measure."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "Design review: the eval set for a policy assistant, before I spend three weeks labelling it",
 "body": """Reviewing an evaluation rather than a system, because the system is the easy half
and this is what the engagement is actually bought on.

### The failure the client is paying to remove

An employee asks about parental leave. The assistant returns a clean, cited, confident answer
drawn from the version of the policy that was superseded in March. The citation resolves. The
quote is accurate. The answer is wrong and there is nothing in it that looks wrong.

This has happened to them twice with their existing keyword search, and it is the reason we were
called.

### Proposed eval set

- **300 questions**, generated by a model from the document corpus, one to three per policy.
- **Stratified by department** so no team can claim the set ignores them.
- Judged for **answer correctness** by a model judge against the generated gold answer.
- Headline metrics: answer correctness and MRR.
- Roughly three weeks of my time plus a day each from four policy owners to review the gold.

### Constraints worth knowing

Every policy in their store carries its **version history**: three to nine prior revisions, all
retrievable, all in the same index, none of them marked in the text beyond a header date.

### What my own design costs

Three weeks before anything is measurable, and a judge whose agreement with the policy owners I
have not established.

### What I want challenged

**Is 300 enough?** At 40 departments that is around seven or eight questions each, and I cannot
tell whether a per-department number at that n means anything or whether I should cut the
stratification and go wider.""",
 "replies": [
  {"by": "lena", "body": """On the metrics rather than the count. I would make MRR the headline
and treat answer correctness as the secondary.

The LinkedIn KG-RAG work (SIGIR 2024, arXiv:2404.17723) is the closest published thing to this
deployment and it reports **MRR +77.6%** alongside **median resolution time down 28.6%**. That is
the pairing you want in a client report: a retrieval metric that moved and an outcome metric that
moved with it. Answer correctness through a model judge introduces a component whose calibration
you have just said you have not established, and it will be the first thing their data team
attacks.

MRR is also cheap. It needs a ranked list and a gold document id, which your generator produces
for free, and it does not need the gold *answer* your four policy owners are spending a day
each on."""},
  {"by": "dan", "body": """That reads right to me and I would take it.

One thing I do not understand well enough to disagree with, so I will just ask it. If the
generator writes each question from the current version of a policy, and the gold document is
that current version, and the retriever returns it, where in this set does the old version ever
get a chance to win?

I am probably missing something obvious, but I cannot construct the failure Aarav described using
a question from this set. The March version would have to beat the current one, and nothing in
the set is asking it to."""},
  {"by": "marcus", "body": """Dan's question is the review, and I will come to it after the
metric, because the metric is wrong for a reason that is measurable here.

A ranking metric can move enormously on a corpus while the number a user feels does not move at
all. This repository's arms at `k=8`:

| Arm | nDCG | answer_correct |
|---|---:|---:|
| BM25 alone | 0.3639 | 0.4156 |
| Weighted alpha=0.2 | 0.4767 | 0.4115 |
| Dense alone | 0.6055 | 0.3992 |

nDCG spans 0.3639 to 0.6055. `answer_correct` is inside the noise band across every pair in that
table, and the best answer correctness is on the worst nDCG. A report built on Lena's headline
would show a 66% relative improvement and a client who felt nothing.

The stratification question has a similar answer. Aggregate `answer_correct` here is 0.4115, and
underneath it: comparison 0.848 on n=46, inference 0.579 on n=95, temporal **0.091** on n=66. The
aggregate is the only number that is useless. But n=66 is what it takes to say that with an
interval, and Aarav is proposing slices of seven."""},
  {"by": "lena", "body": """Taking the metric point. The paper's setup does not carry over and I
should have checked the retrieval unit before quoting the number.

In that system the retrievable object is a resolved ticket and the ranked list is shown to a
human agent who reads it. MRR tracked resolution time because the ranking *was* the product, so
moving the right ticket up moved the outcome directly. Here the ranked list is read by a model
and never seen by the employee, and every ranking gain has to survive a generation step before
anybody feels it.

**The condition under which MRR is the right headline:** when the user reads the ranked list
themselves. That is a real class of system and it is not this one.

Dan's question I cannot answer at all, which I think means he found the actual defect."""},
  {"by": "maintainer", "body": f"""He did, and it has a name here already.

**The mechanism.** A set generated from the current version of each document holds no
wrong-but-plausible distractor, so the staleness failure has no way to occur in it. Not rarely.
Never, at any n. Same shape as
[CS-04's N2]({REPO}/concepts-and-case-studies/case-studies/CS-04-our-own-negative-results.md),
where comparison starvation was unmeasurable because the generator emits organisations on a
balanced schedule: the imbalance is absent by construction. Aarav asked whether 300 was enough, a power
question about a set that cannot produce one instance.

**The condition, as a design.** N3 there is the recipe. Our 36 nulls defeat every
similarity threshold: they name real entities in the corpus's own vocabulary while the
answerable questions paraphrase, so the unanswerable ones are lexically **closer**. Write the
as-of question in the wording of the March revision, leave both revisions indexed, and the set
contains the failure.

**Nothing unanswerable.** Those 36 give abstention a denominator. The baseline reports
`abstention_recall` 0.0000 and 36 false answers on 36 nulls, rather than omitting it. With zero
nulls, a system that never abstains and one that abstains perfectly file the same report.

**Derive slice counts from the harness, not a document.** Ours drifted.
[`protocol.md`]({REPO}/docs/04-evaluation/protocol.md) states 128 single-hop, 61 two-hop and 18
three-plus; the harness reports `hops` as 77 and 130. They do not reconcile, and the document is
being corrected. The retracted multi-hop finding predicting 0.6838 and a 21-point shortfall rests
on that split. What reproduces is **0.4603** predicted against **0.4686** measured, at
independence. There was no shortfall."""},
  {"by": "aarav", "body": """Rebuilt in the other order, and it cost less than the original plan.

Sixty version-paired questions first, written from the wording of a superseded revision, with
both revisions left in the index and the gold answer being the current one. Two days, not three
weeks, because the policy owners were reviewing 60 items instead of 300 and every one of them was
about the thing they had complained about.

Then I ran it before generating anything else.

What surprised me is that retrieval was mostly fine. The current version came back in the window
for most of them, and the answers were still wrong, because the date qualifier in the question
never reached the ranking and the model had two revisions in front of it with no signal about
which was live. That is the temporal shape here almost exactly: evidence recall 0.769 and answer
correctness 0.091 on the 66 temporal questions. The fix is a header the retriever can see and a
prompt that names the as-of date, and neither is a retrieval project.

The uncomfortable part is that my 300-question set would have scored respectably, I would have
shown it, and the failure the client hired us for would have been invisible in every column. I
asked whether the set was big enough. Nobody, including me, asked whether it could fail."""},
 ],
},
]
