# ED2 · Four deltas, four intervals. Which of them would you ship on?

**Track** evaluation · **Kind** drill · **Mode** answer · **Difficulty** medium · **~8 min**
**Prerequisites** ED1

---

Four rows from this repository's fusion measurement. Delta is the second arm minus the first;
the interval is a paired bootstrap over questions, 2,000 resamples.

| | comparison | metric | delta | 95% interval |
|---|---|---|---|---|
| 1 | bm25 → rrf | evidence recall | +0.0624 | (+0.0407, +0.0857) |
| 2 | dense → rrf | evidence recall | +0.0008 | (−0.0101, +0.0109) |
| 3 | rrf → w0.2 | nDCG | −0.0535 | (−0.0776, −0.0295) |
| 4 | rrf → w0.5 | evidence recall | +0.0048 | (−0.0024, +0.0145) |

Which rows are **real** — a difference a release decision could rest on?

And row 3: the weighted rule (α = 0.2) is the one this repository ships. Is it *better* or
*worse* than RRF on nDCG?

<details><summary>Hint 1</summary>

Ignore the delta column. Look only at whether the two ends of the interval have the same sign.
</details>

<details><summary>Hint 2 — row 3</summary>

Delta is *second minus first*. A negative delta with an interval entirely below zero is a real
difference in the second arm's disfavour.
</details>
