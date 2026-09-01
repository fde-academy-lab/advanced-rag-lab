"""General: three threads about the forum itself, rather than about retrieval.

General is the category with no subject matter, which normally makes it a bin. These three
threads are an attempt to give it one: **claims about how this place works**, kept apart from
claims about how the system behaves. A thread here should still be wrong about something and
then corrected, because a meta thread nobody argues with is a policy document wearing a costume.

Thread 1 adds the column the guide's category table does not have. Thread 2 is the question
every part-time reader actually has and the guide never answers. Thread 3 is the one that stops a figure from
this repository reaching somebody's slide without its configuration, which has already happened
once, at our own hands, and is written up as a retraction.

General is an open-ended category, so nothing here is marked as an accepted answer. The
resolution replies are still the resolution.
"""
from __future__ import annotations

CAT = "General"

THREADS = [
{
 "category": CAT, "author": "maintainer",
 "title": "Where does this go? The column the category table does not have",
 "body": """The [discussions guide](/fde-academy-lab/advanced-rag-lab/blob/main/docs/10-community/discussions-guide.md)
tables all fourteen categories — the six GitHub creates by default plus the eight added in
`scripts/seed_content.py` — and says what each is for. That is the question it answers well.

The question it does not answer is the one people actually have with a half-written post in front
of them: **when does a thread stop belonging here?** So this is the same fourteen with a second
column, and the second column is the one worth reading.

| Category | Post here when | Does not belong here |
|---|---|---|
| 📣 **Announcements** | A schedule, a release, a break | Questions about it → **Q&A** |
| 💬 **General** | A claim about how this forum works | Anything carrying a measurement → **Q&A** |
| 🙋 **Q&A** | "Why does X behave this way?" | A defect with a reproduction → **issue** |
| 🐞 **Debugging Clinic** | A failure you cannot explain, symptom first | Install and environment trouble → **Q&A** |
| 🏗 **Design Reviews** | An architecture you want attacked first | Something you already built → **Show and tell** |
| 🎤 **Show and tell** | Finished work, including what failed | Work in progress → **Design Reviews** |
| 🧪 **Exercises & Submissions** | An EX-NN approach, submission or review | A simulator unit → **L.A.B. Simulator** |
| 🧪 **L.A.B. Simulator** | A unit for the grader, approach before code | A grader you think is wrong → **issue** |
| 🧮 **Math & Theory** | The question behind the formula, in LaTeX | "Which should I ship?" → **Design Reviews** |
| 📚 **Reading Club** | The argument about an assigned paper | The assignment itself → **issue** |
| 💡 **Ideas** | A half-formed extension | An idea with a hypothesis → **extension issue** |
| 🗳 **Polls** | Scheduling, topic order | A technical decision → **Design Reviews** |
| 🎯 **Interview Prep** | An answer you want critiqued | Anything under NDA → nowhere |
| 🗓 **Weekly Standup & Retro** | A reply to this week's thread | A new question it raised → **Q&A** |

## The three conversions people get wrong

**Q&A becomes an issue** when it acquires an owner and acceptance criteria. Most people ask "is this a bug". The question that actually routes it is whether a third person
could tell when it is done.

**A Design Review becomes an ADR** when the losing option has been named and costed. An ADR
whose *options considered* section holds only the option taken describes the code, and the code
already does that.

**Show and tell becomes an exercise** when it reproduces from a clean checkout *and* has a trap:
the plausible approach that fails, which
[exercise-workflow.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/10-community/exercise-workflow.md)
requires a brief to name in advance. A reproducible result with no trap is a good post and a bad
exercise.

And the highest-value one: **a Q&A thread answered for the third time is a docs PR.**""",
 "replies": [
  {"by": "wei", "body": """Fourteen categories for a cohort this size is over-engineering, and I
say that having watched it go the other way. At my last company we ran one Discussions category
against a four-hundred-engineer monorepo and a separate bug tracker, and nobody ever failed to
find a thread. GitHub search is full text and it does not care what category you filed under.

What a split does buy you is a new way to be wrong. A miscategorised thread is worse than an
uncategorised one, because now it is somewhere specific and that somewhere is misleading. You
have built a filing system, and filing systems get filed in badly.

If the worry is that Q&A gets noisy, labels do this without asking anybody to choose up front,
and a label can be corrected without moving the thread out from under the people watching it."""},
  {"by": "tomas", "body": """Finding it is not the part I would worry about. The part I would
worry about is the on-call version: somebody hits the prompt cache behaviour at 21:00, and the
difference between a Q&A thread and a Debugging Clinic thread is whether the reader is expected
to answer or expected to help narrow it down. Those are different asks and one of them can be
served by a stranger.

Practical suggestion, since miscategorisation is the real cost Wei names. Can we restrict who
opens threads in the graded categories, and require a template everywhere? Nine categories have
forms in `.github/DISCUSSION_TEMPLATE/`; the five without are Announcements, General, Ideas,
Polls and Weekly Standup. If a thread cannot be opened in the wrong place, the map stops needing
to be read."""},
  {"by": "dan", "body": """I am the miscategorisation, so here is the data point.

Week one I filed my R2 confusion as an issue. It was closed inside ten minutes with a link to
Q&A, and I spent the evening assuming I had broken a rule nobody had told me about. Then I read
Wei's argument, decided one surface was simpler, and posted a design I had not built yet into
Q&A. Moved again.

Two for two, and both corrections were right and friendly and I still felt like an idiot. What I
want is not a longer table. It is one test I can apply in the ten seconds before I press
post."""},
  {"by": "maintainer", "body": """Dan, the ten-second test is: **what has to happen for this
thread to be finished?**

That is also the answer to Wei, and Wei is right under a condition worth naming. One category is
correct while the number of concurrently open threads stays under what one person will scroll in
a sitting. Below that line a split costs you miscategorisation and buys nothing, which is what he
saw. Above it, the first thing to degrade is ownership. Each category names an ending, and the endings are different work: a
Q&A thread ends in a marked answer, a Design Review ends in an ADR or a decision to abandon, an
Exercises thread ends in a peer review by somebody who owes one, a Simulator thread ends in a
green grader run, a Debugging Clinic thread ends when the cause is named and the general form of
it has been reposted in Q&A so it is searchable by symptom. A thread in the wrong category is a
thread whose ending nobody is responsible for, and those never surface as missing. They surface
as a forum that feels quiet.

Tomás, no on the lock, and mostly yes on the forms — nine have one already. The five without
are the ones where a form would cost more than it buys: Announcements, General, Ideas and Polls
are open-ended by nature, and Weekly Standup is written by maintainers to a fixed shape already.

The general rule is that a form earns its cost where the *order of the fields is the teaching* —
approach before code, what you have already ruled out before what you think. Where there is no
such order, a form turns a thirty-second post into a chore, and the threads we most want are the
ones somebody nearly did not bother to write. Moving a thread is cheap. Not writing it is not
recoverable."""},
  {"by": "sofia", "body": """Before we route anything else: which of these are visible outside
the cohort, and can Exercises & Submissions be restricted to enrolled people? A submission
carries half-finished reasoning with a real name on it, and I would rather a client of mine did
not read mine while I am mid-way through being wrong in public.

I think the categorisation question is downstream of this one. If half the categories should be
private and none of them can be, the map is describing something we have not actually decided
yet, and I would want that settled before anybody writes the docs PR."""},
  {"by": "aarav", "body": """Honestly, good enough. I will post in General and let a maintainer
move it if I have guessed wrong. Optimising my own filing is not where my thirty minutes should
go, and the correction costs one of you about four seconds.

Sofia's question I would like an answer to though, because I have been assuming this is public
and telling clients so, which is a thing I have now said out loud in two engagements. If that
assumption is wrong I have a considerably more interesting problem than where to put a thread,
and I would rather find out here than from a client's counsel."""},
  {"by": "priya", "body": """Sofia — all fourteen are public, and it is a decision rather than an
oversight. It is why the corpus is generated rather than borrowed, see
[ADR-0002](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0002-synthetic-corpus.md).
There is no client data here for a permission boundary to protect, so adding one would cost the
thing the public archive is for, which is next cohort reading this year's wrong turns.

Aarav — the move is one click for a maintainer and it is not free. The notification went to the
people watching General rather than the people watching Debugging Clinic, and those are
different people. Your thread lands in the right place with its audience already past it, and
you read that as nobody knowing the answer.

Ten seconds and Dan's test. It really is only ten seconds."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "I have thirty minutes a week. What order do I do this in?",
 "body": """Genuine constraint, not a complaint. I am consulting four days a week and
client-facing on the fifth. Thirty minutes on a Sunday evening is what exists, and it is one
block rather than three tens.

What I have done so far, which I do not recommend. A client asked whether they should add a
reranker, so I opened notebook `04` because the title matched the question. Twenty of the thirty
minutes went on running the cells above it to get a live kernel, and the remaining ten went on
working out that the answer to their question was not in the notebook I had opened. The next
week I started again from a cold kernel and did the same twenty minutes over.

So the naive answer, "open the thing that matches your question", is actively wrong here. What I
want is the ordering, and I want it from people whose week looks like mine rather than from
somebody with a free Saturday.

Three specific questions.

1. Notebooks in order, the L.A.B. Simulator, or the docs? They look like three entrances to the
   same building and I cannot tell which one is the front.
2. Is there anything that genuinely does not survive being put down for a week? The recall
   budget in `01` keeps getting described as load-bearing and I have not read it.
3. What is the smallest thing I can do that leaves something behind? Half my thirty minutes
   evaporates re-establishing where I was, and I would rather drive that cost to zero than get
   slightly further each week.

Twelve weeks of this is six hours in total. I would like to spend them somewhere that
compounds.""",
 "replies": [
  {"by": "wei", "body": """Notebooks, `00` through `09`, in order, and do not skip `01`.

I have onboarded six engineers onto a RAG codebase this way and it is the only route that
produced people who could argue about retrieval rather than repeat things about it. The
notebooks are the curriculum. The simulator is practice for material you have already met, and
practice before exposure is being confused with a grader watching.

Your kernel problem is a tooling problem with a tooling answer: *Run All* at the top of the
session, which is fast on this corpus because there is no dataset to fetch, then work from the
bottom. The twenty minutes buys reading the cells on the way down. The kernel finishing is incidental.

Thirty minutes a week is thin for this. I would rather you took twelve weeks over the notebooks
than twelve weeks over something lighter."""},
  {"by": "priya", "body": """Opposite advice, for exactly your constraint.

Start with the simulator, and start with **R2**, which is a `decide` unit with no code in it at
all. Reasons, ordered by how much they matter for a single Sunday block:

- A unit fits a sitting. Brief, one thing to hand in, a grader that names the promise you broke.
  When you put it down you have either cleared it or you have a specific red check waiting, and
  neither needs re-establishing next week.
- The notebooks are continuous. They assume a live kernel, and a reader who is still holding what an
  early cell established by the time they reach a late one. Fine for a Saturday, bad across a
  seven-day gap.
- R2 makes you commit to a decision before you have seen the measurement, and the gap between
  what you committed to and what R3 then shows you is the part that sticks.

I would not have said this a month ago. I did the notebooks first, in a week off, and I retained
the units better."""},
  {"by": "lena", "body": """Neither. Read the retractions first, then decide.

[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
and the
[multi-hop independence note](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/multi-hop-independence.md)
are the two places where this repository says out loud that it published something false and
then shows the re-measurement. Twenty minutes for both, and they are self-contained, which is the
property you asked for in your third question.

There is a learning-science argument as well. The testing-effect literature is consistent that
retrieval practice under difficulty beats re-reading, which is the case for Priya's ordering, and
the error-correction work suggests that reading a corrected error fixes the correction better
than reading the correct version alone. Roediger and Karpicke is the standard citation.

So: retractions, then simulator, then notebooks as reference rather than as a course."""},
  {"by": "marcus", "body": """Lena, the testing-effect work you are reaching for is mostly
undergraduates recalling word pairs and prose passages in twenty-minute laboratory sessions with
a retention interval measured in days. Aarav is a working consultant with a seven-day gap, one
block, and a transfer target of "argue with a client about reranking" rather than "recall the
passage". The direction may well carry. The size of it, and whether it survives a week between
sessions, is not something that design can tell you, and I would not build a twelve-week
ordering on it.

What I would do is measure it. Pick the two candidate orderings, define what "it worked" means
before starting — say, stating the fusion finding and its interval without opening anything —
and run six weeks of each. Otherwise we are four people asserting orderings with no evidence,
which is the thing this repository is supposedly about not doing.

I realise that is twelve weeks before you get an answer to a question you have this Sunday."""},
  {"by": "maintainer", "body": """Marcus is right that we cannot measure this for you, and Wei
and Priya are each right for a different person. Splitting the difference gives you the worst of
it, so here is the split that matters.

**The mechanism.** Thirty minutes sits below the restart cost of the notebooks. They assume a
continuous session and a live kernel, so the cost of getting back to where you were is charged
again every week. Simulator units are priced the other way round. The real question is which
unit of work fits one sitting and survives being put down.

**Then, which of them you are.**

- *You will build retrieval yourself this quarter.* Notebooks, Wei's route, in 45-minute blocks
  rather than 30. Under that the restart cost eats the session. `01` is the one that cannot be
  skipped, because everything after it assumes the recall budget.
- *You will be in a room defending someone else's decision.* Simulator, Priya's route, R2 first.
  The artefact it makes you produce is the artefact a design review asks for.
- *You will quote this repository to a client.* Retractions first, Lena's route, for a reason
  unrelated to learning science: the most quotable finding here was wrong for a while, and it
  propagated into the README, the interview banks and the seeded threads. RRF beats BM25 by
  +0.0624, ci (+0.0407, +0.0857), and the dense leg is the stronger one.

Aarav, the third one is you."""},
  {"by": "aarav", "body": """Reporting back after three weeks, since I asked.

Retractions first. Then R2, which took two sittings rather than one because the grader rejected
me before running anything — the falsifier field wanted an observation and I had written a
conditional about my own conclusion.

Two things surprised me. The first is that I now understand why my client's reranker question
was unanswerable as posed: on this corpus every fusion arm sits inside the noise band on
`answer_correct`, so "which fusion do you recommend" has no honest answer that is about fusion.
The retrieval numbers move by 9.4% relative and the thing they are supposedly for does not move
at all.

The second is that I have not opened a notebook yet and do not feel behind. I will, when I need
to build one. I had been treating them as the course because they are the biggest thing in the
repository, which is not a reason."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "How to read a number here, because I quoted one and could not defend it",
 "body": """Put this on a slide for an internal review last Thursday:

> **Evidence recall: 0.7645**

Got three questions back and could not answer any of them.

1. "At what *k*?"
2. "Is that with the reranker?"
3. "Compared to what?"

The number is real. I took it from
[metrics.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/04-evaluation/metrics.md), it is
the current scorecard value, and I have not mistyped it. It was still the wrong thing to put on
a slide, and I would like to understand why rather than just have this one slide corrected.

What made it worse was that the follow-up was reasonable and I had no way to answer it live.
Somebody asked whether 0.7645 was good. The honest answer turned out to be that the same metric
over the same 243 questions spans 0.7118 to 0.7790 depending which arm you run, and I had quoted
one point on that range as though it were a property of the system.

So, the general question, and I want the rule rather than the fix. What has to travel with a
figure from this repository? What is the minimum you carry alongside it so that pasting it
somewhere does not create a claim you cannot support three weeks later, in a room, without the
person who wrote the harness there?

And is there something I can run before pasting, rather than a habit I am meant to acquire?""",
 "replies": [
  {"by": "wei", "body": """The rule I use is simple: only quote the committed baseline. It lives
in `.github/eval-baseline.json`, CI gates against it, and it is by definition the number that
describes the shipped system. Everything else is a sweep result, and sweeps are exploratory.

If somebody asks "compared to what", the baseline is the answer to that. It is what the system
does today, and the comparison the gate makes is against the same configuration yesterday.

The number was fine. What it lacked was a home — a configuration, a date, a command. Say "the shipped default scores
0.7645 evidence recall" and the config question stops being interesting, because there is only
one shipped default and everyone in the room is looking at it."""},
  {"by": "marcus", "body": """That rule is roughly what produced the retraction, so I would be
careful with it.

The committed baseline is one configuration on one slice. Three things it hides, all of which
somebody in a review can and will ask about:

| | |
|---|---|
| **The arm** | `structural/weighted/cross/k=8`. Set the reranker to `none` and BM25 at the same k goes 0.7118 → 0.6184. Same metric, same questions, different claim. |
| **The k** | Weighted α=0.2 evidence recall is 0.5024 at k=3, 0.7645 at k=8, 0.8567 at k=20. "Evidence recall 0.76" with no k is a point on a curve you have not shown. |
| **The slice** | `answer_correct` 0.4115 over 243 averages question types that behave nothing alike: comparison 0.848, inference 0.579, temporal 0.091, null 0.000. A stakeholder hearing 0.4115 imagines uniform mediocrity, when one slice is nearly solved and another is broken. |

And on your last point: the gate compares a configuration against its own past self and never
compares configurations against each other. That is stated in
[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
as the reason nothing caught the fusion error for as long as it did. A baseline answers "has
this changed since Tuesday". It cannot answer "is this the best arm we have"."""},
  {"by": "lena", "body": """For "is 0.7645 good" you can anchor against published work.
Anthropic's contextual retrieval write-up reports failed retrieval dropping from 5.7% to 1.9%,
at roughly $1.02 per million document tokens to build the index.

That gives Dan an external reference point for what a tuned retrieval stack looks like, and it
has the advantage of being a number a client has probably already seen. On the face of it,
0.7645 evidence recall is a long way from a 1.9% failure rate, and I would want to know why
before putting either on a slide next to the other."""},
  {"by": "marcus", "body": """Those two cannot go next to each other, and putting them there is
Dan's error one level up.

Failed retrieval at 1.9% is per query: did the right chunk appear at all. Evidence recall here
is per gold evidence piece, at k=8, over a set where half the answerable questions need four or
more pieces. Different denominator, different k, different corpus, different
question generator. The complement of 0.7645 is not comparable to 1.9%, and the direction of the
incomparability is not even obvious without working it through.

The Anthropic figure is worth citing for its mechanism, which is that prepending document
context to a chunk before embedding changes what that chunk can match. It is not a bar."""},
  {"by": "maintainer", "body": """Dan asked for the rule. There is one, and it comes with a case
study where we broke it ourselves.

**A figure here is five things, and quoting fewer creates a claim you cannot defend.**

```
metric        evidence_recall
config        structural/weighted/cross/k=8    chunker / fusion / reranker / k
slice         all, n=243                       or dev, or frozen, and say which
comparison    against which other arm
interval      the paired bootstrap, 95%
```

The last two do different work. A figure with no comparison tells you what happened once. A
comparison with no interval tells you what somebody hoped happened: `dense → rrf` on evidence
recall is +0.0008 with an interval of (−0.0101, +0.0109), and the point estimate alone reads as
a small win when the honest reading is that there is nothing to report.

**The case study.** ADR-0015 exists because `0.7645`, the tuned configuration's number, appeared
in at least one document attributed to *BM25 alone*, whose real value is `0.7118`. One label
slip. A mechanism story was built on top of it and stood for months. The figure was never wrong.
Its config was.

**Before you paste, run the arm you are about to claim.**

```
python scripts/run_eval.py --compare
python scripts/run_eval.py --fusion rrf --k 8 --slice frozen
```

`--compare` prints the arms side by side with intervals, and that table is what belongs on the
slide. If you take a number off the frozen slice, say that you looked."""},
  {"by": "tomas", "body": """The runbook version, since numbers leak into operational docs too
and nobody re-reads those.

A figure in a runbook needs the same five fields plus a date and the command that produced it.
The 3am failure has nothing to do with the number being wrong. Somebody reads "expected recall
0.7645", observes 0.7118, and pages a person, when 0.7118 is what this same system does at k=8
with the lexical leg alone and no fusion, and the config changed in a PR six weeks ago that moved nothing anybody
was watching.

Aggregates hide the thing you actually want alerted on. `abstention_recall` is 0.0000, with 36
false answers on the null slice and 0 over-refusals. Fold that into one quality figure and the
system looks mediocre. Read it as a slice and it is telling you something specific: every
unanswerable question gets a confident answer, and nothing declines anything, ever. Those need
different pages and different fixes."""},
  {"by": "dan", "body": """Rewrote the slide. One line longer, and I can defend all of it.

> Evidence recall 0.7645, config `structural/weighted/cross/k=8`, all 243 questions.
> Equal-weight RRF, same corpus and same k, is 0.7742. That is +0.0008 over the dense leg
> alone, 95% interval (−0.0101, +0.0109), so those two are not distinguishable here.
> `python scripts/run_eval.py --compare` reproduces it.

The thing I got wrong was not carelessness, which is what I assumed on Thursday. I was carrying
a `metric: value` model of what a measurement is. Every document in this repository quotes
figures the other way round with the config attached, and I read straight past that for six
weeks because the shape looked familiar enough.

Also filing Marcus and Lena's exchange for myself. I would have put that 5.7% → 1.9% on the next
slide without hesitating."""},
 ],
},
]
