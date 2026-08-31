# Contributing

Whether you are a student submitting an exercise or a maintainer adding a technique, the
workflow is the same — and the workflow is half of what this repository teaches.

## The one rule

> **Any change that could move a number ships with the number.**
> Before, after, delta, and a 95% interval from `metrics.paired_bootstrap`.
> A delta inside the noise band is reported as *inside the noise band*, not rounded into a win.

The PR template asks for this and the eval gate posts it automatically. A PR without it will be
asked for it before review, not after.

## Setup

```bash
git clone https://github.com/akash-coded/nanorag.git
cd nanorag
make setup
make test          # ~30 s
make notebooks     # ~10 min, executes all ten
```

Optional but recommended — a pre-commit hook that strips notebook outputs:

```bash
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
python scripts/strip_outputs.py
git add notebooks/*.ipynb 2>/dev/null || true
EOF
chmod +x .git/hooks/pre-commit
```

## Branch naming

| Prefix | For | Example |
|---|---|---|
| `exercise/` | Exercise submissions | `exercise/EX-14-priya` |
| `ext/` | An extension from EXTENSION-POINTS.md | `ext/hyde-retrieval` |
| `fix/` | Bug fixes | `fix/fts5-tokenizer-identifiers` |
| `docs/` | Documentation only | `docs/adr-0009-query-routing` |
| `chore/` | CI, deps, tooling | `chore/bump-numpy` |

## Commit messages

[Conventional Commits](https://www.conventionalcommits.org/). The scope is the module or the
notebook.

```
feat(retrieve): add HyDE query expansion behind seam ③

Generates a hypothetical answer and embeds that instead of the query.
Dense-leg evidence recall on the descriptor slice 0.44 → 0.51
[+0.04, +0.10], holds on frozen. Adds ~340 ms p50 and one generation
per query — off by default, enabled with cfg.hyde=True.

Closes #47
```

Types: `feat` `fix` `docs` `test` `perf` `refactor` `chore` `ci`.

**Put the number in the commit body.** Six months later `git log --grep=recall` is how someone
finds out when a metric moved and why.

## Before you open a PR

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] `make strip` run — CI rejects committed notebook outputs
- [ ] Notebooks still execute (`make notebooks`), or let CI prove it
- [ ] `python scripts/run_eval.py` output pasted into the PR body
- [ ] If a public number changed deliberately, `--baseline` re-run **in this PR**
- [ ] No credentials, keys, tenant data or client names anywhere in the diff

## What reviewers look for

In order:

1. **The measurement table.** Present, with intervals, and honest about deltas inside the
   noise band.
2. **One change.** A PR that adds a reranker *and* changes chunking cannot attribute either.
   Two PRs.
3. **The cost.** Latency, tokens, storage, or a second system to maintain. Every change has
   one; a PR that names none has not looked.
4. **Whether the frozen slice was respected.** Tuning against it, even once, invalidates it for
   everyone.
5. **Docs.** If behaviour changed, the doc that describes it changed too.

## Adding a new technique

Extensions plug into one of the ten [seams](docs/ARCHITECTURE.md#the-seams--where-to-plug-things-in).

1. Open an issue with a **falsifiable hypothesis** — which metric, on which slice, moving by
   how much, and why.
2. If it touches more than one seam, post it in
   [Discussions → Design Reviews](../../discussions/categories/design-reviews) first.
3. Implement behind the existing interface. Off by default if it costs latency or money.
4. Add a test. Extensions that cannot be tested cannot be maintained.
5. Measure on dev, verify on frozen, report both.
6. If it did not work: **say so and submit it anyway.** A clean negative result with a
   mechanism is a full-credit contribution and often more useful than a marginal win.

## Adding or changing a notebook

Notebooks are teaching artefacts, so they carry constraints code does not:

- **Flowchart before code, summary after.** A cell that computes without explaining what it is
  about to do breaks the rhythm the whole curriculum uses.
- **Every claim measured.** If a cell asserts something, the cell above it should have
  produced the number.
- **Runtime under ~3 minutes.** CI enforces 10 minutes as a hard limit; anything approaching
  it needs a subsample and a note saying so.
- **Outputs stripped** before commit.
- **Label stand-ins.** If something is simulated or injected, the surrounding markdown says
  so plainly.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not open a public issue for a vulnerability.

## Code of conduct

See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). The short version: assume good faith, critique
the work rather than the person, and remember that most people posting here are learning in
public — which takes more courage than posting a finished thing.
