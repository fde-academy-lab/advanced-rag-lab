"""R1 · Make a citation resolve.

Implement pack_context. Run `labsim check R1` when you want it graded.
"""
from __future__ import annotations

import dataclasses


@dataclasses.dataclass
class PackedContext:
    text: str
    markers: dict[int, str]


def pack_context(hits) -> PackedContext:
    """Assemble hits into a numbered evidence bundle.

    Each hit has: chunk_id, text, doc_id, ordinal, score.

    Returns a PackedContext where `text` is what the generator reads and `markers` maps the
    marker number to the chunk_id it came from, so a citation can be resolved afterwards.
    """
    blocks: list[str] = []
    markers: dict[int, str] = {}

    for i, hit in enumerate(hits, start=1):
        # TODO 1 — record the mapping from marker i to hit.chunk_id
        # TODO 2 — build the provenance line: marker, doc_id, ordinal, score to 2 decimals.
        #          The chunk_id must not appear in it.
        # TODO 3 — append "provenance line, newline, passage text" to blocks
        pass

    # TODO 4 — join the blocks with a blank line between them
    return PackedContext(text="", markers=markers)
