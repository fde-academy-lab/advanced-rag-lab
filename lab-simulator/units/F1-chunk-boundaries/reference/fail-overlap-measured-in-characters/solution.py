"""Decoy · the guarantee is stated in tokens and enforced in characters.

Windows are cut by word count and the overlap is taken as a character slice off the previous
chunk. For short English words the two are close enough that a spot check passes. For technical
prose — identifiers, hostnames, stack frames, the exact places the answers live — a character
overlap of 64 buys about nine words, and the span guarantee is gone without anything looking
wrong.
"""
from __future__ import annotations


def chunk(text: str, size_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    if overlap_tokens >= size_tokens:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    if not words:
        return []
    out: list[str] = []
    start = 0
    while start < len(words):
        window = words[start:start + size_tokens]
        out.append(" ".join(window))
        if start + size_tokens >= len(words):
            break
        # Back up by overlap_tokens *characters* worth of words.
        chars, back = 0, 0
        for w in reversed(window):
            if chars + len(w) + 1 > overlap_tokens:
                break
            chars += len(w) + 1
            back += 1
        start += max(size_tokens - back, 1)
    return out
