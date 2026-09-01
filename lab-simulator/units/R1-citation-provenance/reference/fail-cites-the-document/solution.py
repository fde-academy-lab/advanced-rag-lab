"""Decoy · cites the document instead of the passage.

The commonest wrong answer, and it is wrong in a way that is invisible in a demo. Every block
is formatted correctly, every marker appears in order, and the citation takes a reader to a
34-page runbook rather than to the two sentences the claim came from.

It has to stay rejected. If it ever passes, R1 has become a formatting exercise.
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
        markers[i] = hit.doc_id          # <- the bug
        provenance = f"[{i}] {hit.doc_id} · chunk {hit.ordinal} · score {hit.score:.2f}"
        blocks.append(f"{provenance}\n{hit.text}")
    return PackedContext(text="\n\n".join(blocks), markers=markers)
