"""F1 · Chunk so the answer survives the cut.

Implement chunk(). Run `labsim check F1` when you want it graded.
"""
from __future__ import annotations


def chunk(text: str, size_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    """Split `text` into overlapping windows of whitespace-separated words.

    Guarantees the checks enforce:
      - every word appears in some chunk, in order, including the last
      - no chunk is longer than size_tokens words
      - consecutive chunks share overlap_tokens words
      - any span of at most overlap_tokens words is wholly inside some chunk

    Raise ValueError if overlap_tokens >= size_tokens — that is a configuration error, and the
    alternative is a loop that never advances.
    """
    words = text.split()

    # TODO 1 — reject the configuration that cannot terminate
    # TODO 2 — the stride between window starts
    # TODO 3 — emit windows, and make sure the last one reaches the end of the document
    return []
