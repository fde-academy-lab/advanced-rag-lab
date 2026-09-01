"""Conversations for the three threads that were posted as single posts.

Each of these was a good opening post with nobody answering it. The replies here are what the
thread needed to be worth reading — a real objection, a measurement, and a resolution.
"""
from __future__ import annotations

REPLIES = {
"Design review: sufficiency check as a model call or": [
  {"by": "tomas", "body": """Operational objection before the design one. A model call in the
sufficiency check puts a network hop inside your stop condition. When the provider is slow, your
agent does not merely get slower — it stops being able to decide whether to stop, so it either
blocks or falls through to "keep going", and "keep going" on a broken stop condition is an
unbounded loop with a bill attached.

Whatever you choose, the fallback path when the check is unavailable has to be *stop*, not
*continue*. That is a one-line decision and it is the difference between a degraded agent and a
runaway one."""},
  {"by": "marcus", "body": """On the design: a heuristic and a model call are not the same kind
of thing and comparing them on accuracy alone hides that.

A heuristic over retrieval scores is measuring **similarity** — does the evidence look like the
question. Sufficiency is about **entailment** — does the evidence support an answer. Those come
apart exactly where it matters, which is the abstention finding in this repo: our null questions
name real entities in the corpus's own vocabulary, so they score *higher* on similarity than the
genuine paraphrased ones. A score heuristic there is not weak, it has the wrong sign.

So I would not frame this as heuristic-vs-model on cost. I would frame it as: is there any
cheap signal that measures entailment rather than similarity? If not, the model call is not a
convenience, it is the only thing that measures the right quantity."""},
  {"by": "wei", "body": """Middle path that worked for us: model call, but only when the
heuristic is *uncertain*.

Retrieval score is a bad classifier overall and a fine one at the extremes. Very high score with
strong agreement across legs — stop, no model call. Very low — stop and abstain, no model call.
The band in the middle is where the model call earns its cost, and for us that was about 20% of
steps.

You need the band boundaries measured rather than guessed, and they drift, so they need
rechecking. But it turned a per-step cost into a per-fifth-step cost."""},
  {"by": "sofia", "body": """One thing nobody has said: if the sufficiency check is a model call,
it sees the retrieved evidence. In a permissioned system that means the check is a second place
where documents cross a trust boundary, and it needs the same ACL reasoning as the generator.

Easy to miss because it feels like plumbing rather than a read."""},
  {"by": "maintainer", "body": """Resolution: Wei's banded approach, with Tomás's fail-stop
fallback and Sofia's note folded into the ACL story.

Marcus's reframing is the part to remember though — **similarity and entailment are different
quantities**, and most sufficiency checks in the wild measure the first while claiming the
second. That is the same mechanism as the abstention finding, arriving from a different
direction, and it is now issue #10.

This thread produced a decision, so it becomes an ADR rather than staying here."""},
],
"Negative result: contextual chunking cost 2.4x storage and did": [
  {"by": "dan", "body": """Genuinely useful to see this written up. Question — 2.4× storage is
the headline, but did the *index build time* change much? That is the number that would stop us
adopting it, more than disk."""},
  {"by": "priya", "body": """Not the original poster, but I ran the same thing. Build time went
up roughly 3.1× on our corpus, and almost all of it is the per-chunk generation call rather than
the indexing. So it scales with chunk count, not document count, which is the worse of the two.

For a corpus that reindexes nightly that is the difference between a 40-minute job and a
two-hour one. Survivable. For anything with an hourly freshness SLA it is disqualifying, because
the incremental path has to make the same call for every changed chunk."""},
  {"by": "lena", "body": """Worth being precise about what this result does and does not say,
because contextual retrieval is well-evidenced elsewhere and a flat "it did not work" would be
overclaiming.

The published results come from corpora where chunks are genuinely ambiguous out of context —
long documents where a chunk says "the rate was raised to 4.5%" and the entity is three sections
up. Our corpus is generated with the entity named in nearly every chunk, because the generator
writes self-contained passages.

So the honest statement is: **contextual chunking cannot help on a corpus whose chunks are
already self-contained**, and ours is, by construction. The precondition is absent. That is a
finding about our corpus, and it predicts where the technique *would* pay: long documents with
heavy anaphora and entity elision."""},
  {"by": "aarav", "body": """Which makes this the second time a technique has failed here for the
same reason — the corpus lacks the property the technique addresses. Comparison starvation was
the first.

I do not think that is a coincidence and I think it is worth naming as a limitation of the whole
eval set rather than filing two separate negative results. A generator that writes clean,
balanced, self-contained passages cannot test techniques that exist to fix messy, imbalanced,
context-dependent ones."""},
  {"by": "maintainer", "body": """Aarav's observation is the most valuable thing in this thread
and it changes what we build next.

Two negative results with the same root cause is not two findings, it is one finding about the
corpus generator: **it produces text that is too well-behaved to test robustness techniques.**
That is now issue #14, widened from "adversarial eval slice" to "a corpus mode that deliberately
produces anaphora, elision, imbalance and near-duplicates".

Lena's framing is the one to use when writing this up: name the precondition, say it is absent,
and predict where the technique would pay. A negative result without that is an anecdote."""},
],
"Idea: replay a real cohort's questions as an eval slice": [
  {"by": "sofia", "body": """Strongly in favour, with one hard constraint: the questions have to
be scrubbed before they go anywhere near a committed file.

Cohort questions contain employer names, project details and occasionally things people would
not want indexed by a search engine. A public repository is a publication. That is not a reason
not to do it, it is a reason the pipeline needs a review step with a human in it."""},
  {"by": "marcus", "body": """The methodological value here is bigger than it looks and worth
spelling out.

Every question in the current eval set was written by a generator that also knows the answer.
That guarantees the answer exists and makes gold evidence true by construction — which is why
there is no annotation-error floor under any of our numbers. It also means **no question in the
set is badly posed**, and badly-posed questions are most of real traffic.

A cohort slice would be the first thing here that tests the failure where the *question* is the
problem: ambiguous referents, two questions in one sentence, an assumed premise that is false. I
would expect our numbers to be dramatically worse on it, and that gap is the interesting
measurement."""},
  {"by": "dan", "body": """Would the questions need gold labels? That is the part that sounds
expensive — someone has to decide what the right answer was."""},
  {"by": "wei", "body": """Not necessarily, and this is the trick that makes it affordable.

You do not need gold evidence to measure **abstention behaviour** or **reformulation**. If a
cohort member asked a question and then immediately asked a rephrased version, that is a
labelled failure they gave you for free — no annotator required. Same for a question followed by
"that's not what I meant".

Start there. Label gold evidence later, only for the subset where the cheap signals disagree
with the system's confidence, which is a much smaller set than labelling everything.""",
   "accepted": True},
  {"by": "maintainer", "body": """Accepted with Sofia's scrubbing requirement as a blocking
precondition and Wei's cheap-signals-first sequencing.

Scoping for whoever takes this: the first version is not an eval slice, it is a **logging
schema** — question, timestamp, whether a reformulation followed within N minutes, whether the
system abstained. That is a week of work and it produces the raw material. Turning it into a
graded slice comes after, and only for the subset Wei describes.

Filed. Marcus's point about badly-posed questions goes in the issue body — it is the reason this
is worth doing rather than a nice-to-have."""},
],
}
