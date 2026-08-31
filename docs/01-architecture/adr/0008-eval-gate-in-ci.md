# ADR-0008: Block merges on metric regressions with a CI gate

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

The curriculum's central claim is *build the measurement before the improvement*. A repository
that teaches that while merging changes without measuring them is not credible.

## Options considered

### Option A — trust the PR template
Ask for a measurement table and rely on reviewers.
**Costs:** reviewers do not run evaluations. The table gets filled in with a point estimate and
no interval, or left empty, and after three months nobody notices.

### Option B — report only, never block
Post a scorecard, let humans decide.
**Costs:** a warning everyone learns to scroll past. Also teaches that a gate is advisory,
which is the opposite of the section-6 lesson.

### Option C — a hard gate with a documented override

## Decision

Option C. `scripts/run_eval.py` compares against a committed baseline and exits non-zero on a
regression beyond tolerance. The workflow posts the scorecard on the PR either way. Re-baselining
is a deliberate act (`--baseline`) that must happen **in the same PR**, so the diff shows both
the change and the new numbers.

## Consequences

**Good.** A number that changes is visible in the PR without anyone running anything, which is
the single highest-leverage habit in the repo. Deliberate changes are possible but leave a
trace — the baseline diff is in the commit history, so "when did full-chain recall drop?"
is answerable by `git log`. Students experience a real release gate rather than reading about
one.

**Bad.** The gate is slower than the rest of CI (~2 minutes) and runs on every `nanorag/`
change. Tolerances (2–3 points) are judgement calls that will occasionally block a legitimate
change and occasionally let a small real regression through — they are a compromise between
false blocks and false passes, and we picked them by looking at the noise band rather than by
principle. And the baseline is a single committed file, so two PRs re-baselining concurrently
conflict; that is annoying and also correct, because they should not both be changing the
number silently.

**Revisit when:** the eval set grows enough that the noise band shrinks. Tolerances should
shrink with it, and someone has to remember to do that — which is itself an argument for
recording the noise band in the baseline file.
