# Mental models for the room

Eight named procedures. Each one is a thing you *do* in the first fifteen seconds after a
question lands, before you have decided what the answer is.

They exist because the failure at senior level is almost never ignorance. It is a candidate who
knows the answer, takes ninety seconds to organise it out loud, and runs out of clock before the
follow-up where the marks actually are. A named procedure removes the organising time.

Each model below gives: **when it fires**, **the procedure**, **a worked case**, and **the
failure it prevents**. Learn the trigger, not the prose.

---

## 1 · Two timelines

**Fires when:** any "how would you build / walk me through" question about a retrieval or ML
system.

**Procedure.** Before drawing anything, split the answer into *index time* (paid once per
document, can be slow, decides most of the quality) and *query time* (paid every request, has a
latency budget). Say which you are describing at every moment.

**Worked case.** "Walk me through what happens between a user typing a question and an answer
coming back."

> "Two timelines, because they have completely different cost models. Index-time: ingest, chunk,
> embed, write. Slow is fine, it is a batch job, and it is where most quality is decided.
> Query-time, on an 800ms budget: retrieve ~40ms, rerank ~120ms, generate 400–600ms. Generation
> is 70% of the budget, so 'make it faster' means output tokens or model size, not a faster
> vector database."

**Prevents:** the answer that mixes freshness, latency and quality into one undifferentiated
pipeline, and then falls apart when the interviewer asks about a policy document changing at 9am.

---

## 2 · Name the denominator

**Fires when:** anyone says a number. Yours or theirs.

**Procedure.** Ask three things about it, out loud: **n**, the **unit of analysis**, and the
**slice**. A metric without those is not a result.

**Worked case.** "Our recall is 89%."

> "Recall at what k, over how many queries, and per what — per evidence piece or per question?
> Those are different numbers. Our per-piece is 0.76 and our per-question is 0.47, and the gap
> between them is the entire multi-hop story."

**Prevents:** accepting an aggregate that hides the slice generating every complaint. Also
prevents *your* numbers being dismissed, because a number offered with its denominator is much
harder to wave away.

---

## 3 · Cheapest diagnostic first

**Fires when:** you are asked to debug something, or asked what you would do about a problem.

**Procedure.** Order your hypotheses by **cost × likelihood**, and say the ordering out loud
before you start. Then name the first thing you would actually run.

**Worked case.** "Users say search is broken. Recall@10 is 0.89 and stable."

> "Four candidates, in order of how often they are the answer: the eval set has drifted from
> production traffic; the average is hiding a slice; recall is not the metric users experience;
> or it is not retrieval at all and the generator is failing on correct context.
>
> The first thing I would actually do is take twenty complaint queries and run them by hand.
> Twenty is usually enough to see the pattern, and it costs an afternoon rather than a sprint."

**Prevents:** the instrumentation answer — "I'd add tracing and dashboards" — which is correct,
expensive, slow, and reads as someone who has not had to find a bug this week.

---

## 4 · The third case

**Fires when:** you or the interviewer frame something as a binary.

**Procedure.** Binary framings in retrieval almost always hide a third case. Find it and say it.

**Worked case.** "How do you tell a retrieval failure from a generation failure?"

The binary is *retrieved / not retrieved*. The third case:

> "Retrieved **and** unused. The evidence was in the context and the model did not use it —
> position matters, and a fact in the middle of a long context is measurably less likely to be
> used than the same fact at the start. So 'retrieved' is not the same as 'used', and my two-way
> split has a third bucket in it. The number that separates them is answer accuracy *conditioned
> on* correct retrieval."

**Other common third cases:** relevant-but-redundant (near-duplicates filling k); correct answer
to the wrong question (bad query understanding); unanswerable (no evidence exists, and abstention
is the correct behaviour rather than a failure).

**Prevents:** a tidy answer that the interviewer can puncture with one example.

---

## 5 · Condition, not law

**Fires when:** you are about to say "X always beats Y", or someone else does.

**Procedure.** Convert the claim into a conditional and name the condition. If you cannot name
it, you do not know the claim, you know the slogan.

**Worked case.** "Hybrid retrieval always beats either leg alone."

> "It beats them **when both legs are comparably strong**. We measured equal-weight RRF losing to
> BM25 alone — because fusing a strong leg with a weak one at equal weight moves the result
> toward the weak one. RRF's scale-invariance is a virtue when legs are comparable and a
> liability when they are not, because it throws away the score distribution that would have told
> you to down-weight the weak leg. Weighted at α = 0.2 wins."

**Prevents:** being the candidate who repeats the blog post. Also gives you somewhere to go when
the interviewer says "are you sure?" — you are, and you can say why.

---

## 6 · Whose budget?

**Fires when:** you propose adding anything.

**Procedure.** Every addition spends something: latency, tokens, storage, build time, or one more
system somebody has to keep alive. Name which, unprompted, in the same breath as the proposal.

**Worked case.** "Add a cross-encoder reranker."

> "It costs about 120ms p50 on 100 candidates. On an 800ms budget that is affordable; on 300ms it
> is the whole budget. And it is a second model to version, monitor and roll back — so the real
> cost is not the latency, it is that the on-call surface just grew."

**Prevents:** the free-lunch answer. Interviewers specifically listen for whether a candidate has
ever had to maintain what they proposed.

---

## 7 · What would make this false?

**Fires when:** you state a hypothesis, or are asked to evaluate one.

**Procedure.** Say what result would falsify it, *before* running anything. A hypothesis with no
falsifier is a hope.

**Worked case.** "Contextual chunking will improve recall."

> "It should help most on chunks that are ambiguous out of context. So I would expect the gain
> concentrated on the anaphora-heavy slice and roughly nothing on self-contained chunks. If the
> gain is uniform across slices, my mechanism is wrong even if the number went up — that would
> mean something else improved and I would not know what."

**Prevents:** the post-hoc rationalisation, which interviewers detect easily because the
explanation arrives only after the direction is known.

---

## 8 · Say the shape first

**Fires when:** the question is broad and the answer is long.

**Procedure.** Open with the *count and the axis*: "two timelines", "four candidates, in order of
likelihood", "three ways this fails". Then fill them in.

**Prevents:** the interviewer losing the thread at ninety seconds, and you losing the follow-up
to the clock. It also buys you three seconds of thinking time that sounds like structure rather
than hesitation.

---

## Using these under pressure

The models are not a script. They are triggers, and the drill is recognising which one fires.

Practise like this, in order:

1. Read a question from [questions.yaml](questions.yaml) or the topic banks.
2. **Before answering, say which model fires.** Out loud. That is the whole drill.
3. Answer in ninety seconds, timed.
4. Score yourself against the band table in the topic file.

`python interview-bank/practice.py --drill models` runs exactly that loop and does not show you
the answer until you have named a model.

Most candidates who do this for a week report the same thing: the models stop being a checklist
after about forty questions and start firing on their own. That is the point at which you can
stop practising them and start practising content.

## The one that is not on the list

**Have a number from something you actually ran.** No mental model produces this; only doing the
work does.

Every claim in this bank corresponds to a cell in the notebooks where the number is computed
rather than asserted. Run it, change a parameter, watch the metric move. Then in the room you can
say *"I ran that, and here is where it stops behaving the way the formula suggests"* — and those
two sentences do not land the same way as *"I would expect"*.
