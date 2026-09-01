# Coding

The screen. Forty-five minutes, shared editor, no autocomplete worth having. What is being
tested is not whether you can implement BM25 from memory — it is whether you write code someone
else could maintain while under time pressure, and whether you say what you are doing while you
do it.

Each problem below gives the prompt as it is actually posed, the reference solution, the
follow-ups the interviewer has queued, and the specific things that lose marks.

---

## C1 · Implement BM25 scoring over a small in-memory corpus

**Time given:** 25 minutes, then 15 minutes of follow-ups.

### The prompt

> "Here's a list of documents as strings and a query as a string. Return the documents ranked by
> BM25. You can assume whitespace tokenisation. Write it as if someone else will read it."

### Reference solution

```python
import math
from collections import Counter


def bm25_rank(documents: list[str], query: str, k1: float = 1.5, b: float = 0.75):
    """Rank documents against a query by BM25.

    k1 controls term-frequency saturation, b controls length normalisation. Both are
    defaults from the literature rather than tuned for any particular corpus.
    """
    docs = [d.lower().split() for d in documents]
    n = len(docs)
    avgdl = sum(len(d) for d in docs) / n if n else 0.0

    # Document frequency per term: how many documents contain it at all.
    df = Counter()
    for d in docs:
        df.update(set(d))

    scores = []
    for i, d in enumerate(docs):
        tf = Counter(d)
        score = 0.0
        for term in query.lower().split():
            if term not in tf:
                continue
            # +0.5 smoothing keeps this finite when a term is in every document
            # or none of them — it is a Jeffreys prior, not a fudge factor.
            idf = math.log((n - df[term] + 0.5) / (df[term] + 0.5) + 1)
            denom = tf[term] + k1 * (1 - b + b * len(d) / avgdl)
            score += idf * (tf[term] * (k1 + 1)) / denom
        scores.append((score, i))

    return [(documents[i], s) for s, i in sorted(scores, reverse=True)]
```

### What loses marks

| Mistake | Why it costs |
|---|---|
| `df` counted from `Counter(d)` rather than `set(d)` | Document frequency counts *documents*, not occurrences. This is the single most common bug and it silently produces wrong IDF |
| No `+0.5` smoothing | `log(0)` when a term appears in every document. The interviewer will hand you that input |
| Recomputing `df` inside the document loop | O(n²) for no reason. They will ask about complexity |
| Division by zero on an empty corpus | Guarded above; most candidates don't |
| No docstring, no comment on `k1`/`b` | "As if someone else will read it" was in the prompt. It is part of the grading |

### The queued follow-ups

1. **"What's the complexity?"** — O(N·|d|) to build `df`, then O(N·|q|) to score. The important
   observation is that scoring is linear in corpus size, which is why you need an inverted index:
   it turns the scoring loop into a walk over posting lists for query terms only.
2. **"Make it fast for a million documents."** — Build the inverted index. Term → list of
   (doc_id, tf). Only touch documents containing at least one query term. Then WAND or
   block-max WAND to skip documents that cannot enter the top k.
3. **"What if the query has a term in no document?"** — `df = 0`, IDF is at its maximum, and the
   term contributes nothing because no document has it. Fine mathematically; worth saying out
   loud that it's fine, because the interviewer wants to know you checked.
4. **"Add phrase matching."** — Needs positions in the index, not just counts. Say the cost:
   positional indexes are substantially larger, and it is a storage decision rather than a
   scoring one.

---

## C2 · Chunk a document with overlap, without splitting mid-sentence

**Time given:** 20 minutes.

Tests boundary handling, which is where almost everyone's off-by-one lives.

```python
import re


def chunk(text: str, size: int = 400, overlap: int = 50) -> list[str]:
    """Split text into ~size-word chunks that end on sentence boundaries where possible.

    Overlap is in words and is taken from the end of the previous chunk, so a fact sitting
    near a boundary appears whole in at least one chunk.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than size, or chunking cannot advance")

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks: list[str] = []
    current: list[str] = []
    count = 0

    for sentence in sentences:
        words = sentence.split()
        if count + len(words) > size and current:
            chunks.append(" ".join(current))
            # Carry the tail forward, measured in words rather than sentences so the
            # overlap is predictable regardless of sentence length.
            tail, taken = [], 0
            for w in reversed(current):
                if taken >= overlap:
                    break
                tail.insert(0, w)
                taken += 1
            current, count = tail, taken
        current.extend(words)
        count += len(words)

    if current:
        chunks.append(" ".join(current))
    return chunks
```

