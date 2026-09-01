"""R1 · the worked answer.

Graded in CI on every change to the unit. If this stops passing, the checks moved and the
brief did not.
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
        provenance = f"[{i}] {hit.doc_id} · chunk {hit.ordinal} · score {hit.score:.2f}"
        blocks.append(f"{provenance}\n{hit.text}")
    return PackedContext(text="\n\n".join(blocks), markers=markers)
