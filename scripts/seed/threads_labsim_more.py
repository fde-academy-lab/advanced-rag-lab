"""Four more L.A.B. Simulator solves, worked in public: F1, E1, C1 and R3.

`threads_labsim.py` seeds the index and the first two solves, R1 and R2. These are four of the
five units that had no worked thread — P1 is still uncovered — and they are shaped the same way
on purpose: somebody posts an attempt that is
wrong the way a competent person is wrong, the grading Action's reply is quoted verbatim, a peer
gives the confident textbook answer, somebody else brings the evidence that kills it, and the
resolution names the mechanism rather than the outcome.

Two of them exist for a reason no other thread in this repository covers.

C1 is the two-bar unit. Its interesting submission passes all fourteen named checks and fails on
the numbers, which is the only shape of failure that argues for having bars at all. The thread
also carries a real defect found while writing it: C1's brief header quotes bars that are looser
than the ones `unit.yaml` enforces, and at the looser pair the unit's own decoy would pass.

R3 is where the fusion argument that runs through R2, ADR-0003, ADR-0007 and ADR-0015 finally gets a
number instead of an opinion. 0.9684 of the questions the dense leg misses are missed by BM25 as
well, so the thing R2 spent a month weighting was never going to change the outcome.

Every figure here was produced by running the repository's own grader. The bot replies are
transcripts of `labsim.discussion.render_grade`, not paraphrases.
"""
from __future__ import annotations

CAT = "LAB Simulator"

