"""Decoy · the off-by-one that gets shipped.

`range(0, n - size, stride)` instead of `range(0, n, stride)`. It reads tidier — it looks like
it is avoiding a short final chunk — and it silently drops the end of every document. On a
postmortem corpus that is the resolution section, so questions about how incidents were fixed do
badly for a month and the retriever gets blamed.
"""
from __future__ import annotations


def chunk(text: str, size_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    if overlap_tokens >= size_tokens:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    stride = size_tokens - overlap_tokens
    return [" ".join(words[i:i + size_tokens])
            for i in range(0, max(len(words) - size_tokens, 1), stride)]
