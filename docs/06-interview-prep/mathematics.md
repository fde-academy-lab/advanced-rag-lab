# Mathematics

The derivations a strong candidate can produce at a whiteboard. Panels at Google, Palantir,
Anthropic and the quant-adjacent shops ask these not to check whether you memorised a formula
but to see whether you know *why the formula has the shape it has* — because that is what
tells you when it stops working.

Each question below gives the ask, the derivation, the thing the interviewer is actually
listening for, and the follow-up that separates a mid-level answer from a senior one.

**Grading scale used throughout:** *misses* · *passes a screen* · *hires at mid* · *hires at senior*.

---

## M1 · Derive BM25's term-frequency saturation. Why not raw `tf`?

**Asked at:** Google (Search), Elastic, Palantir. Almost always the opener for a retrieval role.

### The derivation

Start from the Robertson–Spärck Jones weight. For a term $t$, under a binary independence
model with relevance $R$, the log-odds contribution of observing $t$ is

$$w_t = \log \frac{p_t(1-q_t)}{q_t(1-p_t)}$$

where $p_t = P(t \mid \text{relevant})$ and $q_t = P(t \mid \text{non-relevant})$. With no
relevance judgements, estimate $q_t \approx n_t/N$ ($n_t$ documents contain $t$, $N$ total)
and $p_t$ as a constant. That collapses to the familiar

$$\mathrm{IDF}(t) = \log\frac{N - n_t + 0.5}{n_t + 0.5}$$

The $+0.5$ terms are not decoration. They are the Jeffreys prior — a $\mathrm{Beta}(½,½)$
smoothing that keeps the estimate finite when $n_t = 0$ or $n_t = N$. Without them a term
appearing in every document produces $\log 0 = -\infty$.

Now the term-frequency part. Raw $tf$ assumes the tenth occurrence of "latency" carries the
same evidence as the first. It does not: relevance is roughly a saturating function of
occurrence. The classic 2-Poisson model says a document is drawn from either an "elite"
distribution for $t$ or a background one, and the log-likelihood ratio between them is
approximately

$$\frac{tf}{tf + k_1}$$

which is a hyperbola: it rises steeply at first, then flattens. Multiply by $(k_1 + 1)$ to
normalise the first occurrence to weight 1, and add length normalisation:

$$\text{BM25}(q,d) = \sum_{t \in q} \mathrm{IDF}(t) \cdot
\frac{tf_{t,d}\,(k_1+1)}{tf_{t,d} + k_1\left(1 - b + b\frac{|d|}{\text{avgdl}}\right)}$$

### What each knob does

| Parameter | Effect | Typical | What breaks at the extreme |
|---|---|---|---|
| $k_1$ | Saturation rate | 1.2 – 2.0 | $k_1 \to 0$: binary presence, `tf` ignored entirely. $k_1 \to \infty$: linear `tf`, long spammy docs win |
| $b$ | Length normalisation strength | 0.75 | $b = 0$: no normalisation, long documents dominate. $b = 1$: full, short documents dominate and a 3000-word reference page can never rank |

### What the interviewer is listening for

That you know saturation is a *modelling choice about evidence*, not a hack. The tell of a
weak answer is describing $k_1$ as "a tuning parameter" without saying what it models.

### The follow-up that separates levels

> *"Your corpus is API documentation. Median document 4,000 words, but 15% are 80-word error-code stubs that are the correct answer for error queries. What do you do with `b`?"*

**Hires at senior:** lower `b` (toward 0.3–0.5), because full length normalisation actively
penalises the long reference pages *and* the stubs are already short enough to win on `tf`
density alone — you are normalising a distribution that is bimodal, and a single `b` cannot
serve both modes. Then say the real fix: **stop pretending it is one corpus.** Index the stubs
and the prose as separate fields with separate normalisation (BM25F), or route by query class.
Then say how you would know you were right: error-code queries as their own eval slice, with
Recall@10 before and after and a paired bootstrap interval.

**Hires at mid:** lowers `b`, explains why, stops there.

