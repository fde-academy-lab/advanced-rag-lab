"""Weekly Standup & Retro, and Ideas.

Standups are the artefact that makes a project look worked-on rather than assembled. The third
line of each — what somebody was wrong about — is the one that carries information.
"""
from __future__ import annotations

THREADS = [
{
 "category": "Weekly Standup & Retro", "author": "maintainer",
 "title": "Week 3 · P2 Retrieval — the reranker week, and it did not go how we planned",
 "body": """### Moved

- **Hybrid fusion landed.** Weighted at α=0.2 beats equal-weight RRF and beats BM25 alone:
  evidence recall 0.7645 → 0.7891, [+0.008, +0.041], holds on frozen.
- **ANN graph fixed.** Long-range links added; recall at ef=64 went 0.00 → 0.94. Full write-up
  in the Debugging Clinic thread. Closed #2.
- **FTS5 tokenizer.** `tokenchars '_-'` restored; identifier-slice recall 0.34 → 0.81. Closed #1.

### Blocked

- **Reranker.** Second week on this. Every hand-tuned weight vector loses to no reranker at all.
  Grid search over 400 combinations: best is still below baseline. Blocked on a decision about
  whether to abandon the lexical-only feature set entirely, which is a bigger change than we
  scoped.
- **Frozen slice policy.** We will need to grow the corpus for P4 and nobody has decided whether
  the frozen slice is regenerated or preserved. Needs an ADR. I will draft it unless somebody
  objects in the next two days.

### Wrong about

I said in week 2 that the reranker underperforming was a sort-order bug. It is not — I checked
the sort three separate times, which in hindsight is the tell. A wiring bug is catastrophic; this
is *uniformly slightly worse at every k*, and that shape means the reranker is working correctly
and its features are wrong.

Cost of being wrong about this: roughly four days spent verifying code that was fine.

### Numbers

| | Week 2 | Week 3 |
|---|---|---|
| evidence_recall | 0.7301 | 0.7891 |
| full_chain_recall | 0.4074 | 0.4686 |
| ANN recall @ ef=64 | 0.00 | 0.94 |
| identifier slice | 0.34 | 0.81 |
| open issues | 11 | 7 |""",
 "replies": [
  {"by": "marcus", "body": """On the reranker: the shape you describe — uniformly slightly worse
at every k — is diagnostic and I think it points somewhere specific.

If the reranker were merely weak, you would expect it to be roughly neutral: it would shuffle
things without systematically demoting true positives. Uniformly worse means it is
*systematically* preferring something other than relevance.

Your first stage is a fused list. Your reranker's features are all lexical. So the reranker is
re-ranking a list that already used dense signal, using only lexical signal. It is not a weak
reranker — it is a **strictly less informed** one applied on top of a better-informed ordering.
It can only discard information.

That is not a tuning problem and no weight vector fixes it. The feature set has to see what the
dense leg saw."""},
  {"by": "priya", "body": """That reframes it completely. I have been treating "the weights are
wrong" as the hypothesis for two weeks.

Trying MaxSim between query and passage token embeddings, plus document-level cosine. If Marcus
is right those two features should carry most of the gain on their own."""},
  {"by": "tomas", "body": """On the frozen-slice ADR: draft it, and please include the option
nobody likes, which is that growing the corpus **invalidates the frozen slice permanently** and
we accept starting a new one.

The tempting option is regenerating the frozen slice from the grown corpus, which sounds
principled and is not — the new frozen slice has been chosen by a process that has already seen
the results from the old one, and that is a subtle way of leaking the thing the slice exists to
protect."""},
  {"by": "maintainer", "body": """Tomás — that is the argument that should decide the ADR and I
had not seen it that clearly. Drafting with three options: preserve and accept coverage decay,
regenerate and accept the leak, or start a new slice and report both during the transition.

Priya — please post the MaxSim result in the Debugging Clinic thread rather than here, so it is
findable later.

**Retro note for the phase:** the four days lost to the reranker were not lost to the bug, they
were lost to *the wrong hypothesis being cheap to test*. Checking a sort order three times is
easy, so we kept doing it. The expensive hypothesis — that the feature set was structurally
wrong — was the correct one and nobody tested it because it implied a rewrite.

Rule proposal for next phase: **when a cheap hypothesis fails twice, stop testing it and write
down the expensive one.**"""},
 ],
},
{
 "category": "Ideas", "author": "marcus",
 "title": "Idea: a 'measurement smell' linter that fails a PR describing a delta dishonestly",
 "body": """We have a lint for code style and a gate for metric regressions. We have nothing that
catches a PR body which reports a number badly, and that is where the real damage happens.

Proposed checks, run on the PR body:

| Smell | Pattern | Why it matters |
|---|---|---|
| Delta with no interval | a `Δ` or `+0.0x` with no `[` ... `]` nearby | An observation reported as a result |
| Cumulative sum of separate deltas | "cumulatively", "combined", "total improvement" plus 3+ numbers | Compounds uncertainty into a headline |
| Noise band laundering | interval spanning zero, described with "improves", "better", "gain" | The specific failure this repo cares about most |
| Missing k | "recall" without `@k` or `k=` | Recall rises trivially with k |
| Missing n | a per-slice number with no count | Invites conclusions from six questions |
| Frozen slice unstated | metric table with no "frozen" mention | Silence is not "not touched" |

Not blocking — a warning comment with the line quoted. A blocking linter on prose would be
insufferable and would get disabled within a month.""",
 "replies": [
  {"by": "priya", "body": """I want this specifically for the cumulative-sum one, having nearly
shipped exactly that in my capstone. The interval column in the template caught me; a lint
would have caught me earlier and with less embarrassment."""},
  {"by": "aarav", "body": """Sceptical about the noise-band check. Detecting "interval spans zero
AND the prose says improves" requires parsing which interval goes with which claim, and in a PR
body with four rows that mapping is genuinely ambiguous. False positives on a warning are how
warnings get ignored."""},
  {"by": "marcus", "body": """Fair. Narrow it: only fire when there is exactly one interval and
one claim sentence in the same paragraph. Precision over recall — a linter that fires on the
obvious cases and stays quiet on the ambiguous ones is used; one that fires on everything is
filtered out.

That also makes it implementable without a parser."""},
  {"by": "tomas", "body": """Add one: **a baseline moved without a reason in the body.** That one
is unambiguous — you can detect `eval-baseline.json` in the diff and look for a sentence near
it. It is also the highest-consequence smell on the list, because a silently-moved baseline
disables the gate permanently rather than for one PR.""", "accepted": True},
  {"by": "maintainer", "body": """Accepted as an issue with Tomás's addition as the first check
to build, since it is both unambiguous and the highest consequence.

Scoping note for whoever picks it up: start with three checks — baseline moved without a reason,
delta with no interval, and missing k. Ship those, see whether anyone complains about false
positives, then decide about the rest. A six-check linter shipped at once has no way to learn
which check is the annoying one."""},
 ],
},
]
