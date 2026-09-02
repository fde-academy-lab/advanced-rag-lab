# XD1 · solution

| k | evidence_recall | context_precision |
|---|---|---|
| 5 | 0.6329 | 0.3029 |
| 10 | 0.7279 | **0.1948** |

Precision **falls** and recall **rises**, and they must: the denominator of precision is `k`, a
number you chose, and the gold set for a question is fixed. Doubling the slots roughly halves
the share of them that carry gold.

**The gate is cleared by lowering k.** "Context precision above 0.30" is passed at k=5 and
failed at k=10 with retrieval untouched. That is a gate a config flag can pass and a system
change cannot — which is why this repository reports `context_precision` beside recall as a
*budget-efficiency* number and never gates on it alone.

`python scripts/run_eval.py --ksweep` · docs/04-evaluation/metrics.md
