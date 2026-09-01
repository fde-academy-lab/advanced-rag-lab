"""Decoy · correct on the happy path, crashes when retrieval returns nothing.

Written the way people actually write it: a header derived from the top hit, because a bundle
reads better with one. `hits[0]` is fine in every test anyone runs by hand and raises the first
time a user asks about something the corpus does not contain — which, on the Client Zero
corpus, is 36 of 243 questions.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class PackedContext:
    text: str
    markers: dict[int, str]


def pack_context(hits) -> PackedContext:
    blocks: list[str] = []
    markers: dict[int, str] = {}
    top = hits[0]                                           # <- the bug
    for i, hit in enumerate(hits, start=1):
        markers[i] = hit.chunk_id
        provenance = f"[{i}] {hit.doc_id} · chunk {hit.ordinal} · score {hit.score:.2f}"
        blocks.append(f"{provenance}\n{hit.text}")
    assert top is not None
    return PackedContext(text="\n\n".join(blocks), markers=markers)
