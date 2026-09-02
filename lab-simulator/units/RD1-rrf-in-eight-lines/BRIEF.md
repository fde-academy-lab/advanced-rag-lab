# RD1 · Reciprocal rank fusion, with the two blanks everyone fills in wrong

**Track** retrieval · **Kind** drill · **Mode** implement · **Difficulty** easy · **~10 min**
**Prerequisites** none

---

`starter.py` is a working reciprocal rank fusion with two blanks. Fill them.

$$\mathrm{RRF}(d) = \sum_{\text{legs}} \frac{1}{k + \mathrm{rank}(d)}$$

That is the whole formula (Cormack, Clarke & Büttcher, 2009). The two blanks are the two places
the formula meets Python, and each has an answer that is one character away from right.

## The checks

| check | what it is guarding against |
|---|---|
| `rank 1 is 1/(k+1)` | `enumerate()` starts at 0, so rank 1 scores `1/k`. The fused order is *almost* right, which is why this ships |
| `a chunk in only one leg survives` | A merge that keeps only chunks present in every leg is an intersection. The reason for two retrievers is gone |
| `a chunk in both legs outranks a chunk in one` | The score is a **sum**. Keeping each chunk's best single score throws away agreement, which is the only thing RRF rewards |
| `k=0 makes rank 1 worth twice rank 2` | A sanity check on the constant's job |

<details><summary>Hint 1</summary>

Blank 1 is a keyword argument to `enumerate`. Blank 2 is a fraction with `k` and `rank` in the
denominator.
</details>

<details><summary>Hint 2</summary>

If your fused list has the right *members* and the wrong *order* near the top, it is blank 1.
</details>
