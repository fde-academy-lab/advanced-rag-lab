# CS-04 · Three of our own results that went the wrong way

> **Source.** This repository. Every number is reproducible from a notebook cell — see the
> "reproduce it" line on each.

**Read this for:** what a negative result looks like when it is done properly, and why three of
them are the most valuable content here.

---

## Why negative results get buried

A negative result is harder to publish than a positive one and easier to hide. Nobody is
suspicious when a technique quietly does not appear in your writeup.

They are also worth more, because a published positive result tells you a technique *can* work
and a published negative one tells you *when it does not* — which is the question you actually
have on an engagement.

**The standard applied here:** a negative result must carry the **mechanism** and the
**condition under which the expected result returns**. Without both it is an anecdote, and it is
graded as one.

---

## N1 · Equal-weight fusion loses to a single retriever

**The received wisdom.** Hybrid retrieval beats either leg alone. Reciprocal Rank Fusion is the
default because it needs no score normalisation and no training.

**What we measured.**

| Configuration | Evidence recall@8 | nDCG@8 |
|---|---|---|
| BM25 alone | 0.7118 | 0.3639 |
| Dense (LSA) alone | 0.7733 | **0.6055** |
| Equal-weight RRF | **0.7742** | 0.5302 |
| Weighted fusion, α = 0.2 | 0.7645 | 0.4767 |
| Weighted fusion, α = 0.5 | **0.7790** | 0.5967 |

Paired bootstrap over questions: `bm25 → rrf` is **+0.0624** evidence recall, ci (+0.0407,
+0.0857) — real. `dense → rrf` is **+0.0008**, ci (−0.0101, +0.0109) — *inside the noise band*.
On nDCG, `dense → rrf` is **−0.0753**, ci (−0.1061, −0.0462) — the unfused leg wins.

**The mechanism.** Fusion combines two signals into a better one only when the legs fail on
**different** queries. Two retrievers that fail together carry one signal between them, and
combining a signal with itself returns the signal.

On this corpus they fail together. The questions are paraphrase and inference over incident
prose; the dense leg handles nearly all of it and BM25 contributes on the exact-identifier slice
— real, and small. RRF finds what the dense leg found, plus a little, minus some ranking quality,
because giving an equal ballot to a leg that is right less often costs precision at the top even
when it does not cost recall.

**This case study is itself a correction.** It previously reported the opposite — that
equal-weight RRF *loses* to BM25 alone, with BM25 at 0.7645 and a mechanism about fusing strong
with weak. Neither reproduces: RRF beats BM25, the dense leg is the stronger of the two, and
0.7645 is the *tuned configuration's* number that had been mis-attributed to BM25 alone. See
[ADR-0015](../../docs/01-architecture/adr/0015-correct-the-fusion-finding.md). The failure that
let it stand for months is worth more than the finding: an eval gate that compares a
configuration against its own history never compares configurations against each other, so
nothing was structured to notice.

Note that `k = 60` does not save you. `k` controls how much a single voter's *first preference*
counts. It does not control how much a *voter* counts.

**The condition.** The expected result returns when the legs fail on **different queries**, not
when they are comparably strong. Here they fail on the same ones: of the 207 answerable
questions the dense leg misses 95, the lexical leg misses 102, and 92 of those are the same
questions — `P(lexical also misses | dense misses)` = **0.9684**, one command,
`python scripts/failure_overlap.py`. There is almost nothing for a merge to recover, which is
why fusion does not separate from its better single leg.

Note also which leg is which: the LSA leg is the **stronger** of the two here, by +0.0616
evidence recall and +0.2416 nDCG over BM25. A modern sentence encoder changes both failure
profiles, and whether that makes them complementary is an empirical question rather than a
safe assumption — it is EX-15.

**Reproduce it.** [Notebook `04`](../../notebooks/04_retrieval_methods_and_reranking.ipynb).

**What it changes.** The fusion *rule* and the fusion *weight* are two separate decisions. Most
material discusses only the first.

---

## N2 · An effect that could not reproduce, because the corpus lacked the precondition

