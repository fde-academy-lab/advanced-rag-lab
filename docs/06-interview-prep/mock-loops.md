# Mock loops

Four complete interview loops, timed, with the interviewer's script and the scoring sheet.
Run them with a partner. The partner does not need to know retrieval — everything they need to
probe with is written down.

Reading the questions is not preparation. The gap between candidates at this level is almost
never knowledge; it is that one of them says in twenty seconds what the other takes ninety
seconds to say, and runs out of clock before the follow-up that carries the marks.

---

## How to run one

- **Timebox strictly.** When the clock says move on, move on. Overrunning is the failure being
  simulated.
- **The partner reads only the script.** They should not improvise generosity.
- **Record it.** You will not believe how long your answers are until you hear them.
- **Score immediately**, before discussing. Then compare against the candidate's self-score;
  the gap between the two is usually the most useful output of the whole exercise.

---

## Loop A · Applied ML engineer, retrieval-heavy product team

**Shape:** 4 rounds, 45 min each. Level: mid to senior.

### A1 · Technical screen — 45 min

| Clock | Interviewer does |
|---|---|
| 0–5 | "Walk me through a retrieval system you've worked on." Listen for structure, not technology names. |
| 5–25 | **[C1](coding.md#c1--implement-bm25-scoring-over-a-small-in-memory-corpus)** — BM25 in a shared editor. Do not help unless they stall for 90+ seconds. |
| 25–35 | Follow-ups: complexity; make it work for a million documents; a query term in no document. |
| 35–45 | Their questions. |

**Score this round on:** whether they narrated before typing; whether `df` counted documents
rather than occurrences; whether they said an edge case out loud *without* handling it.

### A2 · Systems design — 45 min

Run **[S1](systems-design.md#s1--the-full-round-design-search-for-our-support-knowledge-base)**
verbatim, including the deliberate under-specification. Give three of the six requirement
answers and deflect the other three with "what would you assume?"

**The single most informative moment** is minute 0–5. If they draw before asking, note it and
let the round continue — the rest tells you how they do under a wrong premise, which is also
worth knowing.

### A3 · Evaluation deep-dive — 45 min

| Clock | Question |
|---|---|
| 0–15 | **[E1](evaluation.md#e1--design-a-metric-for-a-retrieval-system-whose-answers-can-require-two-documents)** — metric for two-document answers |
| 15–30 | **[E2](evaluation.md#e2--your-eval-set-says-089-users-are-unhappy-defend-the-number-or-abandon-it)** — 0.89 and unhappy users. Push back once: "but the metric is objective." |
| 30–40 | **[E4](evaluation.md#e4--how-do-you-know-an-improvement-is-real)** — significance. If they say "t-test", ask what it assumes. |
| 40–45 | Their questions |

**Red flag:** defends the metric in E2 rather than questioning whether it still describes
production.

### A4 · Behavioural — 45 min

**[B1](behavioural.md#b1--tell-me-about-a-time-you-were-wrong-about-something-technical)**,
**[B3](behavioural.md#b3--a-stakeholder-wants-something-you-think-is-a-bad-idea)**,
**[B4](behavioural.md#b4--tell-me-about-something-you-shipped-that-failed)**, then their
questions. Ask for a number in each. If none arrives, ask directly: *"how much did it move?"*
Whether they have it is the assessment.

### Scoring sheet — Loop A

| Signal | Seen? |
|---|---|
| Stated structure before detail ("two timelines", "four places, in order of likelihood") | ☐ |
| Asked requirements before designing | ☐ |
| Separated index-time from query-time | ☐ |
| Attached a budget — latency, tokens or cost — to something | ☐ |
| Named a failure mode of their *own* proposal, unprompted | ☐ |
| Distinguished per-piece from per-question recall | ☐ |
| Mentioned intervals, or that a mean alone is not a result | ☐ |
| Proposed a cheap diagnostic before an expensive one | ☐ |
| Brought a real number from something they ran | ☐ |
| Asked a question that revealed how the team measures | ☐ |

**8+ senior · 5–7 mid · 3–4 screen only · ≤2 no**

---

## Loop B · Forward-deployed / solutions engineer

**Shape:** 3 rounds. Weighted toward ambiguity and client pressure rather than depth.

### B1 · Scenario — 60 min

Run **[S2](systems-design.md#s2--design-an-eval-set-for-a-client-who-has-none)** for 25 minutes,
then **[S4](systems-design.md#s4--two-weeks-and-it-has-to-demo)** for 25.

Between them, apply pressure once: *"the client says they don't have time for an eval set, they
just want to see it working."* The answer that scores is not capitulation and not a lecture — it
is a version of the eval set small enough to fit the objection, plus the specific risk of not
having one, stated once and then dropped.

### B2 · Diagnosis — 45 min

Run **[S5](systems-design.md#s5--it-worked-in-the-pilot-and-is-failing-in-production)**. You are
holding a specific cause: **near-duplicates**. The production corpus has three near-identical
copies of the top policy documents from a migration.

Confirm or deny hypotheses honestly. Score on the *order* they ask in — cheapest and most likely
first — not on whether they get there. A candidate who asks "did the corpus change?" first has
already earned the round.

### B3 · Client conversation — 45 min

Role-play. You are a non-technical stakeholder who has been told the system is "88% accurate"
and wants to know why it got their question wrong.

Score on: whether they explain without condescending, whether they resist the urge to defend the
number, and whether they convert the complaint into something actionable ("can you send me five
more like it?").

---

## Loop C · Senior / staff, retrieval infrastructure

**Shape:** 5 rounds. Depth and operational judgement.

| Round | Content |
|---|---|
| C1 | **[M1](mathematics.md#m1--derive-bm25s-term-frequency-saturation-why-not-raw-tf)** and **[M4](mathematics.md#m4--why-does-a-k-nn-graph-fail-as-an-ann-index-and-what-fixes-it)** at a whiteboard, 45 min. Push for the *why* behind each formula's shape |
| C2 | **[S1](systems-design.md#s1--the-full-round-design-search-for-our-support-knowledge-base)** with all four probes, 60 min |
| C3 | **[R7](retrieval.md#r7--the-multi-tenant-question)** permissions, then scale it: 50,000 ACL groups, 45 min |
| C4 | **[E3](evaluation.md#e3--walk-me-through-validating-an-llm-judge)** judge validation, 45 min |
| C5 | **[B5](behavioural.md#b5--how-do-you-handle-being-the-only-person-who-knows-something)** and **[B2](behavioural.md#b2--tell-me-about-a-disagreement-with-a-colleague)**, 45 min |

**Staff-level differentiator to listen for:** in C3, whether they notice that a filtered graph
search can *disconnect* the graph for restricted users — so recall collapses for exactly the
users with the tightest permissions, the worst possible distribution of failure. Almost nobody
says this and it is the correct answer.

---

## Loop D · The 30-minute recruiter-adjacent technical screen

Increasingly common as a first filter, often run by someone who is technical but not a retrieval
specialist. Different failure mode: **over-answering**.

| Clock | Question | Target length |
|---|---|---|
| 0–3 | "Tell me about the project on your CV" | 90 seconds |
| 3–8 | "What is RAG, in your own words?" | 60 seconds |
| 8–15 | "How do you know if it's working?" | 2 minutes |
| 15–22 | "What was the hardest problem?" | 2 minutes |
| 22–30 | Their questions | — |

Every one of those has a five-minute answer you want to give. Giving it is the failure. Practise
the 90-second version of your project until it is automatic:

> "It's a retrieval and evaluation system — the whole stack, BM25 through reranking, but the
> point of it is the measurement rather than the retrieval. Everything runs in memory with no
> API keys, so anyone can reproduce a number in about ten seconds.
>
> The interesting part is that four results came out against the received wisdom. The one I'd
> most want to talk about is that no retrieval configuration we tried moves answer correctness —
> evidence recall moves nine percent relative and the answers don't move at all, so the system
> was generation-limited the whole time and the retrieval work was measuring itself. The
> mechanism generalises even though the specific number doesn't."

That last sentence is doing the work: it hands the interviewer the thread to pull.

**If you have the nerve, there is a better version of this answer**, and it is the one that
separates a senior candidate from a strong mid one:

> "One of those four findings was wrong. We published *'equal-weight RRF loses to BM25 alone'*
> and it doesn't reproduce — RRF wins, and the leg we called weak was the strong one. It stood
> for months and it was quoted in about twenty places. What let it survive is that the eval gate
> compares one configuration against its own history and never against alternatives, so nothing
> in the system was structurally capable of noticing. The fix was a one-command comparison and a
> retraction ADR."

Volunteering a mistake unprompted is a risk and it is usually the right one, because the
interviewer is already trying to find out whether you can. What makes it land is that the story
ends on the **structural** reason rather than on the mistake — you are describing a gap in a
system, not confessing.

---

## After the loop

Score, then answer three questions in writing:

1. **Which answer ran long?** Time it. Cut a third.
2. **Where did you say "it depends" without naming what it depends on?** That is a filler phrase
   until you complete it, and interviewers hear it as one.
3. **Where could you have used a number and didn't?** Go find that number in the notebooks. Run
   the cell. Then you have it for next time, and *"I ran that"* does not sound like
   *"I'd expect that"*.
