# ADR-0014 · Code published in documentation is executed by tests

- **Status:** Accepted
- **Date:** 2026-09-01
- **Deciders:** Maintainers
- **Related:** ADR-0006 (matplotlib diagrams), `tests/test_docs_code.py`

## Context

`docs/06-interview-prep/coding.md` publishes reference solutions — BM25, chunking with overlap,
RRF, an evaluation function — that a reader will memorise and reproduce at a whiteboard.

Prose examples rot. Nothing executes them, so an off-by-one introduced during an edit survives
indefinitely, and the failure mode is a candidate writing a subtly wrong `enumerate(ranking)`
in an interview because we published it that way.

## Decision

Every code block in the interview-prep documentation is extracted and executed by
`tests/test_docs_code.py`, with assertions on **the specific mistakes the surrounding prose warns
about**:

| Assertion | The mistake it catches |
|---|---|
| `df` from `set(d)`, not `Counter(d)` | Document frequency counting occurrences |
| A term in every document scores ≥ 0 | Missing Jeffreys prior → `log(0)` |
| Empty corpus returns `[]` | Division by zero on `avgdl` |
| `chunk` raises on `overlap >= size` | An infinite loop, not a slow chunker |
| RRF rank 1 scores `1/61 + 1/62` | `enumerate` starting at 0 |
| `full_chain@k` computed and `n` returned | A metric without its denominator |

The extraction is deliberately brittle in one direction: if the fences change or the file moves,
the test fails rather than silently passing over nothing.

## Options rejected

**Doctests.** Would put the assertions inside the published code, which changes what the reader
copies. The code in the docs should be what you would write, not what you would write plus test
scaffolding.

**Duplicate the code into `tests/` and check it matches.** Two copies that must be kept in sync,
which is the problem being solved rather than a solution to it.

**Trust review.** This is what was happening. Review catches obvious errors and does not catch
`enumerate` starting at zero, which is the entire class of bug at issue.

## Consequences

**Good.** A documented solution cannot silently rot. The assertions double as an executable
statement of what each warning in the prose means.

**Bad.** `exec` on documentation content, which is flagged by linters and is fine here because
it is our own file, read from a fixed path, executed deliberately. The `noqa` carries that
reasoning.

**Scope.** Applies to code that a reader is expected to reproduce. It does not apply to
illustrative fragments — a two-line snippet showing a config shape is not a reference solution
and testing it costs more than it returns. The distinction is whether the block is presented as
something that works.

## Generalisation

This is the third instance of one principle in this repository, and it is worth naming as such:

| Artefact | Checked by | Failure it prevents |
|---|---|---|
| Mermaid diagrams | `scripts/lint/check_mermaid.mjs` | Renders locally, breaks on GitHub |
| Relative links | `scripts/lint/check_links.py` | Silent 404 after a file moves |
| Documented code | `tests/test_docs_code.py` | Published solution rots |

**Documentation that makes a checkable claim should have the check.** Everything else in the docs
is prose and is reviewed as prose.
