"""Decoy · puts the chunk_id in front of the model.

Reasonable-looking: "the model should know exactly what it is reading." The mapping is correct,
the citations resolve, every property holds. What breaks is downstream and months later — the
model starts quoting `doc-a4f1c2:7:a4f1` at a user, and an internal key scheme becomes a
support ticket and then a migration nobody budgeted for.
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
    for i, hit in enumerate(hits, start=1):
        markers[i] = hit.chunk_id
        provenance = (f"[{i}] {hit.doc_id} · chunk {hit.ordinal} · id {hit.chunk_id} "
                      f"· score {hit.score:.2f}")          # <- the bug
        blocks.append(f"{provenance}\n{hit.text}")
    return PackedContext(text="\n\n".join(blocks), markers=markers)
