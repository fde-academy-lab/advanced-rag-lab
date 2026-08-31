# ADR-0002: Generate the corpus from a fact graph rather than download MultiHop-RAG

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

The curriculum teaches measurement. Every number a student reads has to be trustworthy, and
every failure mode the deck describes has to actually *fire* so it can be measured rather than
described.

## Options considered

### Option A — download MultiHop-RAG
The real dataset, 2,556 questions, human-annotated evidence.
**Costs:** a ~200 MB download, so the notebook is no longer one-click. Human annotation means
an annotation-error floor under every number — you cannot tell a retrieval miss from a bad
label. And crucially, it contains whatever failure modes it happens to contain: there is no
guarantee it exercises the lexical gap, the identifier miss, ACL leakage or temporal ordering.

### Option B — scrape a public corpus
Wikipedia, news archives.
**Costs:** licensing ambiguity, no gold labels at all, and the same coverage problem.

### Option C — generate from a fact graph
Twenty-four organisations, six quarters of results, acquisitions, incidents, launches,
funding, regulatory determinations, and market commentary. Documents rendered from the graph;
questions generated from the same graph.

## Decision

Option C, with `corpus.load_multihop_rag()` as a first-class path for anyone who has the real
files.

## Consequences

**Good.** Gold evidence is true *by construction* — no annotation-error floor. Every failure
mode in the deck is built in on purpose: a lexical gap between "retry delay" and "backoff
interval" that a glossary document bridges, identifiers that appear in exactly one document,
two-hop chains, deliberate distractors, ACL-restricted documents, and null questions the corpus
genuinely cannot answer. The corpus can be scaled to whatever size the lesson needs — and it
had to be, twice: first because 71-word documents made every chunking strategy degenerate, then
because N=100 over 230 chunks is a full scan wearing a costume.

**Bad.** External validity. The absolute numbers do not transfer to a real corpus, and a
student who quotes them in a client meeting has misused them — which is why notebook 00 prints
an explicit real-vs-stand-in inventory and the README repeats it. The corpus is also *balanced
by construction*, which is why the deck's comparison-starvation failure does not reproduce
(notebook 02 reports this rather than engineering around it).

**Revisit when:** a cohort needs to work on a real client corpus. At that point the generator
becomes the *template* for manufacturing their eval set — which is notebook 02's actual lesson.
