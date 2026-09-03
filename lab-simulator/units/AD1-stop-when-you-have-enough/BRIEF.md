# AD1 · An agent that keeps searching after it has the answer is paying for confidence it already had

**Track** agentic · **Kind** drill · **Mode** implement · **Difficulty** hard · **~15 min**
**Prerequisites** ED1, RD1

---

A multi-hop loop searches, reads what came back, decides whether to search again. The decision
is the whole design. Too eager and it answers on partial evidence — a confident wrong answer.
Too cautious and every question costs the full budget — the bill triples and the answers do not
improve, because the last three steps were retrieving things it already had.

Implement `stop_at(steps, required)`. Each step is the set of required pieces its results
satisfied. Return the index of the first step at which **everything gathered so far** covers
`required`, or `None` if the budget runs out first.

## The four ways this ships wrong

| check | the version that ships |
|---|---|
| `stops at the first sufficient step` | stops at the *last* sufficient step, or the last step |
| `does not stop early` | stops on the first non-empty result. Some evidence is not enough evidence — this is evidence recall mistaken for full-chain recall, in a loop |
| `returns None when the budget runs out` | returns the last index, and the caller answers anyway |
| `evidence carries across steps` | checks each step's set on its own, forgetting what earlier steps paid for |

This is E1's lesson wearing a loop: the question is whether the *chain* is complete, and the
chain is a union.

<details><summary>Hint 1</summary>

Keep a running set. Union each step into it. Test the running set, not the step.
</details>

<details><summary>Hint 2</summary>

`required <= gathered` is the sufficiency test. Return the index the moment it is true.
</details>
