# ED1 · This full-chain recall returns 0.667 on a question it did not answer. Fix it.

**Track** evaluation · **Kind** drill · **Mode** diagnose · **Difficulty** easy · **~10 min**
**Prerequisites** none

---

`starter.py` is a `full_chain_recall` that somebody shipped. It passes the tests they wrote. On
a three-hop question where the retriever found two of the three pieces, it returns **0.667**.

That number is wrong in a way that matters more than most bugs, because it is not wrong — it is
a correct computation of a different metric. Two of three pieces is *evidence recall*. Full-chain
recall asks whether the question can be answered, and two thirds of a reasoning chain produces a
confident wrong answer downstream, not two thirds of a right one.

This repository's committed baseline reports evidence recall **0.7645** and full-chain recall
**0.4686** on the same run. The thirty-point gap between them is the most informative number the
harness produces, and a `full_chain_recall` that averages makes it disappear.

Find the line. Fix it. Keep the two things that are already right: `None` on no gold, and a
piece satisfied by *any* of its chunks.

<details><summary>Hint 1</summary>

The bug is the last line. What should the function return when `found < len(gold_map)`?
</details>

<details><summary>Hint 2</summary>

The metric is per question. Its only values are 1.0 and 0.0.
</details>
