# Behavioural

The round people under-prepare because it looks like the easy one. It is not — it is where
offers get downgraded from senior to mid, because the technical rounds established that you
*can* do the work and this one establishes whether anyone wants to work with you while you do.

Every question below is answered with the **STAR-plus-number** shape: situation, task, action,
result, and *the number*. In an applied-ML role a behavioural answer without a measurement is
half an answer, and the panel notices.

---

## B1 · "Tell me about a time you were wrong about something technical"

The most common opener and the one most often answered badly. Interviewers report two failure
modes: the humblebrag ("I was wrong to work too hard"), and the trivial admission ("I picked
the wrong variable name").

### What they are scoring

| | Signal |
|---|---|
| ✗ | A disguised strength, or a mistake with no consequence |
| ○ | A real mistake, but the lesson is generic ("communicate more") |
| ● | A real mistake with a specific mechanism and a specific process change |
| ★ | The mistake was in *reasoning*, they caught it themselves, and the fix is still in place |

### What ★ sounds like

> "I shipped a reranker that made retrieval worse and I did not notice for two weeks, because I
> was reading the wrong number.
>
> I'd built a cross-encoder over eight pair features — coverage, phrase match, title match, that
> family. Offline it looked fine on the queries I spot-checked. What I hadn't done was measure
> it against the un-reranked baseline at every k. When I finally did, evidence recall at k=5 went
> from 0.773 to **0.630**. Worse at every k, which in hindsight is the signature of a systematic
> problem rather than a bug.
>
> The reasoning error was specific: all eight features were lexical, and the first-stage list was
> already a *fusion* of lexical and dense. So my reranker was applying a worse BM25 on top of a
> list that had used more information than BM25 had. I was adding a stage that could only
> discard signal.
>
> Two fixes. Genuinely pairwise semantic features — MaxSim and document cosine — so it could see
> what the dense leg saw. And I stopped hand-tuning the weights; a grid search over hand-picked
> values never beat the baseline, and a logistic regression fitted on a dev slice got +8 points
> of evidence recall, holding on frozen.
>
> The process change that stuck: **no component ships without a comparison against removing it.**
> It sounds obvious. It was not obvious to me at the time, because I was measuring whether the
> reranker was good rather than whether it was better than nothing."

**Why this works:** the mistake is real and consequential, the mechanism is precise, the
candidate found it themselves, and the process change is concrete rather than aspirational.

---

## B2 · "Tell me about a disagreement with a colleague"

Scoring whether you can hold a position without making it personal, and — the part people miss —
whether you can **lose** one gracefully.

**✗:** A story where the candidate was right and the colleague came around. Every candidate
tells this one and it teaches the panel nothing.

**★:**
> "A colleague argued that a negative result we'd got — that a particular effect didn't reproduce
> on our corpus — was worthless, because it was an artefact of our test data rather than a fact
> about retrieval. He said he wouldn't put it in front of a client as either.
>
> He was right, and my first reaction was defensive, because I'd spent two days on it.
>
> What changed my mind was writing out what I'd actually claim. I couldn't claim the effect was
> false — our corpus was balanced by construction, so it lacked the precondition entirely. What I
> *could* claim was something about eval sets: a balanced generator cannot measure imbalance
> failures, and most generators are balanced because balanced generators are easier to write. So
> a whole class of real failures is invisible to most people's evaluation, and they conclude the
> failure is rare.
>
> That reframing was better than my original conclusion and I would not have got there without
> the objection. It became a tracked piece of work — an adversarial eval slice with prevalence
> ratios out to 20:1.
>
> What I'd do differently: I got defensive for about an hour first. The tell was that I was
> arguing about whether the work was valuable rather than about what it showed."

The self-observation at the end — naming the defensiveness and its tell — is what separates
this from a story about being reasonable.

---

## B3 · "A stakeholder wants something you think is a bad idea"

**Style:** consulting, forward-deployed, any client-facing role. Almost guaranteed.

They are scoring whether you can disagree *and still deliver*, rather than either capitulating
or obstructing.

> "A client wanted an agentic system because they'd seen a demo. My read was that most of their
> traffic was single-hop and an agent would multiply cost and latency by the number of steps for
> no benefit on the majority of queries.
>
> What I didn't do was tell them agents were overhyped. That's an argument you lose even when
> you're right, because they've already decided and you've made it about who's smarter.
>
> What I did: asked what they'd seen that made them ask. There was a real failure underneath —
> a class of question their system consistently got half-right — and 'agent' was just the word
> attached to it. So I proposed measuring the multi-hop fraction of their actual traffic before
> building anything. Two days of work.
>
> It came back around 12%. That reframed the whole conversation: route the 12% to a multi-step
> path and leave the rest single-shot. They got the capability on the queries that needed it at
> roughly an eighth of the cost, and — this mattered more than I expected — it was *their*
> number, from their traffic, so nobody had to take my word for anything.
>
> If it had come back at 40% I'd have built the agent, and I'd have been wrong in my initial
> read. The measurement was the point, not my opinion."

---

## B4 · "Tell me about something you shipped that failed"

Distinct from B1: that was about being wrong, this is about consequence and recovery.

The structure that lands: **what broke, how you found out, what you did in the first hour, what
you changed so the class of failure can't recur.**

> "We changed the tokenizer on a search index. Overall recall dropped about 5 points, which read
> as noise in review, and it went out.
>
> What we hadn't measured was per-slice. On queries naming error codes — `ERR_CONN_RESET` and
> that family — recall went from 0.81 to **0.34**. The default tokenizer split the identifier
> into `err` / `conn` / `reset`, and all three are common words in that corpus, so the identifier
> didn't just fail to match, it matched everything. A high-precision query became a high-recall
> one.
>
> We found out from users, not from monitoring, which is the part I actually regret. The
> aggregate never moved enough to alert.
>
> First hour: reverted, which was cheap because the index was versioned behind an alias and the
> rollback was a pointer swap rather than a rebuild. That design decision paid for itself in one
> incident.
>
> What changed permanently: slice-level alerting rather than aggregate only, and the analyzer
> configuration is now part of the index version string — so a tokenizer change forces a reindex
> instead of silently producing a corpus that's half one scheme and half the other."

---

## B5 · "How do you handle being the only person who knows something?"

Asked of senior candidates. Tests whether you build dependency or capability.

> "I treat it as a defect I introduced. The honest version is that it usually happens because I
> moved fast and didn't write anything down, not because the thing is intrinsically hard.
>
> Concretely: architecture decision records for anything where a future person would reasonably
> ask 'why is it like this' — Nygard format, one page, context and consequences, including the
> options rejected and why. The rejected options are the valuable half and they're the half
> everyone omits.
>
> Then runbooks written as decision trees starting from the *symptom*, because at 3am you don't
> know the cause — that's why you're reading it.
>
> And I try not to be the person who reviews everything in my area, because that's the
> comfortable version of the same bug. If I'm the only competent reviewer for a module, I've
> failed at something."

---

## B6 · "Why this role?"

Sounds like a formality. It is a filter, and a generic answer costs you.

**✗:** "I'm passionate about AI and your company is doing exciting work."

**★:** Names something specific about *their* problem, connects it to something you have done,
and asks a real question:

> "The part of this that interests me is that you're deploying into customer environments rather
> than running one system you control. That changes the evaluation problem completely — you can't
> carry a golden eval set between clients, so you have to be able to manufacture one quickly with
> whatever's there. I've done exactly that under a one-week constraint and it's the least
> discussed and most decisive part of the work.
>
> What I'd want to know is how your team handles the eval-set-per-client problem today, and
> whether there's tooling for it or it's rebuilt each time."

---

## B7 · Rapid rounds

| Question | The trap | The ★ move |
|---|---|---|
| *"Greatest weakness?"* | A strength in disguise | A real one, plus the compensating mechanism you actually run. "I under-communicate when I'm deep in something, so I post a written status on Fridays whether or not anything is finished" |
| *"How do you prioritise?"* | Listing a framework | Name the tradeoff you actually made and what you dropped. Frameworks are cheap; a decision with a casualty is evidence |
| *"Where do you want to be in five years?"* | Ambition theatre | Say what kind of *problem* you want to be closer to, not what title. Then ask what the growth path for this role has actually looked like for someone who took it |
| *"Tell me about mentoring"* | Claiming credit for someone else's growth | One specific thing you changed about how someone works, and how you know it stuck |
| *"Questions for us?"* | Having none, or asking about perks | *"What's the last retrieval change that didn't work, and how did you find out?"* — the best question you can ask a team like this, and their answer tells you whether they measure |

---

## Preparing without sounding rehearsed

Write six stories, not answers. Each needs: the situation in one sentence, the specific
technical mechanism, the number, and what changed permanently. Six stories cover almost every
behavioural question, because the same story answers "wrong", "failed", "disagreed" and "learned"
depending on which part you lead with.

Then say them out loud once and cut a third. The commonest behavioural failure at senior level
is not a bad story — it is a four-minute answer to a question that deserved ninety seconds,
which leaves no room for the follow-up where the actual assessment happens.

**And bring a number to every one.** "Recall went from 0.773 to 0.630" is not showing off; it is
the difference between a story and an anecdote, and in an applied-ML loop the panel is
specifically listening for whether you measure the things you claim.
