# F1 · How we did it

```python
def chunk(text, size_tokens=512, overlap_tokens=64):
    if overlap_tokens >= size_tokens:
        raise ValueError(
            f"overlap_tokens={overlap_tokens} must be smaller than size_tokens={size_tokens}; "
            "otherwise the window never advances")
    words = text.split()
    if not words:
        return []
    if len(words) <= size_tokens:
        return [" ".join(words)]

    stride = size_tokens - overlap_tokens
    out, start = [], 0
    while start < len(words):
        out.append(" ".join(words[start:start + size_tokens]))
        if start + size_tokens >= len(words):
            break                     # this window already reaches the end
        start += stride
    return out
```

## The three lines that are the unit

**`stride = size_tokens - overlap_tokens`.** That is the algorithm. Everything else is bookkeeping.

**`if start + size_tokens >= len(words): break`.** Written as a `while` with an explicit break
rather than a `range`, because the tail condition is a *statement about the document* and a range
expression hides it. `range(0, len(words), stride)` emits a final window that is shorter than the
others and that is correct; `range(0, len(words) - size_tokens, stride)` looks tidier and drops
the end of every document. Both are one character apart and one of them is a month of blaming the
retriever.

**The `ValueError`.** `overlap >= size` gives a stride of zero or negative. A `range` with a
non-positive step raises; a `while` loop silently never advances and your process hangs on a
config change. Raising at the boundary is the only version where the failure names itself.

## Why the property is stated over spans

A test that asserts `len(chunk) <= 64` tests your arithmetic. Sliding-window chunking makes a
different promise, and it is worth writing precisely:

> For a window size `s` and overlap `v`, every contiguous span of at most `v` tokens is wholly
> contained in at least one window.

Proof sketch, because it is short and it changes how you pick `v`: windows start at `0, k, 2k, …`
with `k = s − v`. A span of length `L` starting at position `p` falls inside the window starting
at `⌊p/k⌋·k` provided `p − ⌊p/k⌋·k + L ≤ s`. The first term is at most `k − 1`, so the condition
holds whenever `L ≤ s − k + 1 = v + 1`.

The consequence is the useful part: **overlap is not a tuning knob, it is a length budget**. You
do not pick it by feel. You measure the longest thing you need to keep intact — on Client Zero,
the cause-and-effect sentence pair in a postmortem, about 60 tokens — and set `v` above it. Once
somebody asks "how long is the answer?", the argument about 10% versus 20% overlap stops
happening.

## What it costs

Overlap is redundancy, and redundancy is money in three places:

| | Effect of `v = 64` on `s = 512` |
|---|---|
| Index size | `s/(s−v)` = **1.14×** more chunks, so 14% more vectors, more storage, more ANN nodes |
| Retrieval | Near-duplicate chunks compete for the same top-k slots, so effective `k` is lower than nominal `k` |
| Generation | The same sentence can be packed twice, spending context on nothing |

The middle row is the one that surprises people, and it is why `k` and `v` should be tuned
together rather than in separate sprints. Deduplicating on chunk overlap before packing recovers
most of it — `raglab/context.py` does this, and it is four lines.

## What we got wrong first

**We tuned size before we measured span length.** Three days on 256 versus 512, on a corpus where
the answer spans were 60 tokens and the overlap was 32. Both sizes were wrong in the same way and
the comparison could not see it, because both arms lost the same answers. The measurement that
would have ended it in an hour is: take the gold evidence spans, measure their token lengths, plot
the distribution. The 95th percentile *is* your overlap.

**We treated the tail bug as a retrieval problem.** Questions about incident *resolutions* scored
badly. Resolutions are at the end of postmortems. The end of every document was not in the index.
We spent two weeks on the reranker.

The diagnostic that would have found it immediately is the one E1 builds: recall per piece of
evidence, sliced by where in the document the evidence lives. A retriever problem is roughly
uniform across that slice. A coverage problem is a cliff.

## Where this lives in the real system

`raglab/chunking.py` has seven strategies, and F1 is `fixed` with the guard added. The others are
worth reading in this order once you have this one working:

- **`recursive`** splits on paragraph, then sentence, then word — so a cut lands on a boundary a
  human would have chosen. Same guarantee, better-looking chunks.
- **`structural`** (the default) uses the document's own headings, which is why chunk sizes vary
  and why the size cap is a cap rather than a target.
- **`parent_document`** indexes small children and returns large parents: retrieve precisely,
  generate with context. It sidesteps this whole trade-off and pays for it in packing.
- **`contextual`** prepends a generated one-line summary of the document to each chunk. This is
  Anthropic's contextual retrieval, and it moved failed-retrieval rate from 5.7% to 1.9% on their
  benchmark — see `concepts-and-case-studies/`.

[ADR-0004](../../../docs/01-architecture/adr/0004-stable-chunk-ids.md) is the related decision:
chunk ids are content-addressed, so re-chunking with a different overlap does not silently
invalidate every citation ever emitted.

## What this unlocks

**E1** builds evidence recall — the metric that separates "the retriever ranked it badly" from
"it was never in the index". They look identical from the outside and have nothing in common.