**Passes a screen:** knows `b` controls length normalisation.

---

## M2 · Why does Reciprocal Rank Fusion use `1/(k + rank)` and not the scores?

**Asked at:** Anthropic, Cohere, any team that has been burned by fusing a BM25 score with a
cosine similarity.

### The derivation

$$\text{RRF}(d) = \sum_{i \in \text{systems}} \frac{1}{k + r_i(d)}$$

with $k \approx 60$ conventionally, $r_i(d)$ the rank of $d$ in system $i$.

The point is what it *refuses* to use. BM25 scores are unbounded sums of log-odds; cosine
similarities live in $[-1, 1]$; a cross-encoder emits logits. These are not on a common scale,
not even monotonically related, and their distributions differ per query. Any weighted sum of
raw scores is therefore dominated by whichever system happens to have the larger variance on
that query — a property of the scoring function, not of relevance.

Ranks discard the scale and keep only the ordering, which is the part every system agrees is
meaningful. The $1/(k+r)$ shape is a discount that is steep at the top and flat in the tail:

- $r = 1 \to 1/61 = 0.0164$
- $r = 2 \to 1/62 = 0.0161$ (a 2% drop)
- $r = 100 \to 1/160 = 0.00625$

The $k$ is a **dampener on the top rank's authority**. At $k=0$, rank 1 scores 1.0 and rank 2
scores 0.5 — one system's top hit can never be outvoted. At $k=60$ the gap between ranks 1 and
2 is 2%, so agreement across systems outranks confidence within one. That is the entire design
intent: RRF is a voting rule, and $k$ sets how much a single voter's first preference counts.

### The measured result in this repository, which contradicts the folklore

RRF works exactly as Cormack advertises — and the whole exercise was inside the noise band of one
of its own legs. Evidence Recall@8, 243 questions, paired bootstrap:

| Configuration | Evidence recall@8 | nDCG@8 |
|---|---|---|
| BM25 alone | 0.7118 | 0.3639 |
| Dense (LSA) alone | 0.7733 | **0.6055** |
| Equal-weight RRF | **0.7742** | 0.5302 |
| Weighted, $\alpha = 0.2$ | 0.7645 | 0.4767 |

RRF beats BM25 by $+0.0624$, ci $(+0.0407, +0.0857)$, and beats the tuned weighted rule on nDCG
by $0.0535$ — the parameter-free rule wins against the parameterised one, which is the paper's
claim. But `dense → rrf` is $+0.0008$ with ci $(-0.0101, +0.0109)$, and on nDCG the *unfused*
dense leg wins by $0.0753$.

The mechanism is **complementarity, not comparable strength.** Fusion turns two signals into a
better one only when the legs fail on different queries; two retrievers that fail together carry
one signal between them. Cormack's setup is fusion over TREC runs — mature systems that are good
in *different ways*. On this corpus the legs are not: the questions are paraphrase and inference
over prose, the dense leg handles nearly all of it, and BM25 contributes on the exact-identifier
slice, which is real and small.

**Saying this in an interview is a strong move**, provided you give the condition under which the
expected result returns — complementary legs — and name the diagnostic that would have told you
in advance: the per-query overlap of failures between the legs, which nobody ran before choosing.

> **This section was itself wrong until 2026-09-01.** It read *"equal-weight RRF loses to BM25
> alone; BM25 0.7645"* — RRF in fact wins, the dense leg is the stronger of the two, and 0.7645
> is the tuned configuration's number mis-attributed to BM25. See
> [ADR-0015](../01-architecture/adr/0015-correct-the-fusion-finding.md). If you quoted the old
> version in an interview, the recovery is the better story: the reason it survived is that the
> eval gate compares a configuration against its own history and never against alternatives.

### The follow-up

> *"Give me a case where RRF beats a tuned weighted sum."*

When the score distributions are non-stationary across queries — a hybrid over a corpus with
mixed languages or wildly varying document lengths, where BM25's scale shifts per query but its
*ordering* stays sound. A global $\alpha$ tuned on average behaviour is then wrong on every
individual query, and rank-based fusion is robust to exactly that.

