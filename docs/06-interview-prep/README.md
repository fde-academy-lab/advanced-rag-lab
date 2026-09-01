# 06 · Interview prep

Questions asked of retrieval, RAG and applied-ML candidates at companies that interview hard,
grouped by what they actually test. Each carries the panel's intent, a model answer at the
level expected, the follow-ups that separate a good answer from a strong one, and the specific
things that lose the room.

| File | Band | Covers |
|---|---|---|
| [retrieval.md](retrieval.md) | Core | BM25 internals, dense vs sparse, ANN structure, fusion, reranking |
| [evaluation.md](evaluation.md) | Core | Metric design, annotation, significance, judge calibration, gaming |
| [systems-design.md](systems-design.md) | Senior | Freshness, permissions, multi-tenancy, index lifecycle, scale |
| [mathematics.md](mathematics.md) | Hard | The derivations: BM25 saturation, SVD, RRF, nDCG, bootstrap, κ |
| [coding.md](coding.md) | Screen | What gets asked at a terminal, with reference implementations |
| [behavioural.md](behavioural.md) | All | Ambiguity, disagreement, shipping a negative result, client pressure |
| [mock-loops.md](mock-loops.md) | — | Four full loops, timed, with the interviewer's script and scoring sheet |
| [legacy-bank.md](legacy-bank.md) | — | The original 18-question set, kept because the answers are still good |

## Drilling it

The prose here holds the answers. [`interview-bank/`](../../interview-bank/) holds the practice
loop — eight named approach models, a machine-readable index over these files, and a timed drill:

```bash
python interview-bank/practice.py --drill models
```

That makes you name which mental model fires **before** you answer, times you at ninety seconds,
then shows the trap and the follow-ups the interviewer has queued.

Answer quality is graded on a four-level scale used consistently throughout: **misses**,
**passes a screen**, **hires at mid-level**, **hires at senior**. Read the senior answer and
the mid answer together — the delta between them is the thing being taught.
