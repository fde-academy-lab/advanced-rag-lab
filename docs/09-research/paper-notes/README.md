# Paper notes

Structured notes, one per paper. The format is fixed because the useful part is not the summary —
it is **what replicated here and what did not**, and that only becomes comparable if every note
answers the same questions.

| Note | Paper | Replicated on Client Zero? |
|---|---|---|
| [lost-in-the-middle.md](lost-in-the-middle.md) | Liu et al., 2023 — *Lost in the Middle* | Direction consistent, amplitude inside the noise band |
| [rrf.md](rrf.md) | Cormack et al., 2009 — *Reciprocal Rank Fusion* | **No** — equal-weight RRF loses to BM25 alone here |

## The format

Six headings, always:

1. **Claim** — one sentence, in the paper's own terms.
2. **Method** — enough to know whether their setup resembles yours.
3. **What we tested** — the specific experiment, on this corpus.
4. **Result** — with an interval. "Consistent in direction" is a legitimate outcome and so is
   "underpowered, cannot confirm or refute".
5. **Why it did or did not transfer** — the mechanism, or the missing precondition.
6. **What would change the answer** — the corpus property or scale at which the paper's result
   would hold here.

Heading 6 is the one that stops a negative note being a dismissal. A paper that does not
replicate on a synthetic 484-document corpus has not been refuted; a precondition is absent, and
naming it is the finding.

## The rule

**Reading a paper produces a number, not a summary.** A note without an experiment against this
corpus is a book report, and it is not what Reading Club is for.
