# R1 · How we did it

```python
def pack_context(hits) -> PackedContext:
    blocks: list[str] = []
    markers: dict[int, str] = {}
    for i, hit in enumerate(hits, start=1):
        markers[i] = hit.chunk_id
        provenance = f"[{i}] {hit.doc_id} · chunk {hit.ordinal} · score {hit.score:.2f}"
        blocks.append(f"{provenance}\n{hit.text}")
    return PackedContext(text="\n\n".join(blocks), markers=markers)
```

Twelve lines. The exercise is not the code.

## The line that is the whole unit

```python
markers[i] = hit.chunk_id
```

Everything else is formatting. Without that line you have a context block that *looks* cited and
whose citations resolve to nothing — and it passes every shape check anyone writes.

That is why the graded property is stated over randomised inputs rather than as a string
comparison. A test that compares against an expected string tests your formatting choices. A
test that asserts *every marker resolves to a chunk_id that was in the input* tests the promise.

## Four things worth arguing about

**Why `enumerate(hits, start=1)` and not the hit's rank.** The marker is a position in *this*
bundle, not a global rank. Reusing an upstream rank means renumbering anywhere upstream silently
repoints every citation, and nothing detects it.

**Why the score is rounded in the display and not in the data.** The two-decimal form is for a
human. Rounding the stored score would make the audit trail disagree with the retriever.

**Why provenance comes first.** Position matters. A model that reads the passage and then finds
the marker attaches the marker less reliably than one that reads the marker first. Small effect,
free to get right.

**Why `chunk_id` is not in the text.** It is an internal key with a content hash in it. Put it in
front of the model and the model will eventually quote it at a user, and now your internal id
scheme is a support ticket.

## Where this lives in the real system

`raglab/context.py` does the same job with two additions: a **hard token budget**, so packing
stops before the window overflows rather than truncating a chunk in half; and **volatility
ordering**, so the cacheable prefix stays byte-identical between queries.

That second one is a cost decision hiding in a formatting function — see
[ADR-0012](../../../docs/01-architecture/adr/0012-prompt-block-ordering.md), where a timestamp at
byte 58 of a system prompt cost two thirds of an inference budget.

## What this unlocks

**R2** asks you to decide how to fuse two retrievers before you are allowed to implement one.
Same corpus, harder question — and no code until the decision is written down.
