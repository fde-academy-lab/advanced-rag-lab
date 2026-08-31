# 04 · Evaluation

The measurement is the product. Retrieval quality claims that arrive without a number, an
interval and a slice are opinions, and this folder is what turns them into results.

| File | What it answers |
|---|---|
| [metrics.md](metrics.md) | What each metric measures, what it misses, and when it lies |
| [protocol.md](protocol.md) | Dev/frozen split, sample sizes, what invalidates a run |
| [release-gate.md](release-gate.md) | How CI blocks a merge on a regression, and how to move a baseline honestly |

The one rule everything else follows: **any change that could move a number ships with the
number** — before, after, delta, and a 95% interval from `metrics.paired_bootstrap`.
