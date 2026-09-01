# Changelog

Notable changes, in the format of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project versions the **curriculum and the measured results**, not just the code — a change
that moves a published number is a change to the thing people cite, and it belongs here.

Every entry that moves a metric carries the interval. A delta inside the noise band is written as
inside the noise band.

## [Unreleased]

### Added
- Interview bank rebuilt as five topic files with scoring bands and transcript fragments:
  retrieval, evaluation, systems design, mathematics, coding, behavioural, plus four timed mock
  loops.
- `tests/test_docs_code.py` — the four reference solutions published in `coding.md` are executed
  with assertions on the specific mistakes the prose warns about (ADR-0014).
- `scripts/lint/check_mermaid.mjs` — parses every diagram under **GitHub's** renderer config
  rather than Mermaid's defaults, in CI.
- `scripts/lint/check_links.py` — resolves every relative link; skips the `../../discussions/…`
  form, which GitHub resolves against the repository.
- Multi-turn discussion engine: persona attribution, reply chains, accepted-answer marking.
- 27 seeded threads, 107 replies, 17 accepted answers across 11 categories.
- ADR-0009 through ADR-0014.
- `scripts/retarget.py` — repoints owner, repo and package name in one pass; round-trip is
  byte-identical.
- `.github/workflows/provision.yml` — provisions Discussions, the board and repository settings
  from the Actions tab, for environments that cannot reach GitHub's GraphQL API.

### Changed
- `docs/` restructured into ten numbered domains, each with an index. All 153 relative links
  rewritten and verified.
- Package renamed `fde_rag` → `nanorag`.
- Every seeded thread now carries a conversation. Nine previously had none.

### Fixed
- **168 HTML tags inside Mermaid node labels.** GitHub renders with `htmlLabels:false`; the
  library defaults to `true`, so eight diagrams parsed locally and broke on github.com.
- 18 unquoted Mermaid labels containing `( ) , : ;` — an unquoted parenthesis ends a label early.
- Six seeded discussion bodies used `../blob/main/…`, which 404s inside a Discussion because
  relative URLs there resolve against the discussion rather than the repository root.
- Four seeded threads marked an accepted answer in a category created as open discussion, which
  GitHub answers with an error rather than ignoring.
- `setup_github.py` resolved a project board owner via `organization(login:)`, failing on a user
  account. Now `repositoryOwner`, the interface both implement.
- `graphql()` raised whenever `errors` was present, discarding valid data returned alongside an
  expected miss.
- `push_repository` fell through to git's interactive prompt, which cannot succeed — GitHub
  stopped accepting account passwords in August 2021. Now authenticates via `GIT_ASKPASS`.

---

## [1.0.0] — 2026-08-31

First complete curriculum: ten notebooks, the toolkit, the evaluation harness, and the release
gate.

### Baseline results

| Metric | Value |
|---|---|
| `evidence_recall` | 0.7645 |
| `full_chain_recall` | 0.4686 |
| `answer_correct` | 0.4115 |
| `cost_usd` per run | 0.0039 |

### The three findings that contradict the received wisdom

Each names the condition under which the expected result returns. A negative result without that
is an anecdote.

1. **Equal-weight RRF loses to BM25 alone.** Weighted at α = 0.2 wins:
   evidence recall 0.7645 → 0.7891, [+0.008, +0.041], holds on frozen. Fusing a strong leg with a
   weak one at equal weight moves toward the weak one. Returns when the legs are comparable.
2. **Comparison starvation does not reproduce.** Prevalence ratio ≈ 1 by construction, so the
   precondition is absent. The finding is about eval sets: a balanced generator cannot measure
   imbalance failures.
3. **No retrieval-score threshold separates answerable from unanswerable questions.** Best F1
   0.38 across four signals. Null questions name real entities in the corpus's own vocabulary
   while genuine questions paraphrase, so the unanswerable ones are lexically *closer*.

### Defects found and fixed during the build

Each is a closed issue with its reproduction and fix.

| # | Defect | Effect |
|---|---|---|
| 1 | FTS5 default tokenizer split identifiers | identifier slice 0.81 → 0.34 |
| 2 | k-NN graph not navigable at scale | ANN recall → 0.00 at ef=64 |
| 3 | Gold resolution re-normalised all chunks per question | eval 4× slower |
| 4 | Reranker features were lexical-only over a fused list | recall 0.773 → 0.630 at k=5 |
| 5 | Documents too short for chunking to differ | every strategy scored the same |
| 6 | `decision_tree()` crashed on a default branch | `None` was a legitimate stored value |
| 7 | Abstention PR curve computed on a stratified subsample | null base rate 15% → 33%, F1 inflated to 0.69 |
| 8 | Exact search poisoned the ANN cache | graph silently never built |

Fixes: 1 → `tokenchars '_-'` (ADR-0013) · 2 → long-range links (ADR-0010) · 3 → memoised
normalisation, 40s → 9.7s byte-identical · 4 → semantic pair features, learned weights
(ADR-0005), +8 points · 7 → full-set sweep, best F1 0.38, matching the prose.