---

## M3 · Derive nDCG. Why the logarithmic discount specifically?

**Asked at:** Google, Amazon Search, LinkedIn.

### The derivation

Cumulative Gain at $k$: $\ \mathrm{CG}@k = \sum_{i=1}^{k} rel_i$. It ignores position entirely,
so a correct answer at rank 10 counts the same as at rank 1. Fix that with a discount:

$$\mathrm{DCG}@k = \sum_{i=1}^{k} \frac{rel_i}{\log_2(i+1)}$$

(the graded variant uses $2^{rel_i} - 1$ in the numerator, which sharpens the reward for highly
relevant documents).

**Why $\log_2(i+1)$ and not $1/i$?** Two reasons, and a senior answer gives both.

1. *Empirical.* User examination probability decays roughly logarithmically with rank over the
   first page. $1/i$ decays far too fast: it says rank 2 is worth half of rank 1, which
   overstates the penalty for a near-miss.
2. *Mathematical.* Järvelin and Kekäläinen's original argument is that the discount should be
   smooth and *slowly* decaying so the measure remains sensitive deep in the list. The $+1$
   inside the log is there so that rank 1 gives $\log_2 2 = 1$, i.e. no discount, keeping the
   top position at full gain.

Normalise by the best achievable ordering:

$$\mathrm{nDCG}@k = \frac{\mathrm{DCG}@k}{\mathrm{IDCG}@k}$$

IDCG is the DCG of the ideal ranking — all relevant documents sorted by descending relevance.
Normalisation is what makes nDCG comparable across queries with different numbers of relevant
documents; without it, a query with 10 relevant documents dominates one with 2.

### Where it misleads, which is the real question

**nDCG is computed against the judgements you have.** If your gold set marks 3 documents
relevant and the corpus contains 9, the IDCG is computed over 3, and a system that surfaces the
6 unjudged ones is punished for being right. This is the *pooling bias* problem, and it is why
nDCG numbers are not comparable across differently-annotated corpora — a fact people quote
across papers constantly and incorrectly.

Second failure: nDCG is insensitive to whether the retrieved set is *sufficient*. A query whose
answer requires combining two documents can score nDCG 0.85 by retrieving one of them at rank 1
and nine near-duplicates. That is the reason this repository reports **full-chain recall**
alongside it — the fraction of questions where *every* required piece of evidence made the
window. Evidence Recall@8 here is 0.7645 while full-chain recall is 0.4686, and the gap between
those two numbers is the entire multi-hop problem stated numerically.

### The follow-up

> *"Your nDCG@10 went from 0.71 to 0.74. Ship it?"*

Not yet. Three questions first. What is the paired bootstrap interval — if it is
$[-0.01, +0.07]$ the effect is inside the noise band and you have measured nothing. Which
slice moved — a uniform lift and a lift confined to the head are different products. And did
anything else move down: nDCG is an average, and averages hide a metric being robbed to pay
another.

---

## M4 · Why does a k-NN graph fail as an ANN index, and what fixes it?

**Asked at:** Palantir, Pinecone, Weaviate, and anyone who has read the HNSW paper.

### The failure

Build a graph where each node links to its $k$ nearest neighbours. Greedy search from an entry
point, moving to whichever neighbour is closer to the query, stopping at a local minimum.

This has a **diameter problem**. A pure k-NN graph is a lattice of tight, locally-dense
neighbourhoods. Every edge is short. To travel from one region of the space to a distant one
you must traverse $O(n^{1/d})$ short edges, and greedy search terminates at the first local
minimum long before it gets there. Recall collapses — measurably. In this repository, after the
corpus grew to 484 documents and 2,430 chunks, ANN recall at $ef = 64$ went to **0.00**. Not
degraded: zero. Every search terminated in the neighbourhood it started in.

### The fix, and the theory under it