THREADS = [
{
 "category": CAT, "author": "priya",
 "title": "F1 · my chunker tiles perfectly and drops the end of every document",
 "body": """**Approach.** Split on whitespace, slide a window of `size_tokens`, step by
`size_tokens - overlap_tokens`, raise if the overlap is at least the size because that window
would never advance. I spent the first half hour sweeping the window size and the overlap
against each other before writing the loop, on the theory that those two numbers are what the
unit is about.

**Your solution.py**

```python
def chunk(text: str, size_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    if overlap_tokens >= size_tokens:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    stride = size_tokens - overlap_tokens
    return [" ".join(words[i:i + size_tokens])
            for i in range(0, max(len(words) - size_tokens, 1), stride)]
```

**What surprised me.** Five checks pass, four fail, and I cannot see the four. The chunks are
even, none of them is over the cap, consecutive ones share words, the config error raises. If I
print the output for a short document it looks exactly like the diagram in the brief.

The failure that I understand least is `overlap of zero is allowed and tiles the document`,
because with an overlap of zero there is nothing left in my function that could be wrong. It is
a slice and a stride.""",
 "replies": [
  {"by": "labsim-bot", "body": """🔴 `F1` · Chunk so the answer survives the cut — **not yet**

`implement` · easy · foundations · graded in 0.0s on a clean checkout

- ❌ **checks**

**Checks that failed**

- `every word survives, in order`
- `the last word of the document is in the last chunk`
- `every short span survives whole`
- `overlap of zero is allowed and tiles the document`

```
  pass  returns a list of strings
  pass  no chunk exceeds size_tokens
  FAIL  every word survives, in order — 300 words in, 320 out - check the tail
  FAIL  the last word of the document is in the last chunk — document ends
        'tessera-analytics', last chunk ends 'ap-southeast-2'
  pass  consecutive chunks overlap
  FAIL  every short span survives whole — the 16-word span starting at word 241
        (shard-rebalance p99 latency acquisition ...) is not wholly inside any chunk
  pass  a document shorter than one window yields one chunk
  FAIL  overlap of zero is allowed and tiles the document — total words out: 96
  pass  overlap >= size raises ValueError
```"""},
  {"by": "wei", "body": """Your overlap is too tight. Sixteen words against a sixty-four word
window is a quarter of a window, and a quarter is not enough to hold a sentence pair — that is
what `every short span survives whole` is telling you.

We landed on a quarter of the window as a house default after about six months of this and
never touched it again. Push the overlap up to 128 with a 512 window and that check goes green,
and the tail ones will follow because bigger overlap means more windows means the last one lands
closer to the end.

The sweep you did at the start was the right instinct. It was just centred on numbers that are
too small."""},
  {"by": "marcus", "body": """The overlap cannot be the cause, and the bot has already handed
you the proof.

Look at the check you said you understood least. `overlap of zero is allowed and tiles the
document` runs at `size_tokens=32, overlap_tokens=0` and reports **total words out: 96** on a
120-word document. There is no overlap in that call at all, so nothing about the overlap value
explains 24 missing words.

Now the other one. **300 words in, 320 out**, with a 64-word window and 16 words of overlap.
320 is more than 300, so at a glance it looks fine — which is what makes it worth checking.
Covering 300 words at a stride of 48 takes six windows and emits 380; the reference chunker does
exactly that. You emitted five. The overlap duplicates are hiding a missing tail, which is why
320 does not look wrong.

And the span failure starts at **word 241**, which is not a random place. Wei, raising the
overlap moves that number around and never gets it to disappear, because the span that fails is
the one that runs off the end of the last window Priya emits. There is no window after it."""},
  {"by": "maintainer", "body": """Marcus has it. The mechanism is one expression:

```python
range(0, max(len(words) - size_tokens, 1), stride)
```

That bound asks *"is there a whole window left?"*. The property you owe is *"has the last window
reached the end?"*. `range` stops strictly below `len - size`, so the last start always falls
short of it and the last window always ends before the document does — for **every** document
longer than one window, at every stride and every length. The two questions agree only when the
whole document fits inside one window, which is the one green tail check you have (`a document
shorter than one window yields one chunk`) and every example anyone writes by hand. Stop when `start + size_tokens >= len(words)` **after**
emitting the window, rather than before.

Wei's answer would have been the right one under a condition that is worth stating, because it
is the actual F1 lesson. If the tail checks were green and the *only* failure were `every short
span survives whole`, then yes, the overlap is smaller than the longest span you need to keep
intact, and the fix is to raise it. But not to a fixed fraction of anything — and note that the
quarter Wei recommends is the same quarter he has just rejected. Overlap is a length
budget: it guarantees that any span of at most `overlap_tokens` words sits whole inside some
window, and nothing else. The brief gets 64 from measuring the thing — an incident's cause and
effect sentence pair runs to about 60 tokens on Client Zero. A percentage of the window size is
a number about the window. The question is about the answer.

The trap table in the
[brief](/fde-academy-lab/advanced-rag-lab/blob/main/lab-simulator/units/F1-chunk-boundaries/BRIEF.md)
has this as row two, and it is there because it is the row that gets shipped.""",
   "accepted": True},
  {"by": "priya", "body": """Fixed with a `while` loop that emits the window first and breaks
when that window already reaches the end. Green, and it took four lines.

The part I want on the record is the half hour at the start. I swept size against overlap before
I had a chunker that covered the document, and a sweep like that produces a smooth curve whatever
you feed it. Every point on my curve was computed on an index that was missing the last stretch
of every document, and no point on it looks wrong. I would have picked a winner and moved on.

Optimising before measuring is a habit I know I have. What I had not seen before is that the
sweep does not just fail to catch this class of bug — it actively hides it, because it hands you
a plausible-looking answer to a different question."""},
  {"by": "tomas", "body": """The production version of this is worth naming for whoever reads
the thread next, because it does not arrive as a chunking bug.

It arrives as *"questions about how an incident was resolved do badly"*, six weeks in, from
someone who is not on your team. Postmortems put the resolution at the end. If the tail of every
document is missing from the index, that whole class of question is unanswerable and every other
question is fine, so the shape of the complaint points at the retriever, the reranker or the
prompt — three places you can spend a month before you look at the splitter.

There is no error, no alert and nothing to page on. `every word survives, in order` is the check
I want in my own pipeline, and it costs nothing to run at index time."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "E1 · my nDCG is 1.0 and I do not believe it",
 "body": """**Approach.** Both recalls came out easily once I read the hint about `&` rather than
`in` — a piece of evidence is satisfied by any chunk in its set. For nDCG I walked the retrieved
list in rank order, credited each gold piece once, and normalised.

**Your solution.py** (the nDCG only, the rest is green)

```python
def ndcg_at_k(retrieved_ids, gold_map, k=10):
    if not gold_map:
        return None
    items = list(gold_map.values())
    dcg, seen = 0.0, set()
    for i, cid in enumerate(retrieved_ids[:k], 1):
        for j, cids in enumerate(items):
            if j not in seen and cid in cids:
                dcg += 1.0 / math.log2(i + 1)
                seen.add(j)
                break
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, len(seen) + 1))
    return dcg / ideal if ideal else None
```

**What surprised me.** Two failures, both on nDCG, and one of them says my answer is 1.0 where
it should be 0.4693. I checked by hand and my function does return 1.0 there, so this is not a
typo — I have written something that is confidently wrong.

What bothers me is that I cannot construct the input where I would have noticed. Every case I
tried by hand gave me a number that looked sensible.""",
 "replies": [
  {"by": "labsim-bot", "body": """🔴 `E1` · Build the two recalls that disagree by thirty points
— **not yet**

`implement` · medium · evaluation · graded in 0.0s on a clean checkout

- ❌ **checks**

**Checks that failed**

- `nDCG is normalised against the ideal ranking`
- `nDCG credits a gold piece once`

```
  pass  no gold evidence returns None, not zero
  pass  a piece of evidence is satisfied by any one of its chunks
  pass  full-chain recall is all or nothing
  pass  nDCG is 1.0 for a perfect ranking
  pass  nDCG penalises rank, not just presence
  FAIL  nDCG is normalised against the ideal ranking — one of three pieces at rank 1 is
        0.4693, not 1.0. Normalising against what was found gives a metric that cannot go
        down
  FAIL  nDCG credits a gold piece once — c1, c2 and c3 all satisfy hop_a. Three
        near-duplicates of one hop must not score like two different hops
  pass  nDCG caps the ideal at k
        On one three-hop question with two of three pieces found, your two metrics now
        report 0.667 and 0.000. That 0.667 is the number that goes in the deck.
```"""},
  {"by": "lena", "body": """The failures are real and I would take a step back before fixing
them, because I think the unit is asking you to build the wrong metric.

nDCG was designed for graded relevance over a ranked list where the judgements are per document
and largely independent. Multi-hop evidence is neither of those, and you are already discovering
it — the whole `credits a gold piece once` problem exists because you are bolting a set-coverage
idea onto a rank metric that has no concept of it.

The LinkedIn knowledge-graph RAG work at SIGIR 2024 (arXiv:2404.17723) reports **MRR up 77.6%**
and median resolution time down 28.6% on a customer-service corpus, and MRR is what they lead
with. It is one number, it has no normaliser to get wrong, and it maps to the thing a user
notices, which is how far down the list the useful thing was.

Report evidence recall, full-chain recall and MRR. You lose nothing you were going to act on."""},
  {"by": "dan", "body": """That is a much cleaner story than the one I was fighting with, and
the argument about set coverage against rank matches the shape of both failures exactly. Neither
of them is about my loop. Both are about nDCG being asked to do set arithmetic it was not built
for.

Swapped nDCG for MRR over the first satisfying chunk. Six lines shorter, no normaliser to get
wrong, and the two recalls are untouched.

Now three nDCG checks fail instead of two, and the new one is `nDCG penalises rank, not just
presence`, which I assume is the checks being written against the unit rather than against the
metric. If E1 wants nDCG specifically I will put it back, but I would rather understand why
first."""},
  {"by": "marcus", "body": """Hold on. You have replaced a metric you could not yet explain
with one that hides the same problems, and you did it inside a single reply.

The LinkedIn result is real, on a corpus where each ticket has essentially one right answer to
find. Look at what this corpus is. Of 207 answerable questions the gold evidence arrives in
**1: 21 · 2: 59 · 3: 21 · 4: 100 · 6: 6** pieces. A hundred need four separate pieces. MRR scores
the rank of the *first* useful thing, so on a four-piece question it is satisfied by one of them
and says nothing about the rest.

And the check you have newly broken is the tell. `nDCG penalises rank, not just presence` fails
because MRR stops at the first satisfying chunk, so it returns the same number whether the
retriever found one of the three pieces or all three. You have traded a metric that cannot go
down for one that cannot see two thirds of the question.

Dan, the sentence worth sitting with is your own: *I cannot construct the input where I would
have noticed*. That is not a gap in your imagination. Feed your original function one gold chunk
at rank 1 and seven distractors. It returns 1.0. Two gold chunks at ranks 1 and 2 with six
distractors. Also 1.0. `ideal` is built from `len(seen)`, which is how many you found, so the
denominator moves with the numerator and the ratio cannot go down."""},
  {"by": "maintainer", "body": """Marcus has the mechanism. Worth stating in the form that transfers,
because self-normalisation is not an nDCG problem.

**A metric whose denominator is derived from its own output cannot go down.** The ideal DCG is
the score of the best ranking that was *possible* — every gold piece in the top positions, capped
at `k` — a property of the question, not of the run. Dan's version asks what the best ranking
would have been given the pieces he happened to find, and the answer to that is always the
ranking he produced.

`nDCG credits a gold piece once` is the same failure on the other axis. Three chunks satisfying
hop A are one piece of evidence found three times, and counting them as three rewards
near-duplicates. That is why `gold_map` is `dict[str, set[str]]`.

Lena's argument needs a condition, and it is worth naming rather than waving off. On single-piece
lookups MRR is the better number: one right answer, the user's cost is how far they scroll, and
there is nothing to normalise. On a corpus where half the answerable set needs four pieces or
more it answers a question nobody asked. The paper is not at fault. That is what happens when a result crosses a setup change and nobody
checks which assumption carried it.

Dan, you accepted a confident answer inside one comment and it moved you further from the fix.
The failing check said so in the time it takes to re-run the grader, the cheapest correction in this thread.""",
   "accepted": True},
  {"by": "dan", "body": """Green. `ideal = sum(1/log2(i+1) for i in range(1, min(len(gold_map),
k) + 1))`, and the de-duplication was already right — I just needed to stop letting `seen` set
the denominator.

Two things I did not expect.

The grader's closing note is the actual unit: on one three-hop question with two of three pieces
found, my two recalls now report **0.667** and **0.000**. Both correct. The first one is the one
that would have gone in a slide.

And the committed run says the same thing at scale — evidence recall **0.7645**, full-chain
recall **0.4686**, answer correct **0.4115**. I assumed a gap that size meant something was
broken. The brief walks it out: weighted over the gold-piece counts at p = 0.7645, independence
predicts **0.4603**, and the measured value is **+0.0083** above that. There is nothing to hunt
for. Reading that saved me the quarter the brief says it saves you.

Lena, no complaint about the citation — I would not have known to check whether the setup
matched, and now I do."""},
  {"by": "lena", "body": """Taking the correction. The paper is good and my use of it was not: I
reached for the strongest result I could remember rather than the one whose corpus looked like
this one, and the give-away was there in the abstract if I had read for the setup instead of the
number.

For anyone landing here from a search: the retraction in
[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
is the same failure with the citation coming from inside the house. A published number, carried
onward, on a setup nobody re-checked."""},
 ],
},
{
 "category": CAT, "author": "sofia",
 "title": "C1 · every named check passed and both bars are red",
 "body": """**Approach.** Ran the assembler twice on different questions and diffed, as hint 1
says. The prompts diverge almost immediately, at the timestamp glued onto the end of the system
block. Diffed again and found `Tenant:` and `Requester role:` also vary across the trace.

So: three volatile fields, and my rule was that anything varying between requests belongs after
the barrier. I moved the tenant with more conviction than the others. A tenant identifier sitting
inside a prefix that a cache is designed to share is the kind of thing I would flag in review
whatever the cost numbers said.

**Your assemble()**

```python
    parts = [
        SYSTEM,
        INSTRUCTIONS,

        # Everything that varies across the request trace, moved after the barrier "to be safe".
        "Evidence:\\n" + "\\n\\n".join(chunks),
        EXAMPLES,
        f"Tenant: {tenant_id}",
        f"Current time: {now.isoformat(timespec='seconds')}",
        f"Requester role: {user_role}",
        f"Question: {question}",
    ]
```

Nothing is deleted. The "as of when" feature works. The role is still there. The tenant is still
scoped, and now it is scoped somewhere I am happy to defend.

**What surprised me.** All fourteen checks pass and the unit still fails. I have not had a
result of that shape before and I am not sure what to do with it.""",
 "replies": [
  {"by": "labsim-bot", "body": """🔴 `C1` · Find the five characters that cost two thirds of the
bill — **not yet**

`diagnose` · hard · cost · graded in 0.2s on a clean checkout

- ✅ **checks**
- ❌ **bar** `cache_hit_rate ≥ 0.7500` — got `0.6969`
- ❌ **bar** `prefix_tokens_billed ≤ 45.0000` — got `63.2250`

```
        Replaying 200 requests through the cache...
        cache_hit_rate 0.6969 · prefix_tokens_billed 63.2
  pass  the simulation completes
cache_hit_rate = 0.6969, needs cache_hit_rate ≥ 0.7500 — share of each prompt's tokens
served from cache, averaged over 200 requests against a cache that requires a
byte-identical prefix. The assembler as given scores 0.2612; the correct ordering scores
0.8176
prefix_tokens_billed = 63.2250, needs prefix_tokens_billed ≤ 45.0000 — mean full-rate input
tokens per request. 154.04 as given, 38.07 when the volatile fields move after the barrier,
and 63.23 when stable blocks are moved after it too — which is the shape of a fix that
improves the dashboard and the wrong direction on the invoice
```"""},
  {"by": "wei", "body": """You are overthinking the ordering. Delete the timestamp.

(The same argument runs in Show and tell, on *Cut the prompt cache bill on C1 and nearly sent a
client the wrong number* — that one is about what you then tell the client. This is about the
bars.)

We had this exact bill on a support assistant two years ago — a `Current time:` line in the
system block, added by someone who wanted "as of today" answers, and it was costing us the entire
prefix on every request. We took it out, the hit rate went from single digits to seventy-something
inside a deploy, and nobody ever asked for it back. The model does not need to know the wall
clock to read three retrieved passages.

Everything else in your list can stay exactly where it is. One line removed, both bars green,
and you are not shipping a prompt whose block order is load-bearing and undocumented."""},
  {"by": "dan", "body": """Tried it, because it is one line and it sounded right.

Wei is half right and the half that is wrong is the interesting half. Deleting the timestamp
**clears both bars**:

```
- ❌ **checks**
- ✅ **bar** `cache_hit_rate ≥ 0.7500` — got `0.7942`
- ✅ **bar** `prefix_tokens_billed ≤ 45.0000` — got `42.1600`

**Checks that failed**

- `the 'as of when' feature was not deleted to fix a cost bug`
```

and the grader's line under it:

```
  FAIL  the 'as of when' feature was not deleted to fix a cost bug — the timestamp is gone.
        Users ask 'as of when?' — that feature exists for a reason, and removing it makes the
        cache hit and the product worse
```

So the two of you have failed the same unit in opposite directions. Sofia passed every check and
missed both numbers. I hit both numbers and got caught by a check. I did not think a grader could
be built to catch that, and I would like to know how it can, because "you deleted a feature" is
not visible in a hit rate."""},
  {"by": "tomas", "body": """Before the answer — the brief and the grader disagree about the
bars, and somebody should file it.

C1's brief header says:

> **Bars** `cache_hit_rate ≥ 0.6500` · `prefix_tokens_billed ≤ 260`

The bot quotes `≥ 0.7500` and `≤ 45.0000`, and `unit.yaml` is where those come from, so the bot
is right and the brief is stale. That is not cosmetic. Sofia's run scored 0.6969 and 63.2250. At
the numbers printed in the brief she clears both, comfortably, and the unit tells her she is
done. The looser pair does not merely mis-describe the bar — it makes the unit stop teaching the
thing it exists to teach."""},
  {"by": "maintainer", "body": """Tomás is right and that is a real defect, filed with the
`fail-moves-the-wrong-block` decoy attached. `unit.yaml` is the source of truth — the registry
reads its bars and nothing reads the brief header — so that header and the docstring in
`check.py` are the two places to correct.

The severity is the part worth stating. At the numbers printed in the brief, Sofia's run clears
both bars, and so does the unit's own decoy. A decoy that passes is a check that has stopped
existing. Nothing went red in CI because `selftest` grades against `unit.yaml` and prose is not
graded at all, which is the same gap ADR-0015 came through.

Dan's result is the other half of the answer and it is the one to read first. Sofia passed every
named check and missed both numbers. Dan hit both numbers and was caught by a named check.
Neither gate substitutes for the other, and that is the argument for having both."""},
  {"by": "maintainer", "body": """**The mechanism.** A prompt cache reuses the longest
byte-identical *prefix*. A volatile field does not make its own block uncacheable, it makes
everything after it uncacheable. So the cost is measured in stable tokens sitting behind the first volatile byte, not in how many
volatile fields you have. As given, the timestamp lands about
250 bytes in, at the end of the system block and in front of the instructions and the few-shot
block, and both are billed in full on every request although neither has changed since deploy.

That is why one bar cannot grade this. `cache_hit_rate` rises whenever the prefix stabilises,
however you stabilised it. `prefix_tokens_billed` rises when you push cacheable text past the
barrier. Sofia moved `EXAMPLES` after the evidence: 0.6969 and 63.2250, against 0.8176 and 38.07
for the correct ordering.

Dan, a metric cannot see a deleted feature. You catch it by asserting the feature is still
there, which is what the named check does. Wei's fix would be right if nothing depended on the
timestamp. Here, users kept asking.

Sofia, the fact that kills the tenant move is in the simulator:

```python
CACHE_KEY_INCLUDES = ("tenant_id",)
```

The cache is already partitioned per tenant, so the field is constant within any one cache.
Volatility is relative to the cache key, not to the request. Your instinct becomes correct the
day somebody merges the partitions, which is worth a comment by the block.

[ADR-0012](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0012-prompt-block-ordering.md)
is this decision made for real: hit rate 4% to 71%, cost per query down 58%, timestamp at byte
58.""",
   "accepted": True},
  {"by": "sofia", "body": """Green at 0.8176 and 38.07, with `Tenant:` back in block 1 and a
comment above it naming `CACHE_KEY_INCLUDES` as the reason it is allowed to be there.

What surprised me is that "move it somewhere safer" cost more than the bug did. My version had a
better hit rate than the original assembler and a *worse* bill than the correct fix, and if the
only number on the dashboard had been the hit rate I would have called it a win and closed the
ticket. The second bar is the entire reason I found out otherwise.

I also want to name my own move here, since the thread is public. I treated a cost question as
an access-control question, and the access-control answer was not wrong so much as answered
against a threat model I had not checked — the cache was already partitioned, and I never looked
before moving the field. Reading `CACHE_KEY_INCLUDES` first would have cost me thirty seconds."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "R3 · 0.8762 and 0.9684 tell the same story, so why does the bar sit between them",
 "body": """**Approach.** RRF first, straight from the formula — accumulate `1 / (k + rank)` per
`chunk_id` with `rank` from `enumerate(leg, start=1)`, keep one hit object per id, sort
descending. All nine of the structural checks on `rrf` pass, including the ones about the union
surviving and about ignoring `hit.rank`.

Then the diagnostic. The brief asks how much the two legs' failures overlap, so I computed the
overlap of the two sets.

```python
def failure_overlap(dense_misses: set[str], lexical_misses: set[str]) -> float:
    union = dense_misses | lexical_misses
    if not union:
        return 0.0
    return len(dense_misses & lexical_misses) / len(union)
```

**What surprised me.** Rejected, and the corpus was never built, so I have no run of my own to
argue from.

I want to push back on this rather than just fix it. Jaccard is the standard measure of set
overlap, and the brief prints both answers for me: the conditional is **0.9684** and Jaccard on
the same two sets is **0.8762**. Those say the same thing in any sentence I would write for a
client — the two retrievers fail on substantially the same questions, so fusion has very little
to add. Same conclusion, same decision, same slide.

If a metric and its cousin produce the same call, insisting on one of them is a style
preference with a bar attached.""",
 "replies": [
  {"by": "labsim-bot", "body": """🔴 `R3` · Build the rule you rejected, and the measurement that
rejected it — **not yet**

`measure` · hard · retrieval · graded in 0.1s on a clean checkout

- ❌ **checks**
- ❌ **bar** `evidence_recall ≥ 0.7700` — got `not reported`
- ❌ **bar** `failure_overlap ≥ 0.9000` — got `not reported`

**Checks that failed**

- `failure_overlap divides by |D|, not by the union`

```
  pass  rank 1 in a single leg scores exactly 1/(k+1)
  pass  a chunk found by only one leg still survives
  pass  position in the leg is used, not hit.rank
  pass  failure_overlap is conditional, not symmetric
  FAIL  failure_overlap divides by |D|, not by the union — |D and L| / |D| = 1/2 = 0.5; got
        0.25. Jaccard here is 1/4 = 0.25
  pass  failure_overlap of nothing is 0.0
        Structural checks failed, so the corpus was not built. Fix these first — the real run
        takes about eight seconds and it is not worth spending on a bug a synthetic leg can
        find.
check.py did not report `evidence_recall`
check.py did not report `failure_overlap`
```"""},
  {"by": "wei", "body": """I am with you on this. Jaccard is what everyone means by set overlap
and it is what any reviewer will expect to see in the table.

We reported set overlap between retriever failure sets on a hybrid rollout and nobody once asked
whether the denominator was the union or one of the sets, because at values that high the two
land in the same paragraph. 0.88 and 0.97 both read as "these fail together".

The bar sitting at 0.9000 looks to me like it was placed to make a specific implementation pass
rather than to test anything. Fix it to clear the bar, sure. I would not change what I believe
about the measurement."""},
  {"by": "marcus", "body": """The bot has already given you the case where they diverge and it is
in the failure line you both skipped past.

`D = {q1, q2}`, `L = {q2, q3, q4}`. The conditional is `|D ∩ L| / |D| = 1/2 = 0.5`. Jaccard is
`1/4 = 0.25`. A factor of two, on four elements. They agree on this corpus because the two
failure sets happen to be nearly the same size — dense missed **95**, lexical missed **102**,
both missed **92** — and Jaccard's denominator is the union, so it only tracks the conditional
when the sets are close to nested *and* close to equal in size. Change either of those and the
two numbers separate.

Which reduces Aarav's argument to "the metrics agree on this run".
That is a formula that is right for the wrong reason, and the failure mode is that it travels: it
goes into a note, gets re-run on a corpus where the dense leg misses 40 and the lexical leg misses
300, and reports something nobody notices is different in kind.

And the bar is not arbitrary. 0.9684 above it, 0.8762 below it, deliberately, so the wrong formula
fails on a real number instead of on a lint rule. Wei, that is the opposite of placing a bar to
make an implementation pass."""},
  {"by": "maintainer", "body": """Marcus's arithmetic is the reason. Here is the sentence behind it.

The two formulas answer different questions, and only one of them was asked.

- **Jaccard** answers *"how similar are these two failure sets?"* It is symmetric. Neither leg is
  privileged.
- **The conditional** answers *"given that the dense leg already missed this, is BM25 any help?"*
  It is not symmetric, and the asymmetry is the decision: you have a strong leg, you are
  considering paying for a second, and what you need to know is what the second recovers from the
  first one's failures.

Swap the denominator and you stop measuring the thing the money depends on. The two numbers
coinciding here is a property of this corpus, not of the formulas, and that kind of coincidence
is how a wrong method survives for years.

Aarav, the condition under which your version is right does exist. If you were asking whether two
failure reports describe the same incident, or clustering retrievers by how alike their failures
are, Jaccard is correct and the conditional is not. A metric is right or wrong relative to a
decision, never on its own.

One more thing, since you raised the ordering as a complaint. The corpus is not built when a
structural check fails, and that is not fussiness about eight seconds. A measurement produced by
code with a known defect is worse than none, because it arrives with four decimal places attached
and gets quoted onward. That is the whole of
[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md).""",
   "accepted": True},
  {"by": "aarav", "body": """Fixed — `len(dense_misses & lexical_misses) / len(dense_misses)` —
and green. `evidence_recall 0.7709`, `failure_overlap 0.9684`, both bars cleared, about eight
seconds.

Taking the correction properly. I called it a style preference because the two numbers landed in
the same sentence *on the run in front of me*, and that is me declaring a thing settled from one
sample, which is a habit I have and which is cheaper to catch here than in front of a client.

The line the grader prints when it clears is the one I will actually reuse:

> 0.9684 of the questions the dense leg misses are also missed by BM25.

92 of 95. Marcus is right that this closes the R2 thread rather than continuing it. That argument
was about how to weight the two legs' votes, and the answer is that there was almost no question
on which the second vote could change the outcome at any weight.

What I did not expect is how much this does *not* say. On the committed n=243 comparison, going
from BM25 alone to equal-weight RRF is `evidence_recall +0.0624`, interval `(+0.0407, +0.0857)` —
a real gain. Going from the dense leg alone to RRF is `+0.0008`, interval `(−0.0101, +0.0109)` —
inside the noise band. Fusion beats the weaker leg and does nothing measurable over the stronger
one, and both of those are consistent with 0.9684. The retraction in ADR-0015 is the version of
this repository that had the first half backwards."""},
  {"by": "marcus", "body": """The pair of intervals in Aarav's last paragraph is worth pulling out
for anyone heading into P1, because it is the shape of finding that decays fastest.

"Fusion helps" and "fusion does nothing" are both true here, of different comparisons, and a note
that reports one of them without its interval and without saying which baseline it is against
will be quoted as the other one within a quarter. That is not a hypothetical failure mode in this
repository. It is the documented one."""},
 ],
},
]
