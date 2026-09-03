"""Architecture breakdowns and use-case threads.

Each takes one real deployment shape, walks the design, and names the number that decides it.
"""
from __future__ import annotations

THREADS = [
{
 "category": "Design Reviews", "author": "wei",
 "title": "Architecture breakdown: what actually changes when you move from 500 docs to 5 million",
 "body": """Recurring question in the cohort, so here is the whole thing in one place. Each row is
a component that survives unchanged, changes shape, or has to be replaced — and the *reason*,
because "it does not scale" is not a reason.

| Component | 500 docs | 5M docs | Why it changes |
|---|---|---|---|
| Inverted index | SQLite FTS5 | Lucene / OpenSearch | FTS5 is single-writer and has no distributed merge. The scoring is the same; the operations are not |
| Vector search | Full scan, O(N·d) | HNSW / IVF-PQ | At 2,430 chunks a full scan is 4ms. At 5M it is 8 seconds |
| Graph build | Brute-force k-NN, O(N²d) | Incremental insert | The real wall. At 2,430 it is ~2s. At 5M it does not finish |
| Chunk ids | `doc:ord:hash` | **unchanged** | Content addressing is more valuable at scale, not less — it is what makes incremental indexing possible |
| Reranker | Linear over 8 features | Cross-encoder, routed | Feature cost is per candidate. The change is that you can no longer afford it on every query |
| Eval harness | **unchanged** | **unchanged** | This is the point of the whole design |
| Metrics | **unchanged** | Add per-shard slices | The definitions hold; the slicing gets finer |

## The three things that break first, in order

**1 · Graph build time, at roughly 10⁵.** O(N²d) brute-force k-NN stops finishing. This is the
first hard wall and it arrives earlier than people expect. Fix is incremental insertion with a
real ANN library — seam ①, no interface change.

**2 · Full-scan exact search, at roughly 10⁵–10⁶.** Becomes the query-time bottleneck. You were
already meant to be using ANN; what breaks is the *fallback*, which quietly stops being viable and
takes your selectivity-threshold escape hatch with it.

**3 · Reindex time, at roughly 10⁶.** A full rebuild stops fitting in a maintenance window, which
forces the incremental path from optional to mandatory. That in turn forces stable chunk ids,
tombstones, and blue/green with an alias swap — which is why those are in the design at 500 docs
even though nothing needs them yet.

## What does not change, and why that is the whole argument

The **harness, the metrics and the eval set** are untouched across four orders of magnitude.

That is not luck. It is what the seams buy: swapping the retriever changes the retriever. If
scaling the index also required changing how you measure, you could never tell whether a scale-up
had cost you quality — every number before and after would be incomparable.

## The trap in this table

Reading it as a migration plan. It is not. **Do not build the 5M architecture at 500 docs.**
Every row in the right-hand column costs operational surface — another system to version,
monitor, roll back and page someone about at 3am.

The one thing worth building early is the row that says **unchanged**: content-addressed ids,
a versioned index behind an alias, and the eval harness. Those are cheap now and expensive to
retrofit, and everything else is cheaper to defer.""",
 "replies": [
  {"by": "tomas", "body": """Endorsing the last paragraph hard, from having done the retrofit.

Retrofitting content-addressed chunk ids onto a live system is genuinely painful: every existing
id changes, so it is a full reindex plus a migration of anything that referenced an id — cached
scores, click logs, saved searches, citations in previously-generated answers. We took a two-day
outage window for what would have been a five-line decision on day one."""},
  {"by": "priya", "body": """Question about row 3. If the graph build is O(N²d) and that is the
first wall, why not use an incremental ANN library from the start? The interface is the same
either way."""},
  {"by": "wei", "body": """For a production system you should. For this repository it is
deliberate, and the reason is pedagogical rather than technical: the brute-force build is what
lets you *watch* the ANN recall curve collapse when the graph is not navigable.

Import the library and that failure becomes invisible — you get a working index and never learn
why it works. ADR-0010 argues this at length, including why four random long-range links rather
than HNSW: the crude version makes Kleinberg's result visible, the organised version obscures
it."""},
  {"by": "marcus", "body": """One number missing from the table that decides more migrations than
any row in it: **queries per second.**

Everything above is about corpus size. A 5M-document corpus at 2 QPS and the same corpus at 2,000
QPS are different systems, and the second one needs replication, caching and connection pooling
that the first does not — none of which appear here.

Worth a second table, or at least a line saying this axis exists. People routinely scale for
corpus size and get killed by concurrency.""", "accepted": True},
  {"by": "wei", "body": """Fair, and it is the more common failure. Adding it: corpus size drives
index architecture, QPS drives serving architecture, and they are close to independent. A team
that has confused the two usually shows up with a sharded index and a latency problem that
sharding made worse."""},
  {"by": "maintainer", "body": """Marked Marcus's for the axis nobody named.

Pinning this thread. The question "how does this scale" comes up in every cohort and in most
interviews, and the useful answer is not a list of bigger components — it is knowing which parts
are invariant and why.

The row that says the eval harness is unchanged across four orders of magnitude is the single
best argument for the whole seam design, and it is worth being able to say in one sentence."""},
 ],
},
{
 "category": "Design Reviews", "author": "aarav",
 "title": "Use case: internal policy search for 4,000 employees — where a RAG system is the wrong answer",
 "body": """Client wants "ChatGPT for our HR policies". 900 documents, 4,000 employees, maybe 300
questions a day.

I do not think they need RAG and I want this challenged before I tell them.

## Why I think retrieval alone is enough

**The corpus fits.** 900 policy documents is roughly 2M tokens. Not in one context window, but
the *relevant subset* for any question is small and the documents are heavily structured with
headings.

**The questions are navigational, not synthetic.** "What is the parental leave policy?" wants a
document, not a composed answer. People want to read the policy, because they are going to have
to cite it to their manager.

**Generation adds a liability.** A paraphrased HR policy that is subtly wrong is a legal problem.
A link to the correct policy is not.

## What I would propose instead

BM25 over structured chunks, heading-aware. Return the top 3 documents with the matching section
highlighted. No generation.

Cost: near zero. Latency: 40ms. Failure mode: returns the wrong document, which the user
immediately sees, because they can read.

## What I am unsure about

Whether "no AI" is sellable when they asked for AI, and whether I am pattern-matching to
"simplest thing" rather than to their actual need.""",
 "replies": [
  {"by": "sofia", "body": """Agree on the architecture and I would add the strongest argument you
have not made: **auditability.**

With retrieval-only, "why did it show me this" is answerable exactly — these terms matched this
section, here is the score. With generation you are explaining a model's output to an HR director
who has just been asked by an employee why the system told them something wrong.

In a policy context that is not a nice-to-have. It is most of the value."""},
  {"by": "wei", "body": """I will push back on one thing, because I think you are right about the
architecture and wrong about the framing.

"They asked for AI and I am telling them no" loses even when correct. You are inviting them to
find someone who will say yes.

Reframe as staging. Ship retrieval-only first, **instrument the failures**, and let the data
decide whether generation is needed:

> "Phase one is search that actually works, live in three weeks. We log every query and every
> reformulation. A reformulation is a labelled failure the user hands you for free. After a month
> we look at the ones search could not answer, and if a meaningful share of them genuinely need
> composition across documents, that is the business case for phase two — with your traffic
> rather than my opinion."

Now you have not said no. You have said "let's find out", and you have proposed the measurement
that answers it. If it turns out 15% of queries genuinely need multi-document synthesis, you
build it and they trust the number because it is theirs.""", "accepted": True},
  {"by": "marcus", "body": """One correction to the analysis. You say the questions are
navigational. That is a hypothesis, and you have no data — the client's belief that they need
composition might be based on something real that you have not seen.

Cheapest possible test: ask for 50 real questions from their helpdesk before you design anything.
Two hours of somebody's time. If 45 are navigational you have your answer and it is *their* data;
if 20 need composition, your whole design is wrong and you found out in week zero."""},
  {"by": "aarav", "body": """Both taken. The staging reframe is the one I needed — I was
constructing an argument to win rather than a process to find out, which is exactly the thing I
tell other people not to do.

Asking for 50 helpdesk questions first is going in the SOW."""},
  {"by": "tomas", "body": """Operational note for phase one, since it is easy to skip when the
architecture is simple: policies get superseded. A retrieval system that confidently returns the
2023 parental leave policy is worse than no system, because the user has no reason to doubt it.

You need effective-date metadata and a filter, and it is much cheaper to put in at the start than
to retrofit once people trust the thing."""},
  {"by": "maintainer", "body": """Marked Wei's.

This thread is here because the most valuable judgement in this work is knowing when *not* to
build the interesting thing, and it is the hardest to teach — every incentive in a curriculum
points at building more.

Three transferable moves. Wei's staging reframe converts a refusal into a measurement. Marcus's
50-question ask tests the premise for two hours of effort. Tomás's effective-date point is the
kind of thing that decides whether a simple system is trusted or abandoned.

Notebook `03` covers the long-context-versus-RAG decision matrix, and R11 in the retrieval
interview bank asks exactly this question."""},
 ],
},
]
