"""Reading Club threads: four papers, each argued against a number from this corpus.

The category rule is in docs/09-research/paper-notes/README.md — reading a paper produces a
measurement, not a summary — so every thread here follows the note format rather than the shape
of a book club. Claim, method, what we ran, what came back, the mechanism, and the condition
under which the paper's result would return.

Two of the four are negative results and one of those is also a retraction. That is deliberate.
A seeded category where every paper transfers teaches students that papers transfer, which is
the belief this repository exists to remove. It is also the reason the notes carry heading 6:
a paper that does not replicate on a 484-document synthetic corpus has not been refuted, and
naming the missing precondition is the finding.

Reading Club is an open discussion rather than a Q&A category, so no reply here is marked as
the answer. The seeding script strips the flag anyway; it is simply not set.

Every figure quoted is one the repository produces, or one attributed to the source that
published it.
"""
from __future__ import annotations

CAT = "Reading Club"

THREADS = [
{
 "category": CAT, "author": "lena",
 "title": "Cormack et al. 2009 (RRF) — our note said it did not transfer, and the note was wrong",
 "body": """**Paper:** *Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning
Methods*, Cormack, Clarke & Buettcher, SIGIR 2009
([DOI:10.1145/1571941.1572114](https://doi.org/10.1145/1571941.1572114)).

**Claim.** Fuse ranked lists by `Σ 1/(k + rank)` with k around 60 and you beat both the
individual systems and the more elaborate fusion methods, with no training and no score
normalisation.

**Method.** Fusion over TREC runs: several mature retrieval systems on standard collections.

**Why I opened this.** I was writing the seminar questions around our own paper note, which said
equal-weight RRF *lost to BM25 alone* here, and I wanted to open the session with "the 2009
classic does not survive contact with a small corpus". Before writing that I re-ran the
comparison, because the note carried no command and I wanted to see the table myself.

`python scripts/run_eval.py --compare`, 243 questions, k=8 after the cross-encoder:

| configuration | evidence_recall@8 | nDCG@8 |
|---|---|---|
| BM25 alone | 0.7118 | 0.3639 |
| Dense (LSA) alone | 0.7733 | 0.6055 |
| equal-weight RRF | 0.7742 | 0.5302 |
| weighted, α = 0.2 | 0.7645 | 0.4767 |
| weighted, α = 0.5 | 0.7790 | 0.5967 |

RRF does not lose to BM25. It sits at the top of the recall column, and the only arm above it,
weighted α = 0.5, is inside its noise band —
[fusion-rules.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/fusion-rules.md)
reports `rrf → w0.5` at +0.0048, ci (−0.0024, +0.0145).

So two questions for the session, and I do not have clean answers to either. Is our result a
refutation of the paper or a case where its precondition is absent? And what is the correct
thing to do with a note whose headline claim I quoted in a deck three weeks ago?""",
 "replies": [
  {"by": "wei", "body": """Careful before you rewrite the note. That table does not match
anything I have seen in production, and the old note did.

At my last company we ran exactly this pair on a support corpus, and BM25 was the strong leg by
a distance. Customers search with error codes, product SKUs and version strings, and the
embedding model has never seen any of them. The dense leg was mostly there to catch the
"my thing is broken and I cannot describe it" queries, which are a small share of traffic.

A dense retriever that beats BM25 by six points on a support corpus reads to me like a config
difference rather than a finding. Check whether the reranker ran on both arms, and check what
the BM25 arm is doing with the analyser. The usual cause of a BM25 leg that underperforms is
that somebody stemmed at index time and not at query time, and the number that comes out looks
like a fair fight and is not."""},
  {"by": "dan", "body": """That would explain it, and it matches what I have been telling people
— I have said "the dense leg is the weak one here" out loud in at least two study sessions,
because that is what the note said and Wei has actually shipped one of these.

Lena, is there a switch that turns the reranker off per arm? If the comparison ran it on one
side only I would rather find that out before the seminar than during it."""},
  {"by": "marcus", "body": """The reranker runs on every arm — that is what `--compare` does,
and you can see it in the harness. But you do not have to take that on trust, because the paired
bootstrap answers Wei's objection directly.

| comparison | metric | delta | 95% interval |
|---|---|---|---|
| bm25 → dense | evidence recall | +0.0616 | (+0.0382, +0.0870) |
| bm25 → rrf | evidence recall | +0.0624 | (+0.0407, +0.0857) |

Both intervals clear zero comfortably. A stemming asymmetry would show up as a wobble, not as a
gap that holds over 2000 resamples of the same 243 questions.

Then the part nobody has said yet, which I think is the actual reading:

| comparison | metric | delta | 95% interval |
|---|---|---|---|
| dense → rrf | evidence recall | +0.0008 | (−0.0101, +0.0109) |
| dense → rrf | nDCG | −0.0753 | (−0.1061, −0.0462) |

RRF beats BM25, and RRF is indistinguishable from the dense leg on its own while measurably
worse than it at ranking. Both of those are true at once, and the second one is not about the
paper at all."""},
  {"by": "lena", "body": """Then the fix might be k. The paper uses k = 60 on TREC runs, and
those pools are enormous compared to ours — 484 documents against a standard collection is not
the same experiment. A smaller k sharpens the contribution of a system's top ranks, so if our
dense leg is the better one, shrinking k should let it dominate the fused list and we would
recover its nDCG while keeping the recall.

I would like to sweep k from 5 to 60 before we conclude anything about the fusion rule
itself."""},
  {"by": "maintainer", "body": """The sweep is cheap and you should run it, but the mechanism you
are hoping for is not there, and it is worth being precise about why.

At k = 60 rank 1 scores 1/61 and rank 2 scores 1/62 — a gap of about 1.6 per cent. Shrinking
k widens that gap, so a *voter's first preference* counts for more against its second. It does
not change how much a **voter** counts, and it does the same thing to both legs. Nothing in the
constant says "this system is more credible than that one", which is what our table asks for.

The precondition in the paper is complementarity rather than corpus size: mature systems that
are good in *different* ways. Two systems that fail on the same queries carry one signal between
them, and fusing a signal with itself returns the signal.

Here is the diagnostic nobody ran before the original note was written, on the 207 answerable
questions:

```
dense leg missed          95
lexical leg missed       102
both missed               92

P(lexical also misses | dense misses)  0.9684
Jaccard of the two failure sets        0.8762
```

Ninety-two of the ninety-five questions the dense leg misses are also missed by BM25. No fusion
rule had room to add much, at any k and any weighting.

Wei's corpus is the condition under which the paper's result returns, and he is right about it.
Identifier traffic gives BM25 a slice the dense leg cannot reach, and the failure sets separate.
`EX-15` is that experiment with a real sentence encoder.

Rewrite the note, keep the wrong version visible as a correction block, and attach the command.
The wrong claim stood for months because it was a number nobody could re-derive in one line —
[ADR-0015](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
says that plainly."""},
  {"by": "lena", "body": """Rewritten, with the retracted paragraph kept above the correction so
anybody who quoted it can find out that they did:
[rrf.md](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/paper-notes/rrf.md).

What surprised me is that the paper is right on both readings at once. RRF beat every other
fusion rule we tried, parameter-free, exactly as advertised — and the entire exercise sits
inside the noise band of one of its own legs. I had been treating "the paper replicated" and
"the technique was worth building" as the same question and they are not related.

The seminar question changed as a result. It was "does the 2009 result survive on a small
corpus". It is now: **what are you asserting about your two retrievers when you decide to fuse
them, and which single command would tell you whether it is true?** Wei, I would like you to
open with your corpus, because it is the case where the answer is yes."""},
 ],
},
{
 "category": CAT, "author": "priya",
 "title": "MultiHop-RAG (Tang & Yang, COLM 2024) — we borrowed the schema, so where are the hard questions?",
 "body": """**Paper:** *MultiHop-RAG: Benchmarking Retrieval-Augmented Generation for Multi-Hop
Queries*, Tang & Yang, COLM 2024 ([arXiv:2401.15391](https://arxiv.org/abs/2401.15391)).

**Claim, as I read it.** Queries that need evidence from several documents are a distinct and
much harder regime than single-document QA, and the reason existing benchmarks hide it is that
they do not label which pieces of evidence a question needs.

**Method.** News articles, 2,556 questions, human-annotated evidence per question. We did not
download it —
[ADR-0002](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0002-synthetic-corpus.md)
explains why, and the short version is that generating from a fact graph gives gold evidence
that is true by construction instead of true-if-the-annotator-was-having-a-good-day. We kept the
record shape: query, answer, question_type, evidence_list.

**What I was building.** Our docs said full-chain recall sat 21 points below what independence
predicts, which means some questions are hard in a structural way. So I spent two days on a
second-pass reranker that boosts chunks from documents already represented in the top-k, on the
theory that a question's pieces cluster by document and one recovered piece makes the rest
cheaper to find.

```python
# after the cross-encoder, before packing
seen_docs = Counter(h.doc_id for h in hits[:k])
for h in candidates:
    h.score += CLUSTER_BONUS * seen_docs[h.doc_id]
```

**What stopped me.** I ran `python scripts/independence.py` to get a baseline for the write-up,
and the shortfall I was building against is not there. I would rather understand what happened
than quietly delete the branch.""",
 "replies": [
  {"by": "wei", "body": """Do not delete it. Correlated failure across hops is real and I would
be surprised if it is genuinely absent here rather than hidden by how the metric is computed.

The intuition holds up everywhere I have seen it: hop two is phrased against the *answer* to hop
one, so when hop one misses you are searching with a question that has no chance. The failures
are not independent because the second draw depends on the first. Document-cluster boosting is
the standard fix and it is what I would build too.

Before you bin it, check whether the independence script is comparing like with like. If it
takes `p` from the aggregate evidence recall and applies it per piece, it is assuming every
piece is equally easy, which is exactly the assumption a correlated corpus violates."""},
  {"by": "marcus", "body": """The script does take `p` from the aggregate, and Wei is right that
this is the assumption under test. It is also reported both ways, which is the part that decides
it:

| | value |
|---|---|
| `evidence_recall` macro | 0.7645 |
| `evidence_recall` micro (pieces found / pieces total) | 0.7257 |
| `full_chain_recall`, measured | **0.4686** |
| independence prediction at the macro rate | 0.4603 |
| independence prediction at the micro rate | 0.4007 |

Measured is **+0.0083** above the macro prediction and +0.0679 above the micro one. Under either
choice of `p`, measured full-chain recall is at or slightly above independence. There is no
residual, so there is nothing for a hidden class of hard questions to explain.

The 21-point shortfall was arithmetic on the wrong quantity. It raised `p` to the power of the
`hops` field, which is 77 one-hop and 130 two-hop, while `full_chain_recall` requires **every
gold piece**. The pieces distribute `{1: 21, 2: 59, 3: 21, 4: 100, 6: 6}` over the 207 answerable
questions. Half of them need four or more, and the metric scores 1.0 only when all four arrive.
The mixture it quoted, 128 / 61 / 18, is not produced by any configuration of this repository."""},
  {"by": "dan", "body": """So is full-chain recall just measuring how many pieces a question
needs? If the whole gap between 0.7645 and 0.4686 is `p` raised to the piece count, I am not
sure what the metric tells me that the histogram does not already.

I ask because I have been quoting the gap between those two numbers in study sessions as
evidence that multi-hop is hard, and on this reading it is evidence that four is bigger than one.
Those are different sentences and I have been saying the wrong one."""},
  {"by": "maintainer", "body": """It tells you what neither number shows alone, which is
whether the residual is zero. Here it is, and that is a finding rather than a disappointment:
Priya was about to spend a fortnight hunting for structure that is not there, and one command
said so.

The mechanism is the corpus. Our fact graph spreads a question's evidence across documents by
construction, so a retriever whose misses cluster by document does not line up with how a
question's pieces are distributed. Correlated failure needs both halves: evidence that clusters
and failures that cluster the same way. Wei's version has both, and it is common.

Two things would bring the correlation back here. A corpus where evidence clusters by document,
which is most real corpora and is not this one. And a much smaller k, where a single `p` stops
describing every piece: at k = 3 the shipped configuration retrieves 0.5024 evidence recall
against 0.7645 at k = 8, and the pieces at the bottom of that list are not drawn from the same
distribution as the ones at the top.

One correction to the framing, though. I do not believe the paper claims anything about
correlated failure across hops, and I would not want that attributed to it in the note. The
prediction was ours, the arithmetic was ours, and it was ours to get wrong. What Tang & Yang gave
us is `evidence_list` — the field without which none of this is measurable at all, and the reason
we kept their record shape when we kept nothing else."""},
  {"by": "tomas", "body": """What stops the corrected number rotting the same way? The wrong one
lived in the docs long enough to end up in a deck, and the correction is currently one paragraph
in one file.

If the answer is "somebody re-runs it when they remember", that is the same arrangement that
produced the first one, and it survived long enough to reach a deck. I would like to know what
fails, loudly, on the day the corpus changes and these figures stop being true."""},
  {"by": "marcus", "body": """`tests/test_measurements.py` recomputes the piece distribution from
the corpus and fails if the figures quoted in the docs drift from it. So the note is checked on
every push, along with the four documents that quote it, rather than every time somebody
remembers.

What it does **not** read is anything under `scripts/seed/`, so the histogram in *this* thread is
not covered by it. Seeded prose is exactly the surface the last one rotted on.

That covers the numbers a test can recompute. It does not cover a sentence like "and therefore
the failures are correlated", which is the part that actually did the damage, and I do not think
CI can be made to cover it."""},
  {"by": "priya", "body": """Branch closed, and I have written the diagnostic up as the finding
rather than the prototype.

The uncomfortable part is the order I did things in. Two days of implementation against a
premise I never checked, then one command that took under a second and removed the premise. I
have the same habit in code review and I did not think I had it in research.

For anyone repeating this: the piece histogram is worth looking at before anything else. Half
our answerable questions need four pieces, so full-chain recall was always going to look
alarming next to evidence recall, and "alarming" and "structurally hard" are not the same
thing."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "Anthropic's Contextual Retrieval post — the client has read it and wants the 5.7% to 1.9%",
 "body": """**Source:** Anthropic, *Introducing Contextual Retrieval* (2024),
[anthropic.com/news/contextual-retrieval](https://www.anthropic.com/news/contextual-retrieval).
An engineering post rather than a paper, which matters for how we quote it.

**Claim.** Chunks lose the context that makes them findable, so at index time you generate a
short chunk-specific blurb explaining where the chunk sits in its document and prepend it before
embedding and before BM25 indexing. They report failed retrieval dropping from **5.7% to 1.9%**,
and roughly **$1.02 per million document tokens** to produce the context, which prompt caching is
what makes affordable. They kept BM25 alongside the embeddings.

**Situation.** My client's head of support read this on a Friday and asked on Monday why we are
not doing it. I said it was an index-time preprocessing step and we would look at what it does on
their corpus, which I now think was slightly more confident than I had any basis for.

**What I want from this thread.** Two things. Can we replicate any part of it here, so I have
something measured rather than quoted. And if we cannot, what is the honest sentence to say to a
client who has a number from a vendor blog and expects it to be our number too.

The reading list already warns about this — reported figures on somebody's corpus are real
results, not benchmarks you should expect to reproduce. I would like to be able to explain *why*
rather than just repeating the warning at him.""",
 "replies": [
  {"by": "dan", "body": """The cost part looks like the easy half. If caching is what makes the
generation affordable, and we already have the caching work from unit C1, then the index-time
cost is close to a rounding error and the only real question is whether the retrieval gain shows
up. That is one eval run.

Is there a reason we cannot point our own pipeline at it this week? I would rather find out that
it does nothing on our corpus than argue about whether it would."""},
  {"by": "priya", "body": """We already did, and the result is in the repository — which is a
better answer than the one I was about to give.

`chunking.contextual` in
[`raglab/chunking.py`](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/chunking.py) is the
index-time half, and its docstring says so: *"This is the Anthropic contextual-retrieval recipe
from the deck."* The situating sentence is produced offline by a deterministic template — title,
source, date, section — rather than by a model, so the recipe's **shape** replicates here and its
**substance** does not. `describe=fn` is the seam for a real generator.

What that measured, from
[the chunking LLD](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/lld/chunking.md):
**2.4× storage, 3.1× index build time, and a recall change inside the noise band.** The mechanism
is a missing precondition rather than a failed technique — published results come from corpora
where a chunk says "the rate was raised to 4.5%" and the entity is three sections up. Ours are
generated to be self-contained, so there is nothing for the added context to disambiguate.

So the honest thing to tell the client is not "it does not work". It is **"it needs a condition
your corpus may well have and ours does not"**, and the condition is checkable in an afternoon:
sample fifty chunks and count how many name their own subject.

The other half of their post we *can* price. Unit C1's simulator, over 200 requests:

| assembler | cache hit rate | mean full-rate tokens billed |
|---|---|---|
| as given | 0.2612 | 154.04 |
| correct volatility order | 0.8176 | 38.07 |
| timestamp deleted instead | 0.7942 | 42.16 |
| stable blocks moved too | 0.6969 | 63.23 |

And in production,
[ADR-0012](/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0012-prompt-block-ordering.md)
records the same fix taking hit rate from 4% to 71% with cost per query down 58%, after a
timestamp at byte 58 of the system prompt had been invalidating everything after it for three
weeks."""},
  {"by": "aarav", "body": """0.2612 to 0.8176 is a story I can tell on Thursday. Cache hit rate
tripled in the simulator, cost per query down 58% in the production case, and both of those are
ours rather than quoted at us.

My instinct is to take that in, say contextual retrieval sits on the roadmap behind it, and move
the conversation to their corpus before anybody asks me for a date. That gets the meeting to a
useful place and it is a measured number, so I do not see the objection yet."""},
  {"by": "marcus", "body": """Those are two different claims and putting them in one slide is how
the client ends up quoting a number back at us in six months.

Theirs is a **retrieval quality** claim: fewer queries where the right chunk never arrives.
Ours is a **billing** claim about the prefix of a prompt. Neither one predicts the other, and
you would be presenting a cost result as evidence for a quality proposal.

There is a harder problem underneath it. On this corpus retrieval quality does not move the
metric the client feels. Across the fusion arms evidence recall spans 0.7118 to 0.7790, three of
those comparisons statistically solid, while answer correctness spans 0.3992 to 0.4156 and
**every pairwise comparison on it is inside the noise band**. The numerically best answers come
from the numerically worst retriever. A real recall gain from contextual retrieval would land on
a system that is generation-limited, so the honest forecast is that the customer sees nothing."""},
  {"by": "maintainer", "body": """Marcus has the presentation problem. The mechanism answers
Aarav's second question, which is the one worth taking to the client.

Contextual retrieval repairs chunks that have **lost their referents**. A chunk that reads
"revenue grew 3% over the previous quarter" is unfindable because it names neither the company
nor the quarter, and the blurb puts them back. That failure is a property of long human-written
prose: pronouns, bare quarter labels, "the company", tables whose header is four chunks earlier.

Our documents are rendered from a fact graph, so entity names repeat in nearly every chunk by
construction. The failure their method repairs barely occurs here, so a replication would measure
close to nothing and would be telling you about our corpus rather than about their method. The
note we owe should therefore record this as **untested** rather than "does not apply" — that is
what heading 6 of
[the note format](/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/paper-notes/README.md)
is for, and writing it is the action this thread produces.

The condition under which their result returns is a corpus of long documents written for humans:
transcripts, filings, incident reviews with a narrative. Client Zero's real corpus probably
qualifies and ours deliberately does not.

Two more things worth carrying to the client. They **kept BM25**, which is the same finding as
our identifier slice from the other direction — the widely-repeated "dense is enough" assumption
did not survive contact with identifiers on their corpus either. And the cheap diagnostic before
committing to any of it is to sample thirty chunks from their corpus and ask whether each one is
interpretable alone. If most are, the method has nothing to repair."""},
  {"by": "tomas", "body": """Add the operational cost to whatever you present, because $1.02 per
million document tokens is not paid once.

It is paid on every corpus refresh, for every re-chunk, and every time somebody changes the
chunker, which is not a one-off event. So it becomes a line item on the
re-indexing job rather than a one-off setup fee, and re-indexing is already the thing that gets
deferred until it is an incident.

I am not arguing against it. I am arguing that "index-time" reads as "free after the first day"
and it is not."""},
  {"by": "aarav", "body": """Fair, and I was doing exactly what Marcus described.

What I actually said on Thursday: their number is real on their corpus, the failure it fixes is
chunks that cannot be understood on their own, and we can find out in an afternoon how much of
their corpus looks like that by sampling thirty chunks and reading them. Separately, here is a
cost result we measured ourselves, which is unrelated to it.

He was happier with that than with a number, which I did not expect. The sampling exercise gave
him something to do rather than something to wait for."""},
 ],
},
{
 "category": CAT, "author": "tomas",
 "title": "CRAG's retrieval evaluator as a component we could actually grade before wiring it in",
 "body": """**Papers.** Asai et al., *Self-RAG: Learning to Retrieve, Generate, and Critique
through Self-Reflection* ([arXiv:2310.11511](https://arxiv.org/abs/2310.11511)), and Yan et al.,
*Corrective Retrieval Augmented Generation*
([arXiv:2401.15884](https://arxiv.org/abs/2401.15884)).

**Claims, as I understand them.** Self-RAG has the model emit critique tokens about its own
retrieval and generation, so it can decide to retrieve again, use what it has, or decline. CRAG
puts a retrieval evaluator in front of generation that grades the retrieved set as correct,
incorrect or ambiguous and acts differently in each case.

**Why I am reading them.** Our scorecard, `structural/weighted/cross/k=8`, n=243:

```
abstention_recall        0.0
abstention_f1            0.0
false_answers_on_null     36
over_refusals              0
answer_correct        0.4115
```

Thirty-six questions in the eval set cannot be answered from the corpus, and we answer all
thirty-six. Not with a hedge — with a plausible sentence and a citation that resolves.

That is the failure I would be paged for. Every other number on the scorecard is a quality
conversation; this one is the system telling a customer something untrue with a source link
attached, and it is invisible to every average-case metric we report.

My instinct is to stop answering below a support threshold and accept the refusals, this week,
and treat the paper-shaped solutions as next quarter's work. I would like to be told why that is
wrong before I argue for it.""",
 "replies": [
  {"by": "wei", "body": """You do not need either paper for this. Threshold the top retrieval
score and refuse below it.

We shipped precisely that on a support assistant and it held for two years. Sweep the cutoff on a
held-out set, stop where the refusal rate is one you can live with, put the number in a config
and review it monthly. It is a short function, it is explainable to a customer, and it does not
add a model call to the critical path.

The papers are interesting and they are for the case where you have already done this and the
threshold is not enough."""},
  {"by": "dan", "body": """That sounds right to me, and it is a great deal less
frightening than fine-tuning anything. Tomás, if a cutoff gets abstention recall off zero this
week, is there a reason not to do that and read the papers afterwards?

The only worry I can think of is picking the cutoff, and Wei has given a procedure for that:
sweep it and stop where the refusal rate is tolerable. That is at least something somebody can
check rather than a hunch."""},
  {"by": "marcus", "body": """There is, and it is measured. The exercise catalogue states the
result for
[EX-18](/fde-academy-lab/advanced-rag-lab/blob/main/docs/03-exercises/catalogue.md): **no
retrieval-score threshold separates answerable from unanswerable here, best F1 0.38.** Somebody
has already swept it.

The mechanism: a null question in this corpus is a plausible question about entities that
genuinely exist, so the retriever returns confident, on-topic, well-ranked chunks, none of which
contains the answer. Low scores never enter into it. Score measures topical match, and
topical match is exactly what these questions have.

Note also that `over_refusals` is currently 0, which is the other half of the trade. Every point
of abstention recall a threshold buys is paid for somewhere in the 207 answerable questions, and
nobody has priced that side. I would want the temporal slice watched in particular — it is 66
questions at 0.091 answer correctness, so whatever makes those hard is already in the
neighbourhood of whatever a score gate would catch. That last part is a hypothesis, not a
result."""},
  {"by": "sofia", "body": """Before we go further into thresholds — how many of the 36 are
unanswerable *for this persona* rather than unanswerable full stop? We have four personas and an
ACL prefilter, and if a question is only null because the evidence was filtered out, then this is
an access-control conversation and the fix is in the prefilter and the message, not in the
generator.

A system that says "I cannot find that" when it means "you are not allowed to see that" is a
different defect, and it is the one that gets escalated."""},
  {"by": "maintainer", "body": """Worth separating, and here they already are: the 36 are
unanswerable by construction, for everybody. The generator builds them as plausible questions the
fact graph cannot answer, and the ACL-restricted documents are a separate built-in failure mode
with its own slice. Conflating them would make the abstention metric unreadable, because the
right behaviour differs. "The answer does not exist" and "the answer exists and is not yours" are
different sentences, and a customer needs to be told which one they are getting.

On the papers, be precise about which part of Self-RAG could run here. As I read it the critique
tokens are trained into the generator rather than prompted, so the mechanism belongs to a
fine-tuned model. Our default generator is `extractive-offline`, a scorer over sentences with a
`support_threshold` and nothing to train, so this is not a method the repository is merely short
of implementing. If you have read the training setup more recently than I have and that is wrong,
say so in this thread rather than in the note.

What transfers is the **shape of the contract**. CRAG's retrieval evaluator is a separate
component with its own inputs and its own labels, so it can be built and measured on its own
before it is wired into anything, and `sufficiency_check` in
[raglab/agent.py](/fde-academy-lab/advanced-rag-lab/blob/main/raglab/agent.py) is a crude version
of that idea already. Building the evaluator and reporting its precision and recall against the
36 is a week of work that does not need a trained model.

The condition under which the papers' numbers would return: a generator you can instruct or
train, and a null base rate resembling production. Ours is 36 of 243, far higher than real
traffic, so a policy tuned on this mix will over-refuse in the field."""},
  {"by": "tomas", "body": """Taking the correction on the threshold. Best F1 0.38 with nothing on the other side of the ledger priced buys a different failure one
quarter later, with my name on the page, and I would have called it a regression when the refusals
started arriving.

What I have actually done: `false_answers_on_null` and `over_refusals` now sit next to each other
on the dashboard, because either one alone can be driven to zero by breaking the other. And I
have written the freeze proposal up as what it is, a policy with a price we have not measured,
rather than as the safe option. Calling it the safe option was the part I got wrong.

Next: the CRAG-shaped evaluator as a standalone component, graded against the 36 before it is
allowed near the pipeline."""},
 ],
},
]
