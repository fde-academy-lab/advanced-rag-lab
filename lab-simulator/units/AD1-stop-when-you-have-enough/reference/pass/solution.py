from __future__ import annotations


def stop_at(steps: list[set[str]], required: set[str]) -> int | None:
    gathered: set[str] = set()
    for i, found in enumerate(steps):
        gathered |= set(found)
        if required <= gathered:
            return i
    return None
