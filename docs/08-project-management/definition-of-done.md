# Definition of done

A card leaves **In Review** when every line below is true. Not most. The list is short precisely
so that "most" is not a defensible position.

## For any change

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] Notebook outputs stripped (`make strip`) — CI rejects committed outputs
- [ ] No credentials, keys, tenant data or client names anywhere in the diff

## For a change that could move a number

- [ ] `python scripts/run_eval.py` output pasted into the PR body
- [ ] Before, after, delta **and a 95% interval** from `metrics.paired_bootstrap`
- [ ] A delta inside the noise band is described as inside the noise band
- [ ] The slice is named. "Overall" is a slice and must be said
- [ ] Frozen slice status stated: touched or not touched
- [ ] If a public number changed deliberately, `--baseline` re-run **in this PR** with the reason

## For a change that adds a component

- [ ] Measured **against removing it**, not only against its own previous version
- [ ] Its cost is named: latency, tokens, storage, or one more system to keep alive
- [ ] Off by default if it costs latency or money
- [ ] A test that would fail if it silently stopped working

That first line exists because of issue #4. A reranker was measured against earlier versions of
itself and looked like it was improving, while being worse than not having a reranker at all.
Evidence recall at k=5: 0.773 without, 0.630 with.

## For a documentation change

- [ ] Relative links resolve (`python scripts/lint/check_links.py .`)
- [ ] Mermaid renders under GitHub's settings (`npm run check:mermaid`)
- [ ] Any number quoted matches what the code currently produces
- [ ] Any code block that claims to work is executed by a test

## For a notebook change

- [ ] Executes clean end to end
- [ ] Runtime under ~3 minutes (CI hard limit 10)
- [ ] Flowchart before the code, summary after — the rhythm the curriculum uses throughout
- [ ] Every claim in the prose has a number produced by a cell above it
- [ ] Anything simulated or injected is labelled as such in the surrounding markdown

## What "done" explicitly does not require

Stated so nobody adds them informally:

- **Unanimous agreement.** A dissent recorded in the PR is a complete outcome. If it is
  architectural, it becomes an ADR.
- **A positive result.** A merged negative result with a mechanism is done, and is worth more
  than a marginal win.
- **Perfect test coverage.** Coverage of the invariant that would break, yes. Coverage as a
  percentage target, no.

## The one rule everything else follows

> **Any change that could move a number ships with the number.**

Everything above is that sentence, made specific enough to check.
