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

| Configuration | Evidence recall@8 |
|---|---|
| BM25 alone | 0.7645 |
| Equal-weight RRF (BM25 + dense) | below BM25, at every k |
| Weighted fusion, α = 0.2 | **0.7891**, [+0.008, +0.041], holds on frozen |

**The mechanism.** RRF is a **voting rule that treats every voter as equally credible.** Fuse a
strong leg with a weak one at equal weight and the result moves toward the weak one.

Scale-invariance is the property that lets RRF work without normalisation — and it is exactly the
property that discards the score distribution that would have told you to down-weight the weak
leg. The virtue and the failure are the same mechanism.

Note that `k = 60` does not save you. `k` controls how much a single voter's *first preference*
counts. It does not control how much a *voter* counts.

**The condition.** The expected result returns when both legs are comparably strong. Our LSA
dense leg is materially weaker than BM25 on this corpus; a modern sentence embedder would likely
close that gap and RRF should then win.

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
