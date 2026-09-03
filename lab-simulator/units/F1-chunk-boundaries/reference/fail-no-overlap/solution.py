"""Decoy · tidy, even, and it cuts answers in half.

Stride equals window size, so the chunks tile the document perfectly. Sizes are uniform, there
is no redundancy, the index is smaller and cheaper. Everything about it looks better than the
correct version except the one thing it was for.
"""
from __future__ import annotations


def chunk(text: str, size_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    if overlap_tokens >= size_tokens:
        raise ValueError("overlap must be smaller than size")
    words = text.split()
    return [" ".join(words[i:i + size_tokens]) for i in range(0, len(words), size_tokens)]