**The claim.** Comparison starvation: when a question compares two entities, retrieval returns
evidence for the more prevalent one and starves the other, producing a confidently half-supported
answer.

**What we measured.** Prevalence ratio between compared entities: **≈ 1.0**. Per-entity recall
gap: indistinguishable from zero, interval spanning it.

**The mechanism.** Client Zero is generated from a fact graph that emits organisations on a
balanced schedule. The precondition for starvation — an imbalance to starve on — is **absent by
construction**.

**Why this is a finding rather than a null.** The honest statement is not "starvation is a myth".
It is one level up:

> A balanced generator cannot measure imbalance failures. Most evaluation sets are built by
> balanced generators, because balanced generators are easier to write. So a whole class of real
> failures is invisible to most people's evaluation, and everybody concludes the failure is rare.

That is a claim about **evaluation sets**, it generalises, and it produced work: an adversarial
slice with deliberate prevalence ratios out to 20:1.

**The condition.** Test it on a corpus with genuine prevalence imbalance. Ours cannot answer the
question either way.

**Reproduce it.** [Notebook `02`](../../notebooks/02_multihop_rag_use_case.ipynb).

**The wider warning.** This is the second technique to fail here for the same reason — contextual
chunking was the first ([CS-01 §7](CS-01-contextual-retrieval.md)). Two failures with one root
cause are not two findings; they are one finding about the corpus generator, which produces text
too well-behaved to test robustness techniques.

---

## N3 · A feature with the wrong sign cannot be tuned into a right one

**The goal.** Make the system decline when it cannot answer. 36 of 243 eval questions are
deliberately unanswerable.

**What we tried.** Four signals, each with a swept threshold: top-1 retrieval score; score gap
between ranks 1 and 2; mean of top-k; entropy over the score distribution.

**What we measured.** Best F1 **0.38**. Nothing separates the classes usefully.

**The mechanism — and it is counter-intuitive.** The null questions **name real entities using
the corpus's own vocabulary**. The genuine questions **paraphrase**, because the generator was
instructed to avoid the source wording.

So the *unanswerable* questions are lexically **closer** to the corpus than the answerable ones.
Every threshold is reading a feature whose sign is the opposite of the assumption, and no amount
of tuning repairs a feature with the wrong sign.

**The condition.** A signal about **sufficiency** rather than **similarity** — whether the
retrieved evidence *entails* an answer, rather than whether it *resembles* the question. Untested
here, and tracked as open work.

**Reproduce it.** [Notebook `05`](../../notebooks/05_llm_context_design.ipynb).

**What it saved.** A week of threshold tuning that could not have worked. That is the return on a
negative result, and it is why the abstention metric is reported at 0.0000 rather than quietly
omitted.

---

## The shape all three share

| | N1 | N2 | N3 |
|---|---|---|---|
| **Expected** | Hybrid wins | Effect reproduces | A threshold separates |
| **Measured** | It lost | It did not | F1 0.38 |
| **Mechanism** | Equal weight moves toward the weak leg | Precondition absent by construction | Feature has the wrong sign |
| **Condition** | Comparable legs | An imbalanced corpus | Entailment, not similarity |
| **What it produced** | Weighted fusion as default | An adversarial eval slice | A week not spent tuning |

Every row has all five cells filled. **A negative result missing the mechanism row is an
anecdote; missing the condition row it is a dismissal.**

## Using these in an interview

This is the single most credible thing you can bring to an evaluation round, because it cannot be
bluffed — you can only describe a result that went against you if you actually ran it.

The structure that lands: *"We measured that and it went the other way. Here is the mechanism,
and here is the condition under which the expected result returns."*

Worked answers in [`docs/06-interview-prep/evaluation.md`](../../docs/06-interview-prep/evaluation.md).

## Exercises

1. Take a technique you believe works and write its N-row: expected, measured, mechanism,
   condition. If you cannot fill "measured", you believe it rather than know it.
2. Design the corpus modification that would make N2 testable, and say what it would cost.
3. Propose an entailment-based sufficiency signal for N3 and state what would falsify it before
   you build it.
