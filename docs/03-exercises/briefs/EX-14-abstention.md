# EX-14 · Make the system say "I don't know"

**Difficulty** ★★★★☆ · **Seam** ⑨ generator, ⑦ reranker · **Time** 4 h · **Notebook** `05`, `06`
**Thread** Exercises & Submissions → `EX-14`

## Setup

The eval set contains 36 deliberately unanswerable questions. They name real organisations and
real quarters, but the fact they ask for is not in the corpus. The system currently answers
almost all of them, confidently and wrongly. `abstention_recall` is **0.0000**.

## Task

Build an abstention mechanism and measure it honestly.

1. Pick a signal. Retrieval score, score gap between ranks 1 and 2, mean of top-k, entropy over
   the score distribution — or something else, if you can argue for it.
2. Sweep a threshold. Produce a precision–recall curve for the abstention *decision*.
3. Report best F1 and the operating point you would actually ship, which is usually not the F1
   maximum.

## Acceptance

- A PR curve over the full eval set, not a subsample. If you subsample, the null base rate moves
  and precision is inflated — this happened here and produced a chart that contradicted its own
  caption (issue #7).
- Best F1, and the threshold that achieves it.
- The cost in refused-but-answerable questions at your chosen operating point. Abstention that
  refuses 30% of answerable questions is not a feature.

## The trap

You will not beat **F1 0.38** with a retrieval-score threshold, and the reason is worth finding
yourself before you read it.

<details>
<summary>The mechanism, if you have already measured it and want to check</summary>

The null questions name real entities using the corpus's own vocabulary. The genuine questions
paraphrase — the generator that built them was told to avoid the source's wording. So the
**unanswerable questions are lexically closer to the corpus than the answerable ones.**

Any threshold on retrieval score is therefore reading a feature whose sign is the opposite of
what you assumed, and no amount of threshold tuning repairs a feature with the wrong sign.

</details>

## What good looks like

Full marks for a clean refutation: you tried a signal, it did not separate the classes, and you
diagnosed *why* by examining the score distributions of the two groups rather than concluding
"abstention is hard".

Exemplary if you propose and test a signal about **sufficiency** rather than **similarity** —
whether the retrieved evidence entails an answer, rather than whether it resembles the question.
That is issue #10 and it is genuinely open.

## Extension

Abstention interacts with the judge. If the judge scores an abstention as a wrong answer, you
have built a mechanism the metric punishes. Check what your judge does with abstentions before
you tune anything, and say what you found.
