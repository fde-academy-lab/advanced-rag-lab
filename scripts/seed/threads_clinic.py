"""Debugging Clinic and Q&A threads — long investigations where nobody knows the answer.

Modelled on the defects actually found while building this repository, so the reasoning steps
are the real ones rather than a reconstruction that knows the ending in advance.
"""
from __future__ import annotations

THREADS = [
{
 "category": "Debugging Clinic", "author": "priya",
 "title": "ANN recall is 0.00 at ef=64. Not degraded — zero. Where do I even start?",
 "body": """Grew the corpus from 230 chunks to 2,430 and the ANN index stopped returning
anything correct. Not "worse recall" — **0.00** measured against exact search at ef=64.

What I have checked:
- Vectors are non-degenerate (norms all ≈ 1, no NaNs).
- Exact search over the same vectors is fine: evidence recall 0.7645.
- The graph exists — `entry["graph"]` is a (2430, 12) array, not None.
- Raising ef to 256 gets recall to 0.03. So it is not a threshold thing.

A recall of exactly zero with a working exact path smells like a wiring bug, but I have read
the search loop four times and it looks right. What would you check next?""",
 "replies": [
  {"by": "dan", "body": """Long shot — are you rebuilding the graph after the corpus grew, or
reusing a cached one built on the 230-chunk version? A stale graph indexing positions that no
longer exist would give you garbage that still has the right shape."""},
  {"by": "priya", "body": """Good instinct and it was a real bug, just not this one. There *was*
a cache-poisoning issue — `_matrix` was keyed on `index_version` only, so an
`exact_vector(build_graph=False)` call stored `graph=None` and later `ann_vector` silently fell
back to exact search. Fixed by caching matrix and graph separately.

But that made ANN *report* honestly, which is how I now know it is 0.00 rather than
accidentally-correct. So the cache bug was hiding this one."""},
  {"by": "wei", "body": """Print the trajectory. Log the sequence of node ids the greedy walk
visits for a single query, and the distance at each step. If the distances are decreasing
monotonically and then it stops, you have a local minimum. If they jump around, you have a
neighbour-lookup bug."""},
  {"by": "priya", "body": """That was the move. Trajectory for one query:

```
step 0  node 1841  d=0.912
step 1  node 1839  d=0.887
step 2  node 1902  d=0.871
step 3  node 1903  d=0.868
step 4  node 1902  ← already visited, terminate
```

Five steps, distance barely moves, terminates. Every query does this. It is finding a local
minimum immediately and the true nearest neighbour is nowhere near node 1841.

So the walk works and the graph is the problem. But the graph *is* a k-NN graph — each node
links to its 12 nearest neighbours. That is what an ANN graph is supposed to be."""},
  {"by": "lena", "body": """That is exactly the problem, and it has a name.

A pure k-NN graph is **not navigable**. Every edge is short, so the graph is a lattice of tight
local neighbourhoods with diameter O(n^(1/d)). Greedy search cannot cross it — it terminates at
the first local minimum long before it traverses the space. At 230 chunks the diameter was
small enough that you got away with it. At 2,430 you did not. The failure is a function of
corpus size, which is why it appeared on growth and not on day one.

The fix is Kleinberg (2000): augment the lattice with **long-range links**. A small-world graph
— short edges for local refinement, a few random long edges for global traversal — is navigable
by decentralised greedy search in O(log²n) steps. Note it only works in a band: too few long
links and you are back to the lattice, too many and greedy routing has no gradient to follow.

This is the "navigable" half of *navigable small world*, and it is the half everyone drops when
implementing NSW from memory. HNSW is the same idea organised into layers rather than
randomised.""", "accepted": True},
  {"by": "priya", "body": """Four random long-range links per node:

```python
rng = np.random.RandomState(17)
longr = rng.randint(0, n, size=(n, min(4, max(1, n - 1))))
entry["graph"] = np.concatenate([near, longr], axis=1)
```

Recall at ef=64: **0.00 → 0.94**. At ef=128: 0.98.

Trajectory now takes 19 steps and crosses the space. Thank you — I would not have found that
by reading the search loop, because the search loop was never wrong."""},
  {"by": "tomas", "body": """Filing the operational lesson: this bug is **latent in corpus
size**. It passed every test at 230 chunks. Any ANN test that runs on a small fixture is
testing a regime where the bug cannot appear.

The regression test should assert monotonicity — recall must not decrease as ef increases, and
recall at a fixed ef must not collapse as n grows. That is now in `tests/test_retrieval.py`."""},
  {"by": "maintainer", "body": """Answer marked. This is issue #2 and it is the best-shaped
investigation in the repository, so it is worth naming what made it work.

Priya's first hypothesis was wrong but produced a real fix (the cache bug), which then *exposed*
the actual failure instead of masking it. Wei's suggestion — instrument the trajectory rather
than re-read the code — is the move that broke it open; four readings of a correct loop find
nothing. And Lena supplied the theory that turned "add more edges" into "add edges of a
specific kind, for this reason".

Note also what nobody did: nobody suggested switching to a library. That would have fixed the
symptom and taught nothing."""},
 ],
},
{
 "category": "Q&A", "author": "dan",
 "title": "Recall@N keeps climbing but full-chain recall is flat. What am I not understanding?",
 "body": """Sweeping N from 20 to 200 candidates. Evidence Recall@8 goes 0.71 → 0.79, steadily.
Full-chain recall sits at 0.46 and does not move at all — it is flat to three decimals across
the whole sweep.

If I am retrieving more of the right evidence, surely more questions should have *all* their
evidence? What is the relationship between these two numbers?""",
 "replies": [
  {"by": "aarav", "body": """They measure different things. Evidence recall is per-piece,
full-chain is per-question. You are getting more pieces but not more complete sets."""},
  {"by": "dan", "body": """I understand that they are defined differently — I mean why does one
move without the other. If piece-level recall rises, the probability of having all pieces should
rise too, shouldn't it?"""},
  {"by": "marcus", "body": """It should, and the fact that it does not is the finding. Do the
arithmetic.

Suppose a question needs 2 pieces and each has independent probability p of being retrieved.
Full-chain probability is p². At p = 0.71 that is 0.50; at p = 0.79 it is 0.62. So an 8-point
piece-level gain should buy you 12 points of chain-level gain **if the events were
independent**.

Yours moved zero. Therefore they are not independent — and the direction of the dependence is
the diagnosis. Your k=8 window is being filled with pieces that are *all* about hop 1. The
retriever scores against the query, hop-1 evidence looks like the query, hop-2 evidence looks
like the *answer to hop 1* and does not resemble the query at all. Widening N gives you more
hop-1 evidence, which raises the piece-level average and does nothing for completeness.

Test it: split evidence recall by hop. I predict hop-1 recall is climbing and hop-2 recall is
flat or falling.""", "accepted": True},
  {"by": "dan", "body": """Hop-1 recall 0.88 → 0.94 across the sweep. Hop-2 recall 0.54 → 0.55.

So the average was being carried entirely by the hop I was already good at. That is a much
more uncomfortable number than the one I started with."""},
  {"by": "wei", "body": """And this is why single-shot retrieval has a ceiling on multi-hop
questions that no amount of N fixes. You cannot retrieve hop-2 evidence with a query that does
not contain hop-2's vocabulary. The fix is architectural, not parametric: retrieve, read, form
a second query from what you found, retrieve again. That is notebook 08, and it is the honest
answer to "why do I need an agent loop" — not because agents are fashionable, but because one
query cannot express a two-hop information need."""},
  {"by": "maintainer", "body": """Marked Marcus's answer. Two habits in it worth stealing.

He did the arithmetic that turns a vague expectation ("it should rise") into a **specific
prediction** (0.50 → 0.62), so the observation of zero movement became evidence rather than a
shrug. Then he proposed the measurement that would confirm the mechanism, and Dan ran it.

The 0.7645 / 0.4686 gap in this repo's headline numbers is exactly this. It is not a defect —
it is the multi-hop problem stated numerically, and it is the single most useful thing on the
scorecard."""},
 ],
},
{
 "category": "Math & Theory", "author": "marcus",
 "title": "Why is Cohen's κ so brutal on our abstention labels when agreement is 85%?",
 "body": """Two of us labelled 120 answers as *abstain-correct* / *abstain-wrong*. We agree on
102 of them — 85%. κ comes out at **0.31**, which every rubric I can find calls "fair", i.e.
barely acceptable.

I do not think our labelling is that bad. Is κ the wrong statistic here, or are we?""",
 "replies": [
  {"by": "dan", "body": """85% sounds good to me. Can we just report the agreement percentage
and skip κ?"""},
  {"by": "lena", "body": """You can report it, but not skip κ — raw agreement is exactly the
number that is misleading here, and a reviewer will ask. The issue is prevalence.

$$\\kappa = \\frac{p_o - p_e}{1 - p_e}$$

where $p_e$ is agreement expected by chance *given each rater's marginal distribution*. If 90%
of your items are one class and both of you say that class 90% of the time:

$$p_e = 0.9 \\times 0.9 + 0.1 \\times 0.1 = 0.82$$

$$\\kappa = \\frac{0.85 - 0.82}{1 - 0.82} = \\frac{0.03}{0.18} = 0.167$$

You agree, but almost entirely by both following the base rate. κ asks the harder question: do
you agree *more than two people who never looked at the items but knew the base rate*. On a
skewed set, usually barely.

So κ is not wrong and neither are you. κ is measuring something you did not intend to
measure.""", "accepted": True},
  {"by": "marcus", "body": """Checked our marginals: 84% / 16%. So the mechanism is exactly as
described.

Follow-up — what do we do about it? Reporting κ = 0.31 with no context invites the conclusion
that the labels are junk."""},
  {"by": "lena", "body": """Four options, roughly in order of preference.

1. **Report both**, with the marginals. κ alone on a skewed set is uninterpretable; $p_o$ alone
   is misleading. Together they are honest.
2. **Stratify the annotation sample** so the class balance is nearer uniform. Then κ measures
   what you meant. This is the real fix and it costs you one afternoon of re-sampling.
3. **Use a statistic designed for skew** — Gwet's AC1 is explicitly stable under prevalence;
   Krippendorff's α if you go past two raters or have missing labels.
4. **Publish the confusion matrix.** κ compresses a 2×2 table into one number, and the
   disagreement is almost always concentrated in a single cell. That cell names the ambiguous
   rubric line, which is the thing you can actually fix."""},
  {"by": "sofia", "body": """Option 4 paid off immediately for us. All 18 disagreements were in
one cell: model abstained, and one rater called it correct-to-abstain while the other called it
a miss. The rubric said "abstain when evidence is insufficient" and never defined insufficient.

Rewrote that line with a threshold and a worked example. Re-labelled: agreement 94%, κ 0.71.
The statistic was fine; the rubric was ambiguous, and κ was the thing that told us."""},
  {"by": "maintainer", "body": """Marked. Sofia's follow-up is the point of the whole thread:
**a low κ is usually a rubric bug, not a rater bug.** Raters disagree where the instructions are
silent.

The interview version of this question is in
[docs/06-interview-prep/mathematics.md](../blob/main/docs/06-interview-prep/mathematics.md)
(M5), including the follow-up that catches most candidates — whether κ = 0.62 is good enough to
gate a release, where the answer depends entirely on whether the disagreement is noise or
bias."""},
 ],
},
]
