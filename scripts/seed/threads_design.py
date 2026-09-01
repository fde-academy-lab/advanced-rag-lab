"""Design Reviews and Show and Tell — architecture argued before it is built.

The shape these model: a design posted with its own cost named, an objection that lands, and a
resolution that is either a changed design or an explicit decision to measure first.
"""
from __future__ import annotations

THREADS = [
{
 "category": "Design Reviews", "author": "sofia",
 "title": "Design review: retrieval for a regulated insurer, 14 ACL groups, 40-day audit trail",
 "body": """Posting before I build. Constraints are real and two of them fight each other.

### Constraints
- **1.2M documents**, mixed: policy PDFs, claim notes, regulator correspondence.
- **14 ACL groups.** A claims handler sees their book. A compliance officer sees everything. An
  external auditor sees a time-boxed slice.
- **Audit requirement:** for any answer shown to a user, we must be able to reconstruct *40 days
  later* exactly which documents were used and what the retrieval scores were.
- **p95 800ms.**
- Answers on coverage questions are regulated advice. Wrong is not "annoying", it is reportable.

### Proposed design
Pre-filter on ACL group, hybrid retrieve (BM25 + dense, weighted), cross-encoder rerank top 100,
pack to 8 chunks with provenance blocks, generate with mandatory citation or abstain.

Every query writes a trace row: query text, ACL group, candidate ids with scores, final packed
ids, index version, model version, timestamp.

### What my own design costs
- The trace store grows at roughly 4KB/query. At 200k queries/day that is 800MB/day, ~30GB for
  the 40-day window. Storage is cheap; the *retention policy* is a legal question I have not
  answered.
- Pre-filtering with 14 groups means either 14 index partitions or a filtered ANN search. I have
  assumed partitions and I am not confident.
- Mandatory citation means the generator must decline more often. I have not measured how much.

### The alternative I rejected
Post-filtering, for k-collapse and score leak. Rejecting it was easy; what I am unsure about is
whether partitions or filtered search is right at 14 groups.""",
 "replies": [
  {"by": "tomas", "body": """Partitions at 14 groups is fine and I would do the same. The
question is whether the groups are actually disjoint. If a document can belong to more than one
group, partitions mean storing it more than once, and now your 1.2M documents are 3M and your
index rebuild time triples.

Check the multiplicity before committing. If the average document is in 2.4 groups you want
filtered search and a single index, not partitions."""},
  {"by": "sofia", "body": """Checked. Average is 1.3 groups per document, but the distribution is
horrible — 91% are in exactly one group and the regulator-correspondence set is in all 14. So
partitions duplicate ~4% of documents fourteen times.

That is tolerable on storage and annoying on consistency: fourteen copies that must be updated
together or a compliance officer and a claims handler see different versions of the same
letter."""},
  {"by": "marcus", "body": """That consistency problem is the actual risk in this design and it
is worth more attention than the storage.

Fourteen copies updated non-atomically means there is a window where the answer depends on who
asked. In a regulated setting that is not an eventual-consistency inconvenience, it is two
different answers to the same question with an audit trail proving it.

Either make the write atomic across partitions — which is most of the way to reinventing a
transactional store — or do not duplicate. Single index, filtered search, ACL as a column."""},
  {"by": "wei", "body": """Filtered ANN has a failure that is not obvious until it bites, and
Sofia should know about it before choosing.

A filtered graph search can **disconnect the graph** for a restricted user. The long-range links
that make the small-world graph navigable may all point at documents the user cannot see. Greedy
search then cannot cross the space, and recall collapses — for exactly the users with the
tightest permissions, which is the worst possible distribution of failure.

We hit this in production. Recall for our most-restricted role was 0.31 against 0.94 for
unrestricted, and nothing in the aggregate showed it.

Mitigation is a selectivity threshold measured rather than guessed: below some filter
selectivity, fall back to exact search over the permitted set. Costs latency on a minority of
queries and is correct.""", "accepted": True},
  {"by": "sofia", "body": """That settles it. Single index, ACL column, filtered search with a
measured selectivity fallback. The duplication consistency problem was going to be a live
incident eventually and I would rather pay latency than explain that to a regulator.

Revised: I need an eval slice **per ACL group**, because Wei's failure is invisible in aggregate.
That is a change to the eval set, not just the retriever, and it is the part I would have
missed."""},
  {"by": "aarav", "body": """One thing nobody has raised: the 40-day trace requirement means your
trace store contains query text, which in an insurance context contains claimant data. That is a
40-day retention of personal data you have just designed in without a lawful basis discussion.

Not blocking the architecture. Blocking the *deployment*, and better to find now."""},
  {"by": "maintainer", "body": """Marked Wei's reply as the answer, but read Aarav's too — it is
the one that would have stopped this at a compliance gate three months in.

What made this a good design review: Sofia posted **before** building, named what her own design
costs including the part she was unsure about, and stated the alternative she had rejected and
why. Three objections landed and the design changed. That is the outcome; a design review where
everyone agrees has not reviewed anything.

Filed the ACL-group eval slice as issue #16 and the retention question as a decision needing an
ADR."""},
 ],
},
{
 "category": "Show and tell", "author": "priya",
 "title": ("Capstone: two of my four improvements were inside the noise band, "
           "and I nearly reported all four"),
 "body": """Finished the capstone. Four changes, measured individually, and the honest result is
that half of them did nothing.

| Change | evidence_recall Δ | 95% CI | Verdict |
|---|---|---|---|
| Weighted fusion α=0.2 (from equal-weight RRF) | **+0.0246** | [+0.008, +0.041] | Ship |
| Learned reranker with semantic pair features | **+0.0812** | [+0.031, +0.124] | Ship |
| Structural chunking (from recursive) | +0.0071 | [−0.011, +0.026] | **Inside the band** |
| Query expansion on short queries | +0.0043 | [−0.019, +0.028] | **Inside the band** |

The thing I want to write about is not the two that worked.

My first draft of the report said "all four changes improved evidence recall, cumulatively
+0.117". That sentence is *arithmetically true* and completely dishonest. Two of those numbers
are indistinguishable from zero, and summing four deltas — two of which are noise — into one
cumulative figure launders the noise into the headline.

I caught it because the capstone template has a column for the interval and I had to fill it in.
Without that column I would have shipped the sentence and believed it.

**What I would do next:** structural chunking is *plausibly* positive and the interval is wide
because n=243 is small for a per-slice question. The right move is more questions on the slice
where chunking should matter, not more tuning.

**Cost:** the reranker adds ~120ms p50. On a 800ms budget that is affordable; on a 300ms budget
it is the whole thing.""",
 "replies": [
  {"by": "dan", "body": """The cumulative-sum thing is going straight into my notes. I have
definitely written that sentence before.

Question — if two changes are each inside the band individually, could they be jointly
significant? Or is that just the same laundering with extra steps?"""},
  {"by": "marcus", "body": """Genuinely good question and the answer is "sometimes, but not the
way you would test it by default".

Two changes can be jointly significant if their effects are correlated in the same direction —
you would test the *combined* configuration against baseline as a single comparison, one
interval. That is legitimate.

What is not legitimate is summing the individual point estimates, which is what Priya's draft
did. Summing point estimates ignores that each carries its own uncertainty, and the errors do
not cancel — they compound. Four deltas each ±0.02 do not give you a cumulative figure ±0.02.

There is also a multiple-comparisons problem hiding here: test four changes at 95% and there is
roughly an 18% chance at least one clears by luck. Priya tested four and two cleared, which is
consistent with two real effects, and would also be consistent with one real effect and one
lucky one. The frozen slice is what distinguishes those.""", "accepted": True},
  {"by": "priya", "body": """Ran both on frozen. Fusion holds (+0.019, [+0.004, +0.035]),
reranker holds (+0.074, [+0.022, +0.119]). So both survive, which is the answer to Marcus's
"one real and one lucky" case.

Also ran the combined configuration as a single comparison as he suggested: +0.098,
[+0.048, +0.147]. Which is *less* than summing the two individual point estimates (0.0246 +
0.0812 = 0.106), and that gap is exactly the overlap I would have double-counted."""},
  {"by": "lena", "body": """Worth naming why the combined effect is smaller than the sum: the two
changes are partly doing the same work. Weighted fusion promotes semantically-relevant chunks
the equal-weight version buried; the learned reranker with semantic features promotes some of
the *same* chunks. Each fixes part of the same failure, so the second one has less left to fix.

This is extremely common and almost never reported, because reporting it requires running the
combined arm, which nobody does when both individual arms already look good."""},
  {"by": "maintainer", "body": """Marked. This is the best capstone submission in the repository
and the reason is the paragraph Priya nearly did not write.

Everyone who does this exercise gets four numbers. What separates submissions is whether the two
that did nothing are reported as having done nothing. Priya's draft sentence — "all four
improved, cumulatively +0.117" — is the single most common way retrieval results get
misrepresented, and it is usually not dishonesty, it is a template without an interval column.

Lena's point about overlapping effects is the follow-up worth stealing for interviews. "Why is
the combined effect smaller than the sum of the parts?" is a question a good panel asks, and
"because both changes fix part of the same failure" is the answer almost nobody has."""},
 ],
},
]
