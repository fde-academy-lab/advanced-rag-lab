# Session 02 · Retrieval internals, and three things that fail

**Length** 3.5 hours · **Notebooks** `03`, `04` · **Phase** P2

## Timings

| Time | What | Mode |
|---|---|---|
| 0:00–0:10 | Open with the failure: ANN recall at 0.00. What could cause that? | Cold open |
| 0:10–0:50 | BM25 from scratch. Saturation, length normalisation, what each knob models | Talk + notebook `04` |
| 0:50–1:10 | The tokenizer demo — break identifiers live | Live |
| 1:10–1:25 | Break | |
| 1:25–2:05 | Dense retrieval, the ANN graph, and why the lattice cannot be crossed | Talk + live |
| 2:05–2:45 | Fusion. Run equal-weight RRF and watch it lose | Exercise |
| 2:45–3:20 | Reranking, and the reranker that made things worse | Talk |
| 3:20–3:30 | Close: which of today's three failures would your monitoring have caught? | Discussion |

## The cold open

Put this on screen before saying anything:

```
ANN recall @ ef=64:  0.00
exact search recall: 0.7645
```

Ask the room what could cause that. Let them run for five minutes. Someone will say "the search
loop is broken" — it is not, and that is the lesson. The loop is correct and the *graph* is not
navigable.

Opening with a broken number rather than a definition is worth the ten minutes. Nobody remembers a
definition of small-world navigability; everybody remembers the graph that could not be crossed.

## The three live demos

**1 · Break the tokenizer.** Remove `tokenchars '_-'`, rebuild, search for `ERR_CONN_RESET`. The
identifier slice goes 0.81 → 0.34 while the aggregate moves 5 points. Show both numbers on screen
at once — the gap between them is the argument for slice-level alerting and it is much more
convincing seen than said.

**2 · Collapse the ANN graph.** Remove the long-range links, re-run. 0.94 → 0.00. Add them back.
Five lines, two orders of magnitude.

**3 · Fuse badly.** Equal-weight RRF against BM25 alone. It loses. Let the room sit with that,
because it contradicts what most of them have read, then give the mechanism: a voting rule that
treats every voter as equally credible moves toward the weak one.

## The exercise

Find α. Sweep the weighted-fusion parameter, plot evidence recall, and report the value they would
ship **with an interval**. Then check it on the frozen slice.

Most will land near 0.2. The ones who report 0.2 *without* an interval get the same question
everyone gets: what is the interval?

## Discussion prompt (post 24 h ahead)

> Name a retrieval failure that an aggregate metric would not catch. Be specific about the query
> class and why the average absorbs it.

## Exit check

Each participant can explain **why a pure k-NN graph stops working as the corpus grows**, in two
sentences, without using the word "navigable" — because using the word is not the same as
understanding the diameter argument.

## Common failure in the room

The fusion result generates real resistance, and it should — it contradicts widely repeated
advice. Do not oversell it. The honest framing is that the received wisdom is a *conditional*
whose condition fails here, and the condition is comparable leg strength. A room that leaves
thinking "hybrid retrieval is a myth" has learned something false.
