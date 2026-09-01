# LLD · `chunking.py`

Seven strategies and the id scheme. The module whose output constrains everything downstream,
because a fact split across two chunks cannot be recovered by any amount of retrieval quality.

## Contract

```python
def chunk_corpus(documents, strategy: str) -> list[Chunk]
```

`strategy ∈ {fixed, recursive, structural, semantic, parent_document, contextual, late_chunking}`

## The id

```python
chunk_id = f"{doc_id}:{ordinal}:{sha1(text)[:10]}"
```

Content-addressed, so an unchanged chunk keeps its id across a rebuild. That is what makes an
incremental update an **upsert** rather than a delete-then-insert that orphans rows and leaves
the previous version of a document permanently retrievable with no error anywhere. ADR-0004.

The consequence people find surprising: **changing the chunker changes every id**, so it forces
a full reindex. That is the honest cost of chunking being a real decision rather than a setting.

## The strategies

| Strategy | Boundary rule | Best when | Cost |
|---|---|---|---|
| `fixed` | Every N tokens | Never, in practice. It is the baseline to beat | Splits mid-sentence, mid-fact |
| `recursive` | Paragraph → sentence → token, largest that fits | Unstructured prose | Reasonable default |
| `structural` | On document headings | Anything authored with sections | Variable sizes; a long section stays long |
| `semantic` | Where adjacent-sentence similarity drops | Topic drift within a section | An embedding pass at index time |
| `parent_document` | Retrieve small, return the parent | Precision at retrieval, context at generation | Two representations to keep in sync |
| `contextual` | Prepend a generated summary of the document | Chunks that are ambiguous out of context | One generation call **per chunk** |
| `late_chunking` | Embed the whole document, pool per chunk | Long-range coreference | Whole document must fit the encoder |

## What the comparison actually shows

Evidence recall differences between strategies on this corpus are mostly **inside the noise
band**. That is the uncomfortable result most chunking comparisons produce and rarely report.

The measurement that does discriminate is **boundary damage** — the fraction of gold evidence
spans split across two chunks. It varies widely across strategies while recall varies narrowly,
and the two are only weakly connected here.

The reason is a corpus property, not a general finding: gold spans in this corpus are short
relative to chunk size, so a split is rare enough that it does not move an average. On a corpus
with long gold spans the two would couple tightly. EX-04 is this exercise.

## The methodology trap

**Fit the embedder on documents, not chunks.**

```python
emb = embed.LsaEmbedder(dim=dim).fit([d.title + "\n" + d.body for d in bundle.documents])
vecs = emb.encode_documents([c.text for c in chunks])
```

Fitting on chunks lets the chunking strategy change the embedding space itself, so a comparison
between strategies measures two things and attributes the result to one. The numbers look
reasonable and mean nothing.

This is a correctness failure, not a preference, and it invalidates any strategy comparison run
the other way.

## `contextual`, and why it did not pay here

Contextual chunking cost **2.4× storage** and **3.1× index build time**, for a recall change
inside the noise band.

The mechanism is a missing precondition rather than a failure of the technique. Published results
come from corpora where chunks are genuinely ambiguous out of context — long documents where a
chunk says "the rate was raised to 4.5%" and the entity is three sections up. This corpus is
generated to write self-contained passages, so the entity is named in nearly every chunk. There
is nothing for the added context to disambiguate.

Honest statement: **contextual chunking cannot help on a corpus whose chunks are already
self-contained.** It predicts where the technique *would* pay — long documents with heavy anaphora
and entity elision.

Build-time scaling matters here too: the cost is per **chunk**, not per document, so it scales
with the worse of the two. Survivable for a nightly rebuild, disqualifying for an hourly
freshness SLA, because the incremental path pays it for every changed chunk.

## Complexity

| Strategy | Index-time cost |
|---|---|
| `fixed`, `recursive`, `structural` | O(total tokens) |
| `semantic` | O(sentences) embeddings |
| `contextual` | O(chunks) **generation calls** |
| `late_chunking` | O(documents) encoder passes, each over a whole document |

## Failure modes

| Symptom | Cause |
|---|---|
| Every strategy scores identically | Documents too short for boundaries to differ. This was issue #5 |
| Recall drops after a chunker change with no reindex | Ids changed; the index holds orphans |
| Oversized chunks | A single section longer than the target. State the policy — hard-split or allow |
| Strategy comparison is unstable | Embedder fitted on chunks |

## What would change this design

**A corpus with long gold spans.** Boundary damage would then couple to recall and the strategy
choice would matter far more than it does here.

**Layout-aware chunking.** PDFs with tables and multi-column text need boundaries derived from
layout rather than from text, which is a different input, not a different rule.
