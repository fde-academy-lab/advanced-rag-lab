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

**Bad — and this one is load-bearing.** LSA is roughly fifty years behind a modern encoder, and
it will not survive contact with a real embedding model on a real corpus. α must never be quoted
outside this corpus, and the README carries an explicit real-vs-stand-in table.

> **Corrected 2026-09-01 — see [ADR-0015](0015-correct-the-fusion-finding.md).** This section
> previously claimed LSA was *weaker than BM25* here and that equal-weight RRF therefore lost to
> BM25 alone. Re-measured, both are false. On this corpus LSA **beats** BM25 by +0.0616 evidence
> recall and +0.2416 nDCG, and RRF beats BM25 by +0.0624 — the fifty-year-old method is the
> stronger leg, because the questions are paraphrase and inference over prose where term overlap
> has almost nothing to score. The full table is in
> [`docs/09-research/measurements/fusion-rules.md`](../../09-research/measurements/fusion-rules.md).

What survives the correction is the argument for choosing LSA in the first place, and it is
strengthened rather than weakened: a stand-in that is *too weak to be interesting* would have
made every fusion lesson vacuous, and this one is strong enough to win.

We also had to fit LSA on *documents* rather than chunks — the association between a customer's
register and an engineer's register lives at document level, and fitting on fragments learns
nothing a bag of words would not.

**Revisit when:** a student has a GPU and wants to re-derive α with a real encoder. That is
EX-15, and the expected outcome is that α moves up and the hybrid story gets easier.