### What loses marks

- **Infinite loop when `overlap >= size`.** Guarded above. Without the guard the function never
  advances, and the interviewer has that input ready.
- **A single sentence longer than `size` silently produces an oversized chunk.** Say it out loud
  and state the policy — hard-split it, or let it through — rather than leaving it undefined.
- **Overlap measured in sentences.** Then chunk sizes swing wildly with sentence length.
- **Dropping the final partial chunk.** Common and easy to miss.

### The follow-up that matters

> *"How would you know whether this chunking is any good?"*

Not "measure recall". The specific answer: **boundary damage** — the fraction of gold evidence
spans split across two chunks. That is the failure chunking uniquely causes, and it is invisible
in aggregate recall because a split fact degrades both chunks slightly rather than failing one
loudly.

---

## C3 · Reciprocal rank fusion

**Time given:** 15 minutes. Usually a warm-up before a discussion.

```python
def rrf(rankings: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fuse ranked id lists by reciprocal rank.

    k dampens the authority of any single system's top hit: at k=0 rank 1 scores twice
    rank 2 and cannot be outvoted; at k=60 the gap is about 2%, so agreement across
    systems outranks confidence within one.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: -kv[1])
```

The code is easy. The marks are in the discussion:

- **Why ranks and not scores?** BM25 is an unbounded sum of log-odds, cosine is bounded, a
  cross-encoder emits logits. Not on a common scale, not monotonically related, and their
  distributions differ per query — so any weighted sum of raw scores is dominated by whichever
  system has the larger variance on that query, which is a property of the scoring function
  rather than of relevance.
- **`enumerate(..., start=1)`** — starting at 0 makes rank 0 score `1/k` and rank 1 score
  `1/(k+1)`, which is a subtle and real bug. Interviewers watch for the `start=1`.
- **When does RRF lose?** When the legs differ a lot in strength. Equal-weight fusion is a
  voting rule that treats both voters as equally credible; fuse a strong leg with a weak one and
  you move toward the weak one. Bringing a measured instance of this is a strong move.

---

## C4 · Evaluate a retriever

**Time given:** 20 minutes. Often the last problem, and the one that most predicts the offer.

```python
def evaluate(results: dict[str, list[str]], gold: dict[str, set[str]], k: int = 10):
    """Recall@k, full-chain recall@k, and MRR over a query set.

    Recall@k is per evidence piece; full-chain is per question and requires every piece.
    Reporting only the first hides multi-hop failure, because widening k raises the
    per-piece average by returning more of the evidence you were already good at.
    """
    if not gold:
        return {"recall@k": 0.0, "full_chain@k": 0.0, "mrr": 0.0, "n": 0}

    recalls, chains, rr = [], [], []
    for qid, needed in gold.items():
        retrieved = results.get(qid, [])[:k]
        found = set(retrieved) & needed
        recalls.append(len(found) / len(needed) if needed else 0.0)
        chains.append(1.0 if needed <= set(retrieved) else 0.0)
        rank = next((i for i, d in enumerate(retrieved, 1) if d in needed), None)
        rr.append(1.0 / rank if rank else 0.0)

    n = len(gold)
    return {"recall@k": sum(recalls) / n, "full_chain@k": sum(chains) / n,
            "mrr": sum(rr) / n, "n": n}
```

### What earns the band

- Returning **`n`**. A metric without its denominator is not reportable, and interviewers notice
  who includes it.
- Handling a query with **no results** rather than raising.
- Computing full-chain at all. Most candidates return recall and MRR and stop, and the
  interviewer's follow-up — *"what does this miss?"* — is the question the whole problem exists
  to ask.
- Saying out loud that these are means, and a mean without a confidence interval is not a result
  you would act on.

---

## Behaviour that decides the screen

The code is rarely the differentiator at this level; three behaviours are.

**Narrate before typing.** Thirty seconds of "I'll build document frequency first, then score in
one pass, and I need to be careful that df counts documents rather than occurrences" tells the
interviewer everything about how you think — and if your plan is wrong they will stop you
before you spend fifteen minutes on it.

**Say the edge cases out loud even when you don't handle them.** "A sentence longer than the
chunk size produces an oversized chunk. I'd hard-split it, but I'll leave it for now and note
it." That is a stated tradeoff. Silence is an unnoticed bug.

**Test with one hand-computed example.** Two documents, one query, work out the score on paper
and check the code agrees. Candidates who do this find their own bugs; candidates who don't have
them found for them.
