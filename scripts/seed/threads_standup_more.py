"""Weekly Standup & Retro, weeks 4 to 7 — P3 Context through P6 Agentic.

A standup that lists progress is a status report and nobody reads the second one. These four are
shaped around the third heading instead: **what we got wrong this week**. Two of them carry
corrections this repository actually published — the fusion finding (ADR-0015) and the multi-hop
independence claim — because a cohort that only ever sees a project's wins learns that projects
do not have retractions, which is the least useful thing we could teach them.

Each week carries the same four loads: what moved with a number, what is blocked with a name and
a date, what we were wrong about, and one decision with the observation that would overturn it.
A decision with no falsifier is a preference, and it is not worth the heading.

Every figure quoted is one the harness produces or one an opened repository file states. The
announcement format has no accepted answer, so no reply is marked.
"""
from __future__ import annotations

CAT = "Weekly Standup & Retro"

THREADS = [
{
 "category": CAT, "author": "maintainer",
 "title": "Week 4 · P3 Context — the exit criterion that was only measuring k",
 "body": """### Moved

- **Packing with provenance landed.** Every packed block carries a marker that resolves to a
  `chunk_id`, not a `doc_id`. That distinction failed review twice and is the whole of R1.
- **Frozen slice closed.** [ADR-0009](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0009-frozen-slice-lifecycle.md)
  takes option C: keep the old slice, start a new one, report both for a phase. Tomás's argument
  from the week 3 thread decided it, in a stronger form than he posted it — the corpus itself is
  downstream of the old slice, so blinding whoever re-samples does not save option B.
- **`context_precision` is on the scorecard.** 0.2433 at k=8, n=243.
- **Reranker features.** Priya's MaxSim run is in review. No number yet; the interval is not
  tight enough to report and I would rather it stayed off this table than went on it soft.

### Blocked

- **Human labels for the answerable slice.** Aarav owns it, by Thursday. The 36 nulls are done.
- **Corpus growth for P4.** Needs the ADR-0009 transition rule wired into `run_eval.py` so a
  claim has to clear both slices before it counts. Sofia owns it, by Friday.

### Wrong about

We wrote the P3 exit criterion as *"context_precision above 0.30"*.

Priya's table in the Q&A thread *context_precision is 0.2433 — is three quarters of my context
window wasted?* already plots what that means: across k on BM25 alone, precision falls as recall
rises, monotonically, because the denominator is k and the gold set for a question is fixed. At
k=5 it clears 0.30; at k=8 it does not.

What that thread does not say, and what we got wrong here, is that **the criterion is therefore
clearable by a config flag.** Set `k=5`, hand back evidence recall from 0.7118 to 0.6329, and the
exit gate goes green on a system that got worse. We wrote a target no packing change can move and
one flag can.

Cost of being wrong: a week of packing work aimed at a number that was never about packing.

### Decision taken

`context_precision` is reported only as a triple with k and `evidence_recall`, never gated on its
own.

**Falsifier.** At fixed k=8, if `context_precision` moves outside the paired-bootstrap band while
`evidence_recall` stays inside it, then packing has changed something real and precision becomes
gateable by itself. Until somebody shows me that pair of intervals, the metric is a restatement
of k.""",
 "replies": [
  {"by": "lena", "body": """The fix for this is in the contextual retrieval work — prepending a
short generated context string to each chunk before indexing took failed retrieval from 5.7% to
1.9%, at about $1.02 per million document tokens. That is cheap and it is exactly the "the chunk
does not carry enough of its own situation" problem you are describing.

I would put it in front of the packing work rather than behind it. If the chunks arrive better
situated, the packer has less to do and the precision question gets easier."""},
  {"by": "marcus", "body": """It would help, and it is not aimed at this. That 5.7% to 1.9% is a
retrieval failure rate — a recall-direction number on a different corpus with a different
question mix. `context_precision` here has a ceiling set by arithmetic before anyone touches the
chunks.

Gold evidence pieces per answerable question on this corpus:

```
1 piece   21 questions      4 pieces  100 questions
2 pieces  59 questions      6 pieces    6 questions
3 pieces  21 questions      ----------------------
                            638 pieces over 207 questions
```

A question with 4 gold pieces has a precision ceiling of 4/8 at k=8. One with a single piece has
a ceiling of 1/8. Across that distribution the ceiling is `638 / 207 / 8`, which is under
0.39, and we measure 0.2433 against it. Contextual prefixes move which chunks come back. They do not move the
size of the gold set or the size of k, and those two are what the metric is made of."""},
  {"by": "wei", "body": """We dropped context precision from the dashboard entirely at my last
place and gated on `tokens_in` instead. Same information for a tenth of the argument, and it is
the number finance asks about anyway.

The reasoning was that precision at k is a research metric that does not survive contact with a
review where somebody has to decide something. Nobody in that room could tell you what a move in
the second decimal place of `context_precision` would mean for a user, so it got quoted, nodded
at and ignored. A token count maps onto a bill and a latency budget, and people argue about those
properly.

I would say the same here. You have just spent a week discovering the metric is mostly k. The
next thing that happens is somebody proposes a target of 0.30 again with a different justification
and you spend another week on it."""},
  {"by": "tomas", "body": """`tokens_in` and `context_precision` are not the same information the
moment your packer starts truncating. A cap on tokens can be met by cutting the last block, and
the last block is the one the reranker liked least, which is usually fine and occasionally is the
gold piece. You would not see that in `tokens_in`.

Keep both. The one I would page on is neither: it is packed blocks whose marker fails to
resolve, because that is the failure a user notices at 3am and it is the only one on this list
that is unambiguously a defect rather than a tradeoff."""},
  {"by": "priya", "body": """I have been tuning chunk overlap for a week to move this number, so
Marcus's arithmetic is the most annoying thing I have read this month.

What actually surprised me: I went back through my own notebook and every overlap setting that
moved `context_precision` moved it by changing how many chunks survived dedup, which changes the
effective k. I was tuning k with extra steps and I could not see it because the flag I was
turning was called `overlap`.

Filing the general version somewhere: **if a knob moves a metric through a path you cannot name,
you are probably turning a different knob.**"""},
  {"by": "maintainer", "body": """That is the retro note for the phase and Priya has written it
better than I was going to.

The rule I want out of this one is about criteria rather than metrics. **A criterion is only a
criterion if the work you are about to do can move it.** Ours could not, and we did not notice
because it was written by the same people who then went off to do the packing, in a week when
nobody had yet plotted precision against k.

Lena, the contextual prefix idea is worth its own Design Review thread. It is a real technique
and my objection is only to the sequencing: it is aimed at recall, we have a precision criterion
that is not about the packer, and putting them in the same conversation buries the second
problem under a plausible answer to the first.

Next week is P4 and the judge. Aarav, Thursday.""",
  },
 ],
},
{
 "category": CAT, "author": "maintainer",
 "title": "Week 5 · P4 Evaluation — a metric read 0.0 for three weeks and all of us filed it as 'not built yet'",
 "body": """### Moved

- **The null slice is wired in.** 36 of the 243 questions are unanswerable by construction, and
  the scorecard now reports abstention separately from correctness instead of folding both into
  `answer_correct`.
- **Both frozen slices report.** The ADR-0009 transition rule is live: a claim clears both or it
  is unproven, not "the old slice is stale".
- **Per-type breakdown published.** comparison 46 · inference 95 · temporal 66 · null 36.

### Blocked

- **Human labels for the answerable slice.** Aarav, still, now by Monday. This is the second
  week and it is the only thing between us and a calibrated judge.
- **The temporal slice.** `evidence_recall` 0.769 and `answer_correct` 0.091 on n=66. Retrieval
  finds the evidence and the answer is wrong nine times in ten. Nobody owns the diagnosis.
  Marcus wants a design first; what I need by Monday is one page of scope, not the design.

### Wrong about

`abstention_recall 0.0` and `abstention_f1 0.0` have been sitting on the scorecard for three
weeks. Every one of us read them as *not implemented yet*.

They were implemented. The two columns beside them say what they meant:

| | |
|---|---|
| `abstention_recall` | 0.0 |
| `abstention_f1` | 0.0 |
| `false_answers_on_null` | **36** |
| `over_refusals` | 0 |
| `answer_correct`, null slice | 0.000 |

The system answers all 36 unanswerable questions, confidently, every time, and has never once
declined. A working metric was reporting the worst result available to it and we read the worst
result as an empty field.

### Decision taken

The gate uses `false_answers_on_null` as a raw count. `abstention_f1` stays on the scorecard and
gates nothing. Separately: no metric ships to the scorecard unless a not-yet-implemented version
of it reports `n/a`, so that zero can only ever mean zero.

**Falsifier.** If a change drops false answers below 36 while `over_refusals` stays at 0 and
`answer_correct` over the 207 answerable questions stays inside the paired-bootstrap band, the
abstention is real and the count is the right gate. If `over_refusals` climbs alongside it, we
have bought abstention with refusals and the gate should reject that change.""",
 "replies": [
  {"by": "dan", "body": """Asking the thing I assume everyone else already worked out. How do you
get `abstention_f1` of 0.0 and `over_refusals` of 0 at the same time?

I read f1 of zero as "this classifier is broken in both directions", and zero over-refusals reads
to me like the opposite, as though it is being careful and never refusing when it should not.
Those two feel like they cannot both be describing the same run.

Is that a bug in how f1 is computed for this slice, or is it just what f1 does when one side of
the matrix is empty and I should be reading the count of 36 instead? I would rather ask than
quietly assume the metric is wrong, because I nearly filed an issue about it last week."""},
  {"by": "wei", "body": """Not a contradiction. It never abstains, so it never abstains wrongly —
recall is 0, precision is undefined and reported as 0, over-refusals are 0 because there are no
refusals of any kind.

And the fix is prompting. Add "if the context does not contain the answer, say you do not know"
to the instruction block and this goes to near-perfect. We did exactly that at my last place and
the null slice stopped being a problem in an afternoon."""},
  {"by": "dan", "body": """That clears it up, thanks. So f1 of 0.0 describes one side of the confusion matrix being empty, rather than a classifier
broken in both directions, and the number I
should have been reading all along was the count of 36.

I will take the prompt change then. It sounds like an afternoon and it is the sort of thing I can
do without blocking anyone. Will post the before and after on the null slice, and I will report
`over_refusals` on the answerable set beside it rather than only the bit that got better."""},
  {"by": "marcus", "body": """Hold on, Dan. Wei's answer to your first question is right and his
answer to the second one is a folk rule that this corpus is specifically positioned to break.

An instruction to abstain when the context lacks the answer only works if the generator is
reading the context and reasoning about what is in it. Look at the temporal slice: 0.769 evidence
recall, 0.091 answer correct, n=66. On a whole class of question the evidence is in the packed
context and the answer is wrong anyway. That is a generator not using what it was given, and the
proposed fix is an instruction whose execution depends on the generator using what it was given.

Wei's fix is the right one when abstention fails because **nobody asked for it**. Try it, by all
means, it is an afternoon. But the result to watch is `over_refusals` on the 207 answerable, rather than the null slice going
green, because the cheap way for a model to satisfy that
instruction is to decline more often everywhere."""},
  {"by": "sofia", "body": """The version of this that worries me is downstream of the ACL
prefilter. A system that never abstains does not abstain when the filter has removed every
document the user was allowed to see either. Same input to the generator — an empty or
irrelevant context — and the same behaviour, which is to answer anyway.

That failure has a different blast radius from a wrong answer on a synthetic null. It looks like
a permissions leak in the incident review even when nothing leaked, because the answer was
plausible and the user was not cleared for the subject.

Can the null slice carry a few questions whose evidence exists but is filtered out for the
persona asking? Same measurement, and it exercises the path that actually pages someone."""},
  {"by": "dan", "body": """Went and read the abstention code after Marcus's reply rather than
before it, which is the lesson.

There is a test. It passes. What it asserts is that the metric **scores hand-made rows
correctly** — `test_abstention_scores_reward_refusing_only_the_nulls` feeds three rows, abstains
on one null, and checks precision 1.0, recall 0.5, one false answer. All true, all about the
arithmetic. Nothing in it ever runs the pipeline, so it passes identically against a system that
abstains perfectly and one that never abstains at all.

Which is the shape R1 in the simulator taught me to look for, except R1 *has* the check —
`every marker resolves to a real chunk_id, over random inputs`, ten on the rendering and one on
the promise, and only the last one failed. Here there is no last one."""},
  {"by": "maintainer", "body": """Sofia's suggestion is in as an issue for P7, tied to ADR-0011.
It is the right instinct and I want to be careful about the framing: filtered-to-empty and
unanswerable-by-construction produce the same context and want the same behaviour, so measuring
them together is fine. They want different *messages* to the user, and that is a product
decision we have not made.

Retro note. Both of this week's mistakes are the same mistake at different layers. A metric
reporting 0.0 could not be told apart from a metric nobody had written, and a test asserting a
float came back could not be told apart from a test asserting the feature works. In both cases
the artefact was present, passing, and carrying no information.

**Rule for the phase: a check that has never failed and a value that has never been anything
else are both indistinguishable from absence.** If you cannot say what would make it change, it
is decoration.""",
  },
 ],
},
{
 "category": CAT, "author": "maintainer",
 "title": "Week 6 · P5 Cost — the cache win, and a finding we have to retract",
 "body": """### Moved

- **Cost split into four token categories** — input, output, cache-write and cache-read,
  tracked separately rather than summed, which is the point of
  [`raglab/costs.py`](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/costs.py). At the
  committed default: `tokens_in` 884.05 (p95 1123), `tokens_out` 82.21, `cost_usd` 0.0039
  (p95 0.0046), `latency_ms` 34.62.
- **Prompt block ordering shipped**
  ([ADR-0012](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0012-prompt-block-ordering.md)).
  Over 200 simulator requests the assembler as given hits 0.2612 and bills 154.04 tokens at the
  full input rate; ordered by volatility, **0.8176 and 38.07**. In production: hit rate 4% to
  71%, cost per query down 58%, cause a timestamp at byte 58.
- **Two near-misses.** Deleting that timestamp rather than moving it gives 0.7942 / 42.16 and
  loses the "as of" feature; reordering the stable blocks too gives 0.6969 / 63.23.

### Blocked

- **The α re-baseline** (EX-16). Blocked on sequencing, not a person: I will not move a default
  in the same commit as a correction. Mine, end of next week.
- **ANN recall against the cost budget.** Tomás, Wednesday.

### Wrong about

The fusion finding. The week 3 standup says *"Weighted at α=0.2 beats equal-weight RRF and beats
BM25 alone: evidence recall 0.7645 → 0.7891, [+0.008, +0.041]."* Re-measured with `run_eval.py
--compare`, paired bootstrap:

| | claimed | measured |
|---|---|---|
| equal-weight RRF vs BM25 alone | RRF loses | RRF **wins**, +0.0624 evidence recall, ci (+0.0407, +0.0857) |
| the dense (LSA) leg | weaker | **stronger**, +0.0616 over BM25 |
| weighted α=0.2 | wins | ties RRF on evidence recall (+0.0008, ci −0.0101 to +0.0109); **loses** nDCG (−0.0535, ci −0.0776 to −0.0295); α=0.5 is better |

Mechanism, and it is not carelessness. **The gate compares a configuration against its own past
self, never against alternatives**, so CI could not catch a wrong ranking between arms. Likely
origin is a label slip: 0.7645 is the tuned configuration and appears somewhere attributed to
"BM25 alone", whose real number is 0.7118.

What replaces it teaches more. Evidence recall spans 0.7118 to 0.7790 across arms while every
pair on `answer_correct` stays inside the noise band, and the best `answer_correct`, 0.4156,
comes from the worst retriever. The system is generation-limited.

### Decision taken

`--compare` runs in CI. α=0.2 stays the default even though α=0.5 measures better on evidence
recall and nDCG, because the baseline is cut from it.

**Falsifier.** If a re-baselined α=0.5 moves `answer_correct` outside the paired-bootstrap band,
we move the default. If it moves only `evidence_recall` and nDCG, we do not, because by the
finding above those do not reach the user.""",
 "replies": [
  {"by": "dan", "body": """So the honest version is that fusion buys nothing and we should drop
the second index. BM25 alone has the best `answer_correct` on the whole table at 0.4156, it is
one index instead of two, it is the cheapest thing to run, and by the third finding the retrieval
numbers are not reaching the user anyway.

That looks like where the table points, and it makes P2 much smaller: no dense build, no fusion
rule, no α to tune and no per-corpus retune when the corpus grows. If the correction is that we
over-believed a fusion result, the consistent move is to stop paying for fusion rather than to
pay for it under a different rule. Am I missing something, or is the retraction bigger than the
ADR is willing to say?"""},
  {"by": "priya", "body": """No, and this is the trap the retraction sets for anyone reading it
quickly, so it is worth being exact.

BM25 alone is the **weak** leg here. Dropping the dense leg costs 0.0616 evidence recall with an
interval clear of zero. What buys nothing measurable is the *fusion step on top of a dense leg
that already works*: `dense → rrf` is +0.0008 with an interval straddling zero, and the unfused
dense leg wins nDCG outright. If you want to remove a moving part, remove the fusion rule and the
α tuning. Keep dense.

On 0.4156: the default is 0.4115, and the ADR says every pair on `answer_correct` sits inside
the noise band. Choosing a retriever on the gap between those two is choosing on noise, in the
same week we retracted a finding for doing exactly that."""},
  {"by": "wei", "body": """Keep BM25 either way. In production BM25 always wins on
identifier-shaped queries: error codes, ticket numbers, function names, table names. No dense
encoder I have shipped has handled those, because there is nothing semantic about `ERR_4471` and
the encoder has no reason to place it anywhere useful.

Losing on average is not the same as losing everywhere, and the average is the wrong statistic
when one slice is the one users are angriest about. Every support-facing system I have worked on
had a small identifier slice with wildly outsized complaint volume attached to it. I would keep
the lexical leg in the pipeline on that basis alone, whatever the corpus-level table says about
who is stronger."""},
  {"by": "marcus", "body": """That one holds and the ADR already says so: BM25's win is confined
to the exact identifier slice, and it calls it real and small. It is also why the FTS5 tokenizer
fix in week 3 mattered — identifier-slice recall went 0.34 to 0.81 on that change alone.

The generalisation I would not make is the reverse one. "BM25 always wins on identifiers"
predicts a slice-level win, not a corpus-level one, and this corpus is paraphrase and inference
over prose, so term overlap has very little to score on the rest of it.

The audit worries me more than the finding. My instinct is to design a full provenance scheme
for every number in the docs before we quote another one, and to hold the ADR until that lands.
I recognise that instinct and I know where it goes."""},
  {"by": "aarav", "body": """Do not hold the ADR. Some of the cohort quoted this in interviews
last month and every day it stands uncorrected is a day somebody says it out loud again.

The client-facing framing, for what it is worth, is the strongest thing we have: "we published a
result, built a mechanism story on it, re-ran it and it inverted, and here is the one-line
command that would have caught it." Nobody gets asked in an interview whether they have ever
been wrong and has a good answer. This is a good answer."""},
  {"by": "maintainer", "body": """Publishing this week. Marcus, the scheme you want is two things
and only one of them is a design problem — `--compare` is already the re-run path, so what is
left is which documents quote which figures, and that is a grep and a test, not a scheme. Take
the grep.

The cost, stated plainly, because I would rather it were in the standup than only in the ADR.
The claim reached the README, the CHANGELOG, the retrieval LLD, four interview-prep banks, the
session-02 script, the exercise rubrics, notebook 04, the Pages site and these standups. Every
one of those is corrected. Copies people already have are not recallable, and some of you learned
a wrong result from us and used it.

**The rule: a finding nobody can re-derive in one command is a rumour with a decimal point on
it.** The gate we had was doing its job, which was never this job — a configuration against its
own history is a regression check, and ranking alternatives is a different question that nothing
was asking. The audit is still open and I would be surprised if this is the only one.""",
  },
 ],
},
{
 "category": CAT, "author": "maintainer",
 "title": "Week 7 · P6 Agentic — the audit found the second one, and it is the number that scoped this phase",
 "body": """### Moved

- **The agent loop has stop conditions that stop**, and traces are scored on evidence retention
  rather than the final answer alone.
- **The k sweep is published.** With the cross-encoder, RRF evidence recall is 0.5048 at k=3,
  0.7742 at k=8 and 0.8700 at k=20. Without the reranker: 0.4517 at k=3 and 0.8659 at k=20. The
  reranker is worth about five points at k=3 and almost nothing at k=20, so its value sits where
  the list is short.
- **`scripts/independence.py` exists**, and `tests/test_measurements.py` recomputes the
  gold-piece distribution from the corpus, failing if the docs drift.

### Blocked

- **A cost ceiling for the loop.** Nobody has set one and I will not merge an agent without one.
  Aarav, Friday.
- **Trace scoring rubric.** Lena, Thursday.

### Wrong about

The multi-hop independence claim, which is the number this entire phase was scoped on. Until
2026-09-01 this repository said:

> The 207 answerable questions split 128 single-hop, 61 two-hop, 18 three-or-more. At p = 0.7645
> that predicts 0.6838. We measure 0.4686 — 21 points below independence, so the pieces are not
> independently retrievable and they fail together.

Wrong three times over, and each error is a different kind.

**The mixture is not real.** Gold pieces per answerable question are `{1: 21, 2: 59, 3: 21,
4: 100, 6: 6}`; `hops` reports 77 and 130. Neither is 128/61/18.

**The exponent was wrong.** `full_chain_recall` needs every gold *piece*, so the exponent is
`len(gold_map)`, not `hops`. A two-hop question routinely carries four pieces.

**The conclusion inverts.** Corrected, the prediction at the macro rate is 0.4603 and we measure
0.4686, **+0.0083 above** it. At the micro rate of 0.7257 the prediction is 0.4007, and measured
is +0.0679 above. No shortfall, so no correlated-failure structure to find. The 0.7645 → 0.4686
gap is the arithmetic of a distribution where half the answerable questions need four or more
pieces.

Both corrections are dated 2026-09-01: we published
[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
and the
[measurement note](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/multi-hop-independence.md)
together, so a reader who finds one finds the other.

### Decision taken

The loop's bar is the **single-shot k=20 arm at 0.8700**, at matched cost per query. Not the k=8
default, which it beats by fetching more.

**Falsifier.** If a two-step loop at matched cost does not clear 0.8700 by more than the
paired-bootstrap band, we stop, ship k=20 as a config change, and close P6 as not worth the
machinery.""",
 "replies": [
  {"by": "lena", "body": """Before we conclude there is nothing here, the LinkedIn KG-RAG work is
directly on this: SIGIR 2024, arXiv:2404.17723, MRR up 77.6% and median resolution time down
28.6% by putting a graph between the question and the passages. That is a very large effect for
a multi-hop customer-support setting and it is the closest published system to what we are
scoping.

If graph-structured multi-hop retrieval buys that much there, I would want a much stronger
argument than one measurement before we drop the phase."""},
  {"by": "marcus", "body": """Their result holds and it is measuring something we are not.

Their gain is MRR — where the first relevant thing lands — on a corpus of support tickets that
have real structure to build a graph out of: a ticket links to a resolution, a resolution links
to an article. Our metric is `full_chain_recall`, which is all-or-nothing over every gold piece,
and our finding is about whether those pieces fail *together*.

The condition under which your paper transfers is worth stating because it is testable. A graph
helps when a question's evidence clusters and the retriever's failures cluster the same way, so
finding one piece pulls in the next. This corpus spreads a question's evidence across documents
by construction, which is very likely why the independence check comes out where it does. Build
the graph on a corpus where evidence clusters by document and I would expect something closer to
their number."""},
  {"by": "dan", "body": """The question I cannot get past is where 128/61/18 came from. Not who
wrote it. How do three numbers that no command produces sit in a document for weeks with a
prediction computed off them and a roadmap hanging off the prediction?

I ask because I have written that kind of line myself, more than once. You carry a mixture in
your head from the last dataset, the arithmetic works out, the conclusion is interesting enough
that people repeat it back to you, and nobody re-derives it because it already looks derived. The
decimal places are what sell it. `0.6838` reads as measured in a way that "about two thirds"
never would, and I do not think that is an accident of style."""},
  {"by": "maintainer", "body": """That is the whole answer, Dan, and the observation about
decimal places is the part I want people to keep. There was no command. The number looked derived
because it *was* derived, correctly, from inputs nobody had checked against the corpus.
Arithmetic on a wrong premise is still arithmetic and it reads exactly like rigour.

`0.6838` also had the property of being interesting. A 21-point shortfall justifies a phase of
work; a result at independence justifies nothing and closes a line of enquiry. We were not
neutral about which one we were looking at, and I do not think anyone consciously bent it.

That is why `independence.py` exists and why `test_measurements.py` recomputes the distribution
from the corpus rather than asserting the literals in the document."""},
  {"by": "aarav", "body": """Then k=20 closes this phase today, surely. It is a config change,
0.8700 against 0.7742, and we now have a measurement saying the premise the phase was scoped on
was not real. Ship the flag, write P6 up as a negative result and move to P7, where the ACL work
is the thing every client I talk to asks about first.

"We tried an agent loop, measured it against a one-line config change, and the config change won"
is a genuinely good story to tell and it costs us a week instead of a quarter. The alternative is
that we spend the quarter proving something we already have a strong prior against, and end up
telling the same story with a much larger invoice attached to it."""},
  {"by": "tomas", "body": """k=20 is not free and "config change" is doing a lot of work in that
sentence. Going from 8 to 20 packed blocks moves `tokens_in` — it is 884.05 with a p95 of 1123
at k=8 today — and that lands on the cost ceiling nobody has set yet, which is the item at the
top of the blocked list.

Separately, and this is the one that pages someone: "stop conditions that stop" is a claim, not a
property. What is the behaviour when a step returns nothing, twice? My instinct is to keep the
loop behind a flag that defaults off until we have watched it fail on purpose. I know that is my
usual instinct and I know it is usually wrong, and I would still hold this one, because an agent
that does not terminate fails differently from a retriever that returns a bad list: one is a
worse answer and the other is a bill."""},
  {"by": "maintainer", "body": """Aarav, not today. Tomás's first point is the reason: k=20 has a
token cost we have not budgeted, so it is a tradeoff to be measured against the ceiling rather
than a free win, and the ceiling is Friday.

Retro for the phase, and it is the same note as last week with a second data point behind it.
Both retractions survived for one structural reason: **a number nobody could re-derive in one
command.** The fusion claim had no `--compare`. The independence claim had no `independence.py`.
Neither error required anyone to be careless, and neither would have survived a week if the
re-run had been one line.

The falsifier for that rule, since I am asking everyone else for theirs. If
`tests/test_measurements.py` goes a full phase without ever failing, it is not protecting
anything and I want to know whether that is because the docs stopped drifting or because the
test only checks figures nobody edits.""",
  },
 ],
},
]
