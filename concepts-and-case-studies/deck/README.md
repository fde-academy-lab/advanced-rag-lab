# The accelerator deck

**Retrieval, RAG and Evals — 97 slides.** The taught material behind this repository: decision
trees, decision matrices, high-level designs, engineering budgets, case studies and an interview
bank.

## Viewing it

| Where | How |
|---|---|
| **Online** | [fde-academy-lab.github.io/advanced-rag-lab/deck/](https://fde-academy-lab.github.io/advanced-rag-lab/deck/) — published with the notebooks |
| **Locally** | `open retrieval-rag-and-evals.dc.html` — no server needed |

`support.js` and `deck-stage.js` are the runtime the export needs. Keep all three files together;
the HTML loads `./support.js` by relative path.

The deck pulls its typefaces from Google Fonts, so it degrades to system fonts offline. Nothing
else is fetched.

## What is in it

| Slides | Covers |
|---|---|
| Fault isolation | A decision tree for separating retrieval, context and generation failures |
| Chunking and embedding | Selection trees, and the matrices behind each choice |
| Retrieval | BM25 internals, ANN index selection, hybrid fusion arithmetic, reranker comparison |
| Context | Token budgets, position sensitivity, provenance, long-context versus RAG |
| Evaluation | Metric-to-failure mapping, judge calibration, the release gate as a decision tree |
| Cost | Latency budgets, per-query unit economics, the cost levers matrix |
| Agentic | The search loop, and where it goes wrong |
| Enterprise | Permission-aware retrieval, index freshness, blue/green with atomic swap |
| Interview | Six scenario questions with what the panel is testing and the red flags |

## How it relates to everything else

The deck **teaches** the concepts. The [notebooks](../../notebooks/) make them produce a number.
The [case studies](../case-studies/) show the same concepts deciding real outcomes at other
companies. The [scenarios](../scenarios/) put you in the seat where you have to choose.

Read in that order if you are new: deck for the map, notebook for the mechanism, case study for
the consequence, scenario for the practice.

## Provenance

Authored in Claude Design and exported as a static bundle. Figures reported in the case-study
slides are as publicly reported by the companies concerned; where a figure could not be verified
the slide hedges it, and the written case studies in
[`../case-studies/`](../case-studies/) carry the citations.
