"""Decoy · tests each step on its own and forgets what earlier steps gathered."""
from __future__ import annotations


def stop_at(steps: list[set[str]], required: set[str]) -> int | None:
    for i, found in enumerate(steps):
        if required <= set(found):
            return i
    return None
