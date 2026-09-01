"""F1 · the worked answer."""
from __future__ import annotations


def chunk(text: str, size_tokens: int = 512, overlap_tokens: int = 64) -> list[str]:
    if overlap_tokens >= size_tokens:
        raise ValueError(
            f"overlap_tokens={overlap_tokens} must be smaller than size_tokens={size_tokens}; "
            "otherwise the window never advances")
    words = text.split()
    if not words:
        return []
    if len(words) <= size_tokens:
        return [" ".join(words)]

    stride = size_tokens - overlap_tokens
    out: list[str] = []
    start = 0
    while start < len(words):
        out.append(" ".join(words[start:start + size_tokens]))
        if start + size_tokens >= len(words):
            break                     # this window already reaches the end
        start += stride
    return out
