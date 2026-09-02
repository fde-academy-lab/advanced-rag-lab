# How to reproduce any number in the repository

**Takeaway:** every figure in the documentation has a command that regenerates it, and a test
that fails when the two drift. If you cannot find the command, that is a bug; open an issue.

| The number | Regenerate with | Guarded by |
|---|---|---|
| The baseline scorecard (evidence recall 0.7645, full-chain 0.4686, and the rest) | `python scripts/run_eval.py` | `.github/eval-baseline.json`, the eval gate on every pull request |
| The fusion table (bm25 0.7118, dense 0.7733, rrf 0.7742, weighted 0.7790 at α=0.5) | `python scripts/run_eval.py --compare` | `tests/test_measurements.py` |
| The α sweep | `python scripts/run_eval.py --sweep` | same |
| The k grid (precision falls 0.3029 to 0.1948 from k=5 to k=10 on the BM25 arm) | `python scripts/run_eval.py --ksweep` | same, and drill `XD1` |
| Failure overlap between legs (0.9684 without personas) | `python scripts/failure_overlap.py` | same, and drill `RD2` |
| Independence of the two recalls (+0.0083) | `python scripts/independence.py` | same |

1. Open a Codespace on the repository (see [Codespaces](How-To-Use-Codespaces.md)).
2. Run the command from the table. Ten seconds for the scorecard; a minute for the sweeps.
3. Compare with the note that quotes it, under
   [docs/09-research/measurements](https://github.com/fde-academy-lab/advanced-rag-lab/tree/main/docs/09-research/measurements).

**Done when:** your terminal and the note agree to four decimals. If they do not, the note is
wrong and `pytest tests/test_measurements.py` will say so; open an issue with both numbers.

Why this matters: the retracted fusion finding stood for months in eleven files because the
numbers had been typed, not generated. The rule that fixed it is the table above.
