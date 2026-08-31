# ADR-0003: Ship LSA as the default encoder, not a neural model

- **Status:** Accepted
- **Date:** 2026-08-31
- **Deciders:** Maintainers

## Context

Dense retrieval has to be *real* — a mocked encoder teaches nothing. But
`sentence-transformers` pulls PyTorch and downloads a model, which breaks the one-click
promise and adds a gigabyte to the setup.

## Options considered

### Option A — sentence-transformers/all-MiniLM-L6-v2
A genuinely good small encoder.
**Costs:** ~90 MB model download plus ~800 MB of PyTorch, non-deterministic across hardware
without pinning, and slow enough on CPU that the sweeps in notebook 04 become a coffee break.

### Option B — a mocked/random encoder
Fast and dependency-free.
**Costs:** dishonest. Every dense-retrieval number becomes meaningless, and a student who
notices would be right to distrust the whole curriculum.

### Option C — latent semantic analysis
TF-IDF over the corpus, then a truncated SVD. The original dense retrieval method.

## Decision

Option C as the default, with `SentenceTransformersEmbedder` and `BedrockEmbedder` implemented
behind the same interface.

## Consequences

**Good.** It is *genuinely* dense retrieval — it bridges paraphrase through co-occurrence, and
it demonstrates real properties: the cosine/dot-product identity after L2 normalisation, the
dimension/generalisation tradeoff (notebook 04 measures the paraphrase slice peaking at a lower
dimension than the exact-match slice), prefix asymmetry, and mixed-version index corruption.
It fits in 300 lines that a student can read. It is deterministic and fits in milliseconds.

**Bad — and this one is load-bearing.** LSA is roughly fifty years behind a modern encoder,
and on this corpus it is *weaker than BM25*. That produced a finding that contradicts the folk
rule: equal-weight RRF loses to BM25 alone here, because fusing a strong retriever with a weak
one at equal weight moves you toward the weak one. We chose to **report that rather than
engineer around it**, with the mechanism explained and the condition under which the expected
result returns (ADR-0007). Two consequences follow: the README carries an explicit
real-vs-stand-in table, and α=0.2 must never be quoted outside this corpus.

We also had to fit LSA on *documents* rather than chunks — the association between a customer's
register and an engineer's register lives at document level, and fitting on fragments learns
nothing a bag of words would not.

**Revisit when:** a student has a GPU and wants to re-derive α with a real encoder. That is
EX-15, and the expected outcome is that α moves up and the hybrid story gets easier.
