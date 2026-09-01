# Case studies

Four studies of retrieval systems meeting reality. Three are drawn from published work with
citations and reported figures; the fourth is this repository's own results, including the ones
that went the wrong way.

| # | Case | Source | What it teaches |
|---|---|---|---|
| [CS-01](CS-01-contextual-retrieval.md) | Contextual Retrieval | Anthropic, 2024 | An index-time intervention with a large measured gain — and the cost model that decides whether you can afford it |
| [CS-02](CS-02-knowledge-graph-rag.md) | Knowledge-graph RAG | LinkedIn, SIGIR 2024 | The win came from *representation*, not a better retriever. Also: what a business metric looks like |
| [CS-03](CS-03-seven-failure-points.md) | Seven failure points | Barnett et al., CAIN 2024 | The taxonomy that turns "the answers are wrong" into a locatable defect |
| [CS-04](CS-04-our-own-negative-results.md) | Three results that went the wrong way | This repository | What a negative result looks like when it is done properly |

## The shape each one follows

1. **The situation** — what was actually broken
2. **The approach** — what was tried, with the architecture
3. **What it moved** — the numbers, as published
4. **Solution dissection** — what each piece fixes and what it costs
5. **ADR-lite** — the decision as you would record it
6. **Does it transfer?** — the precondition their corpus had, and whether yours does
7. **Work it yourself** — an exercise against Client Zero

Step 6 is the one that makes these useful rather than inspirational. **A published number is
evidence about a corpus, not a law about retrieval.** Every case study names the property that
made the intervention work, so you can check whether you have it before spending a quarter.

## On the figures

Every figure attributed to a company or a paper is **as published by that source**, with the
citation at the top of the file. Where we ran the equivalent experiment on Client Zero and got a
different answer, both numbers appear and the difference is explained by a precondition rather
than treated as a contradiction.

Nothing here is inferred, estimated or reconstructed from memory. If a number is ours it says so
and links to the notebook cell that produces it.

## Reading order

New to this? **CS-03 first.** The taxonomy is what you will use on day one of an engagement, and
the other three make more sense once you can locate a failure in it.

Then CS-01 for an intervention that worked, CS-02 for one that came from a different direction
entirely, and CS-04 for the discipline of reporting what did not.
