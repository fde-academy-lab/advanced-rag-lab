# Measurement · Which fusion rule, and does fusion pay at all

- **Date** 2026-09-01
- **Command** `python scripts/run_eval.py --compare` for the table;
  `python scripts/failure_overlap.py` for the diagnostic that explains it
- **Configuration** `structural` chunking, `n=100` candidates, cross-encoder rerank, `k=8`
- **Set** 243 questions, 207 answerable; paired bootstrap over questions, 2000 resamples
- **Supersedes** the fusion claims in ADR-0003 and ADR-0007 as originally written. See
  [ADR-0015](../../01-architecture/adr/0015-correct-the-fusion-finding.md).

---

## The table

```
configuration       evidence_recall  full_chain_recall               ndcg     answer_correct
--------------------------------------------------------------------------------------------
bm25                         0.7118             0.4348             0.3639             0.4156
dense                        0.7733             0.4638             0.6055             0.3992
rrf                          0.7742             0.4638             0.5302             0.4033
w0.2                         0.7645             0.4686             0.4767             0.4115
w0.5                         0.7790             0.4686             0.5967             0.3992
```

`alpha` is the **dense** weight, so `w0.2` is one fifth dense and four fifths lexical.
`w0.2` is `raglab.TUNED` and the configuration `.github/eval-baseline.json` is cut from.

## What the intervals say

Deltas are **second arm minus first**, matching `metrics.paired_bootstrap(a, b)`.

| Comparison | Metric | Delta | 95% interval | Verdict |
|---|---|---|---|---|
| bm25 → rrf | evidence recall | +0.0624 | (+0.0407, +0.0857) | real |
| bm25 → rrf | nDCG | +0.1663 | (+0.1362, +0.1976) | real |
| bm25 → dense | evidence recall | +0.0616 | (+0.0382, +0.0870) | real |
| bm25 → dense | nDCG | +0.2416 | (+0.1975, +0.2869) | real |
| **dense → rrf** | **evidence recall** | **+0.0008** | **(−0.0101, +0.0109)** | **inside the noise band** |
| **dense → rrf** | **nDCG** | **−0.0753** | **(−0.1061, −0.0462)** | **regression** |
| rrf → w0.2 | nDCG | −0.0535 | (−0.0776, −0.0295) | regression |
| rrf → w0.5 | evidence recall | +0.0048 | (−0.0024, +0.0145) | inside the noise band |
| w0.2 → w0.5 | evidence recall | +0.0145 | (+0.0048, +0.0254) | real |
| w0.2 → w0.5 | nDCG | +0.1200 | (+0.0958, +0.1445) | real |
| **every pair** | **answer correct** | | | **inside the noise band** |

## Three findings

### 1 · BM25 is the weak leg here, not the dense one

LSA — a truncated SVD over TF-IDF, fifty years old — beats BM25 by **+0.062** evidence recall
and **+0.242** nDCG, both with intervals well clear of zero.

The mechanism is the corpus, not the method. Client Zero's questions are largely paraphrase and
inference over incident prose, where the question and the passage share meaning and almost no
vocabulary. BM25 scores term overlap. It has nothing to score.

Where BM25 wins is exact identifiers — `PagerDuty-4471`, `ap-southeast-2`, `RB-118` — which are
out-of-vocabulary for a latent model and matched exactly by a lexical one. That slice is real and
it is small. Aggregate numbers hide it in both directions, which is the argument for
`metrics.slice_report`.

### 2 · Fusion does not separate from its better single leg

`dense → rrf` is **+0.0008** evidence recall with an interval straddling zero, and on nDCG the
**unfused dense leg wins outright** by 0.075.

Fusion here means a second index, a second pipeline, a fusion rule, and — for weighted — a
normalisation choice and a constant refitted per corpus. The measured return on all of that is
indistinguishable from zero, and on ranking quality it is negative.

This contradicts the folk rule and it contradicts the deck's matrix. Both are priors formed on
corpora where the legs are complementary. The question a matrix cannot answer is whether *your*
legs fail on different queries, and the diagnostic for it is the per-query overlap of failures —
which nobody ran before choosing. That is a finding about the evaluation rather than about
fusion, and it is the more valuable half.

#### The diagnostic, measured

The overlap argument above was made in prose for months before anyone computed it. It is one
command:

```
python scripts/failure_overlap.py

  207 answerable questions, k=8, n_candidates=100, rerank=cross

    dense leg misses                95
    lexical leg misses             102
    both miss                       92
    only dense misses                3   ← questions fusion could recover from the lexical leg
    only lexical misses             10   ← and from the dense leg

    P(lexical also misses | dense misses)   0.9684
    Jaccard of the two failure sets         0.8762
```

**Thirteen questions in 207 are recoverable by fusion at all**, and only three of them in the
direction people assume. That is the entire budget the merge is competing for, and it explains
the +0.0008 above without appealing to anything.

The conditional is the quantity that answers the question; the Jaccard is the plausible wrong
formula and is printed beside it deliberately, because they are close enough to be mistaken for
one another. R3 grades against exactly this, with the bar placed between the two values so a
wrong formula fails on a real number rather than on a style check.

Run with `--with-personas` for the same quantity through the shipped pipeline, ACL filter
included: 111 / 117 / 110, conditional **0.9910**. The filter removes reachable evidence, so both
legs miss more and miss it together. The conclusion does not depend on which of the two you take,
which is the useful part.

### 3 · No retrieval configuration moves answer correctness

Evidence recall spans 0.7118 → 0.7790 across these arms — a real 9.4% relative improvement, three
of the comparisons statistically solid. `answer_correct` spans 0.3992 → 0.4156 and **every
pairwise comparison on it is inside the noise band**. The numerically best answers come from the
numerically worst retriever.

The system is **generation-limited, not retrieval-limited**. That was already visible in the
0.4686 → 0.4115 gap between full-chain recall and answer correctness and nobody joined it up: at
k=8 the evidence is present for 47% of questions and the answer is right for 41%, so the last
six points are the generator, and the 67 points below that are the chain.

Consequences worth stating plainly:

- Retrieval work on this corpus is close to exhausted as a lever on the metric the customer
  feels. Further recall is not free and buys nothing measurable downstream.
- `evidence_recall` is the right gate metric for *catching regressions* and the wrong metric for
  *justifying a roadmap*, because it moves when nothing the user experiences does.
- The next real gain is in the generator and the packing — position, budget, abstention — not in
  the retriever. That is where notebook 05 and the cost track point.

## What this does not say

It does not say hybrid retrieval is a bad idea, or that BM25 is obsolete, or that RRF is wrong.
It says that **on this corpus, with this dense encoder and this question mix**, the fused
configurations are inside the noise band of the better single leg.

Change any of those three and the answer can flip. The condition under which the textbook result
returns is a dense leg and a lexical leg that fail on *different* queries — and the way to know
is to measure the overlap, not to consult a matrix. `EX-15` is that experiment with a real
sentence encoder, and the expected outcome is that the legs become complementary and fusion
starts paying.

## Reproducing it

```bash
python scripts/run_eval.py --compare              # this table, ~2 minutes
python scripts/run_eval.py --fusion dense         # one arm
python scripts/run_eval.py --fusion weighted --alpha 0.5
```

Nothing here needs a network, a key or a download.
