"""Decoy · stops on the first non-empty step. Some evidence is not enough evidence."""
from __future__ import annotations


def stop_at(steps: list[set[str]], required: set[str]) -> int | None:
    for i, found in enumerate(steps):
        if found & required:
            return i
    return None