Add **long-range links**. This is Kleinberg's small-world result (2000): a lattice augmented
with random long-range contacts drawn with probability proportional to $d(u,v)^{-\alpha}$ is
navigable by a decentralised greedy algorithm in $O(\log^2 n)$ steps — and *only* when
$\alpha$ equals the lattice dimension. Too few long links and you are back to the lattice; too
many and greedy routing has no gradient to follow because every step looks equally good.

The implementation here adds 4 random long-range links per node:

```python
rng = np.random.RandomState(17)
longr = rng.randint(0, n, size=(n, min(4, max(1, n - 1))))
entry["graph"] = np.concatenate([near, longr], axis=1)
```

That is the "navigable" half of *navigable small world*, and it is the half people drop when
they implement it from memory.

HNSW extends this with a hierarchy: exponentially-decaying layer membership, so upper layers
are sparse long-range graphs used for coarse routing and the base layer is dense for the final
descent. Same principle, organised rather than random.

### The follow-up

> *"Your recall@10 against exact search is 0.94 and you need 0.99. What do you turn?"*

`ef_search` first — it is a query-time knob, costs latency only, and needs no rebuild. Measure
the recall/latency curve rather than picking a value. If latency budget is exhausted, `M`
(edges per node) at build time, which costs memory and build time permanently. Then the
question nobody asks: check whether the 6% miss is *uniform or clustered*. Clustered misses
mean a region of the embedding space is poorly connected, and no amount of `ef` fixes a graph
that is disconnected there.

---

## M5 · Cohen's kappa is 0.31 but the annotators agree 85% of the time. Explain.

**Asked at:** Anthropic, Scale, Surge, any team building an LLM judge.

### The derivation

$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

$p_o$ is observed agreement; $p_e$ is agreement expected by chance given each rater's marginal
distribution. For two raters over classes $c$:

$$p_e = \sum_c P(\text{A picks } c)\,P(\text{B picks } c)$$

### The resolution

This is the **prevalence problem**, and it is the correct answer to the question.

Suppose 90% of items are "relevant" and both raters say "relevant" 90% of the time. Then

$$p_e = 0.9 \times 0.9 + 0.1 \times 0.1 = 0.82$$

With $p_o = 0.85$:

$$\kappa = \frac{0.85 - 0.82}{1 - 0.82} = \frac{0.03}{0.18} = 0.167$$

85% agreement, κ near zero. The raters agree, but almost entirely by both following the base
rate. κ is asking a harder question than "do you agree" — it asks "do you agree *more than two
people who had never looked at the items but knew the base rate*". On a skewed label
distribution the answer is usually "barely".

### What to do about it

1. **Report both.** κ alone on a skewed set is uninterpretable; $p_o$ alone is misleading.
2. **Balance the annotation sample.** Stratify so the label distribution is closer to uniform,
   then κ measures what you meant it to.
3. **Use a different statistic when prevalence is inherent** — Gwet's AC1 is explicitly
   designed to be stable under skew; Krippendorff's α handles more than two raters and missing
   data.
4. **Look at the confusion matrix.** κ compresses a 2×2 table to one number; the disagreement
   is almost always concentrated in one cell, and that cell tells you which rubric line is
   ambiguous.

### The follow-up that catches people

> *"Your LLM judge agrees with humans at κ = 0.62. Is that good enough to gate a release?"*

It depends entirely on **what the disagreement is made of**. κ = 0.62 with disagreement spread
evenly is a judge with noise, and noise averages out over a few hundred examples — usable for a
gate. κ = 0.62 with disagreement concentrated on one class — say, the judge marks abstentions
as wrong answers — is a judge with *bias*, and bias does not average out. It systematically
moves the number your gate is reading. Same κ, opposite decisions. Then: the judge should be
calibrated on a frozen human-labelled slice that is never used for tuning, and the gate should
trip on the judge's *disagreement rate with itself* across reruns, which catches drift a single
κ never will.

---

## M6 · Why a *paired* bootstrap, and what exactly is being resampled?

**Asked at:** Google, Meta, any team with a ranking release gate.

### The derivation

