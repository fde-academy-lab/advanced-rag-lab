# XD1 · k goes from 5 to 10. Which way does context precision move, and by how much?

**Track** context · **Kind** drill · **Mode** answer · **Difficulty** medium · **~8 min**
**Prerequisites** ED1

---

BM25 arm, cross-encoder reranked, at **k = 5**:

| metric | value |
|---|---|
| `evidence_recall` | 0.6329 |
| `context_precision` | 0.3029 |

Now k goes to **10**. Before you open the k grid, commit to:

- which way `context_precision` moves
- which way `evidence_recall` moves
- a number for `context_precision` at k=10

And answer the question that makes this a drill rather than arithmetic: a team sets a release
gate of *"context precision must stay above 0.30"*. **What config change clears that gate
without improving retrieval at all?**

<details><summary>Hint 1</summary>

Write the definition down. What is in the denominator of context precision, and who chose it?
</details>

<details><summary>Hint 2</summary>

The gold set for a question does not grow when k does. The slots do.
</details>
