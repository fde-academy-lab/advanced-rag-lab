## What this changes

<!-- One or two sentences. If it takes a paragraph, it is probably two PRs. -->

## Why

<!-- Link the issue: Closes #NNN. If there is no issue, say what prompted this. -->

Closes #

## Type

- [ ] Exercise submission (student)
- [ ] Bug fix
- [ ] New teaching content (notebook / doc / diagram)
- [ ] Toolkit change (`raglab/`)
- [ ] Infrastructure (CI, templates, board)

---

## Measurement

> **House rule:** any change that could move a number ships with the number.
> Run `python scripts/run_eval.py` and paste the output.

| Metric | Before | After | Δ | 95% CI | Verdict |
|---|---|---|---|---|---|
| Evidence Recall@k | | | | | |
| Full-chain recall | | | | | |
| Answer correctness | | | | | |
| Cost / query | | | | | |
| p95 latency | | | | | |

- **Noise band on this eval set:** ±____ (from `metrics.paired_bootstrap`)
- **Did the gain hold on the frozen slice?** yes / no / not applicable
- **If a delta is inside the noise band, say so here rather than rounding it away.**

<details>
<summary>Paste the <code>run_eval.py</code> output</summary>

```

```
</details>

## Checklist

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make strip` run — no notebook outputs committed
- [ ] Notebooks still execute clean (`make notebooks`), or CI proves it
- [ ] If a public number changed, `.github/eval-baseline.json` was re-baselined **in this PR**
- [ ] Docs updated if behaviour changed
- [ ] No credentials, keys, tenant data, or client names anywhere in the diff

## Reviewer notes

<!-- What should the reviewer look at hardest? Where are you least sure? -->