You have systems A and B evaluated on the same $n$ queries, with per-query scores
$a_i, b_i$. You want a confidence interval on the mean difference $\bar{d}$ where
$d_i = a_i - b_i$.

Procedure: for $B$ iterations (typically 1,000–10,000), sample $n$ queries **with replacement**,
recompute $\bar{d}^{(b)}$ on that resample, and take the 2.5th and 97.5th percentiles of the
$B$ values as a 95% interval.

**Why paired.** Query difficulty varies enormously — some queries are easy for every system and
some are hopeless for all of them. That between-query variance is typically much larger than the
between-system variance you care about. Pairing removes it entirely: you resample the
*differences*, so a query that both systems ace contributes $d_i = 0$ and adds no variance. An
unpaired comparison of two means on the same query set throws that away and produces intervals
several times wider, which is how a real improvement gets declared insignificant.

**Why resample queries and not documents.** The unit of independence is the query. Documents
within a query's result list are not independent — they were selected by the same retriever.
Resampling documents would understate variance and produce intervals that are too narrow, which
is the more dangerous error.

### The senior-level caveat

The bootstrap estimates variance **due to query sampling**. It says nothing about:

- **Annotation error** — if your gold labels are wrong, every resample is wrong the same way.
  (This repository sidesteps that: gold evidence is true by construction because the corpus is
  generated from a fact graph, so there is no annotation-error floor under any number.)
- **Multiple comparisons** — test twenty variants at 95% and one will clear by chance. Correct
  for it, or hold out a frozen slice you touch exactly once.
- **Non-stationarity** — the interval assumes your query sample represents production traffic.
  It usually does not.

### The follow-up

> *"Interval is [+0.001, +0.09]. It excludes zero. Ship?"*

Statistically significant, practically ambiguous — the interval spans "invisible" to "large",
so you have established direction but not magnitude. That is a reason to gather more queries,
not to ship. And significance is not the shipping criterion anyway: ask what the change costs
in latency, in tokens, in one more system to keep alive. A +0.5% recall that adds 340ms p50 is
a regression wearing a win's clothing.

---

## M7 · Prove that truncated SVD gives the optimal rank-k approximation. Why does that matter for LSA?

**Asked at:** Palantir, quant shops, ML-heavy panels.

### The statement

For $A \in \mathbb{R}^{m \times n}$ with SVD $A = U\Sigma V^\top$, let $A_k = U_k \Sigma_k V_k^\top$
keep the $k$ largest singular values. **Eckart–Young–Mirsky:** for any matrix $B$ of rank $\le k$,

$$\|A - A_k\|_F \le \|A - B\|_F$$

and the same holds in the spectral norm. The error is exactly
$\|A - A_k\|_F^2 = \sum_{i>k} \sigma_i^2$.

**Sketch of why.** The Frobenius norm is unitarily invariant, so minimising $\|A - B\|_F$ is
equivalent to minimising in the basis where $A$ is diagonal. There the problem separates into
choosing which $k$ diagonal entries to keep, and keeping the largest is optimal by inspection.

### Why it matters here

LSA is truncated SVD on a TF-IDF matrix. Eckart–Young says the $k$-dimensional space you get is
the best possible linear compression *in reconstruction error*. It does **not** say it is the
best space for retrieval — reconstruction error is not relevance. That distinction is the whole
answer to "why are learned embeddings better than LSA", and it is the sentence most candidates
cannot produce.

### The implementation detail worth mentioning

In this repository the latent space is fitted **on whole documents** and chunks are then encoded
into it:

```python
emb = embed.LsaEmbedder(dim=dim).fit([d.title + "\n" + d.body for d in bundle.documents])
vecs = emb.encode_documents([c.text for c in chunks])
```

Fitting on chunks would let the chunking strategy change the latent space itself, which makes
any comparison between chunking strategies circular — you would be measuring two things at once
and attributing the result to one. Naming that unprompted reads as someone who has actually run
the experiment.

---

## M8 · When is precision-recall the right curve and ROC the wrong one?

**Asked at:** most applied-ML panels; near-universal for anything with class imbalance.

