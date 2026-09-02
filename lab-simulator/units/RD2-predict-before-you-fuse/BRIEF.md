# RD2 · Write down what fusion will score before you look. Then look.

**Track** retrieval · **Kind** drill · **Mode** answer · **Difficulty** medium · **~10 min**
**Prerequisites** RD1

---

You know what reciprocal rank fusion is. Now predict what it does.

Three arms on this repository's corpus — 243 questions, structural chunking, 100 candidates, the
cross-encoder reranker, **k = 8**:

- BM25 alone
- the dense (LSA) leg alone
- equal-weight RRF of the two

Fill `answer.yaml` with your predicted **evidence recall** for each, which single leg is
stronger, and whether fusion beats its better leg by more than about a point. **Do not open the
measurement note first.** The value of this drill is the distance between your number and the
measured one, and there is no distance if you copy it.

Then post it. The grader knows the measured values and tells you how far off each was.

## Why predict

A prediction is a claim about a mechanism. "Fusion will win by five points" is a claim that the
two legs fail on different queries. "Dense will lose" is a claim about a corpus of paraphrase
versus one of identifiers. Being wrong tells you which model of the system you were carrying —
and this repository carried the wrong one for months, in print, with ADRs.

<details><summary>Hint 1 — what kind of corpus</summary>

Client Zero's questions are paraphrase and inference over incident prose. Term overlap between a
question and its evidence is low by construction. Which leg does that favour?
</details>

<details><summary>Hint 2 — when fusion pays</summary>

Fusion recovers a question only when one leg found what the other missed. If both miss the same
questions, the merge has nothing to recover. `python scripts/failure_overlap.py` measures it.
</details>
