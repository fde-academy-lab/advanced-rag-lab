#!/usr/bin/env python3
"""FD1 · the grader runs the three chunkers rather than trusting a key.

The answer key is computed, not asserted: each implementation in the brief is executed on a
document whose length is not a multiple of the stride, and "drops the tail" means the last
word of the document is missing from the output. If somebody edits the brief's code, the key
moves with it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_answer, run  # noqa: E402


def chunk_a(text, size=64, overlap=16):
    words = text.split()
    stride = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - size, 1), stride)]


def chunk_b(text, size=64, overlap=16):
    words = text.split()
    stride = size - overlap
    out, start = [], 0
    while True:
        out.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            return out
        start += stride


def chunk_c(text, size=64, overlap=16):
    words = text.split()
    stride = size - overlap
    n_windows = len(words) // stride
    return [" ".join(words[i * stride:i * stride + size]) for i in range(n_windows)]


CANDIDATES = {"A": chunk_a, "B": chunk_b, "C": chunk_c}


LENGTHS = (100, 140)     # neither is a multiple of the stride (48); C fails only at 140


def drops_tail_at(fn, n_words: int) -> bool:
    words = [f"w{i}" for i in range(n_words)]
    out = fn(" ".join(words))
    return not out or words[-1] not in out[-1].split()


def drops_tail(fn) -> bool:
    """Drops it on ANY of the lengths. C is the reason for the plural: it reaches the end of a
    100-word document and loses the last 28 words of a 140-word one, which is the nastier bug —
    it passes the one test somebody wrote."""
    return any(drops_tail_at(fn, n) for n in LENGTHS)


def main(attempt: str) -> int:
    ans = load_answer(attempt, required=("drops_the_tail", "because"))
    c = Checker()

    raw = ans["drops_the_tail"]
    picked = {str(x).strip().upper() for x in (raw if isinstance(raw, list) else [raw])}
    truth = {letter for letter, fn in CANDIDATES.items() if drops_tail(fn)}
    for n in LENGTHS:
        bad = [L for L, fn in CANDIDATES.items() if drops_tail_at(fn, n)]
        c.note(f"{n}-word document, stride 48: {', '.join(bad) or 'none'} lose the last word")

    c("only letters A, B or C are named", picked <= set(CANDIDATES),
      f"got {sorted(picked)}")
    c("the chunkers you named are the ones that drop words", truth <= picked,
      f"missed {sorted(truth - picked)}: {', '.join(sorted(truth - picked))} "
      f"return a last chunk without the document's last word")
    c("you did not accuse a chunker that is correct", picked <= truth,
      f"{sorted(picked - truth)} reach the end of the document")
    c("the reason names the condition", len(str(ans["because"]).split()) >= 6,
      "one sentence about the bound, six words or more")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