### The derivation

ROC plots TPR against FPR. $\mathrm{FPR} = FP / (FP + TN)$, and $TN$ is typically enormous under
imbalance. Adding false positives barely moves FPR, so ROC-AUC stays flattering while precision
collapses.

PR plots precision against recall, and precision $= TP/(TP+FP)$ has no $TN$ term at all — it is
sensitive to exactly the thing you care about when positives are rare.

**Concrete:** 1,000,000 documents, 100 relevant. A system returning 100 true positives and
10,000 false positives has $\mathrm{FPR} = 10^4/(10^6) = 0.01$ — an excellent-looking ROC point
— and precision $= 100/10{,}100 \approx 0.0099$. Unusable. ROC said fine; PR said catastrophe.

The formal statement (Davis & Goadrich, 2006): a curve dominates in ROC space **iff** it
dominates in PR space, but *area* under the two is not monotonically related, and algorithms
that optimise ROC-AUC do not optimise PR-AUC.

### Connected to a measured result here

Abstention detection in this repository is a rare-positive problem, and no retrieval-score
threshold separates answerable from unanswerable questions — best F1 **0.38** across four
signals tried. The mechanism is worth stating because it is counter-intuitive: the null
questions name real entities using the corpus's own vocabulary, while the genuine questions
paraphrase. So the *unanswerable* questions are lexically **closer** to the corpus than the
answerable ones. Any threshold on retrieval score is therefore reading a signal that points the
wrong way, and no amount of threshold tuning repairs a feature with the wrong sign.

---

## M9 · Rapid-fire

Short derivations that appear as warm-ups or interrupts.

| Question | The answer they want |
|---|---|
| Why cosine and not Euclidean for text embeddings? | Document length inflates vector magnitude without changing topic. Cosine is scale-invariant; on $L^2$-normalised vectors it is monotone in Euclidean distance, so they rank identically — the real answer is that normalisation is doing the work, not the metric |
| Expected value of MRR for a random ranker over $N$ documents with 1 relevant? | $\frac{1}{N}\sum_{i=1}^{N}\frac{1}{i} = \frac{H_N}{N} \approx \frac{\ln N + \gamma}{N}$. For $N=1000$, ≈ 0.0075. Useful as a floor: an MRR of 0.02 is not "low", it is 3× random |
| Why is `k` in Recall@k not a free parameter? | It is a context-budget decision in disguise. `k` chunks × chunk size must fit the window alongside the prompt and the answer. Reporting Recall@100 for a system that can pack 8 is measuring something you cannot ship |
| Two retrievers, 0.70 recall each. Union's recall? | Between 0.70 (identical) and 1.00 (disjoint errors). The gap *is* the complementarity, and it is the only thing that predicts whether fusion will help. Measure it before building the fusion |
| Why does a cross-encoder beat a bi-encoder? | The bi-encoder must compress a document to a fixed vector *before seeing the query*, so it cannot attend query-conditionally. The cross-encoder attends jointly over the pair. The price is no precomputation: $O(N)$ forward passes per query, which is why it only ever runs on a candidate list |
| Chunk size ↑ — what happens to recall and precision? | Recall@k rises (each chunk covers more ground, more likely to contain the evidence), context precision falls (more irrelevant text per retrieved chunk). Both move; reporting only the one that improved is the most common way retrieval results are misrepresented |

---

## How to practise these

Do them at a whiteboard, out loud, timed at eight minutes each. The failure mode in a real
interview is not being unable to derive BM25 — it is deriving it correctly while silent, then
having ninety seconds left for the follow-up that was the actual question.

For each: state the shape of the answer first, derive second, and volunteer the failure mode
without being asked. That ordering is what the "hires at senior" column is made of.

**Then go further than the answer.** Every derivation above has a corresponding cell in the
notebooks where the number is computed rather than asserted. Run it, change a parameter, watch
the metric move, and you will have something to say that no other candidate in the loop does:
"I ran that, and here is where it stops behaving the way the formula suggests."
