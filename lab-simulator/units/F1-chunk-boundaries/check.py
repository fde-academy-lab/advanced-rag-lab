#!/usr/bin/env python3
"""Checks for F1 · Chunk so the answer survives the cut.

The check that carries the unit is `every short span survives whole`. It is stated the way the
sliding window's promise is stated — over spans, not over sizes — because a chunker with no
overlap at all satisfies every size assertion anyone writes and fails the promise completely.

The vocabulary is deliberately technical. A decoy that measures overlap in characters passes on
ordinary English and fails here, which is the same asymmetry it would show in production.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

VOCAB = ("halden-systems tessera-analytics pagerduty-4471 rollback ap-southeast-2 "
         "postmortem escalation runbook/RB-118 sev2 latency p99 acquisition "
         "consolidation ingest-worker backpressure kafka-lag shard-rebalance").split()


def document(n_words: int, seed: int) -> str:
    rng = random.Random(seed)
    return " ".join(rng.choice(VOCAB) for _ in range(n_words))


def _contains(body: list[str], span: list[str]) -> bool:
    n = len(span)
    return any(body[j:j + n] == span for j in range(len(body) - n + 1))


def spans_survive(words: list[str], chunks: list[str], span_len: int) -> tuple[bool, str]:
    """Every window of `span_len` consecutive words must sit whole inside some chunk."""
    bodies = [c.split() for c in chunks]
    for i in range(max(len(words) - span_len + 1, 0)):
        span = words[i:i + span_len]
        if not any(_contains(body, span) for body in bodies):
            return False, (f"the {span_len}-word span starting at word {i} "
                           f"({' '.join(span[:4])} ...) is not wholly inside any chunk")
    return True, ""


def _subsequence(original: list[str], produced: list[str]) -> bool:
    """Every original word appears in `produced`, in order, allowing overlap duplicates."""
    i = 0
    for w in produced:
        if i < len(original) and w == original[i]:
            i += 1
    return i == len(original)


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("chunk",))
    c = Checker()

    text = document(300, seed=5)
    words = text.split()
    try:
        chunks = mod.chunk(text, size_tokens=64, overlap_tokens=16)
    except Exception as exc:  # noqa: BLE001
        c("chunk runs", False, f"{type(exc).__name__}: {exc}")
        return emit({}, c)

    if not c("returns a list of strings",
             isinstance(chunks, list) and all(isinstance(x, str) for x in chunks),
             f"got {type(chunks).__name__}"):
        return emit({}, c)

    c("no chunk exceeds size_tokens",
      all(len(x.split()) <= 64 for x in chunks),
      f"largest was {max((len(x.split()) for x in chunks), default=0)} words")

    joined = [w for x in chunks for w in x.split()]
    c("every word survives, in order", _subsequence(words, joined),
      f"{len(words)} words in, {len(joined)} out - check the tail")

    c("the last word of the document is in the last chunk",
      bool(chunks) and chunks[-1].split()[-1:] == words[-1:],
      f"document ends {words[-1]!r}, last chunk ends "
      f"{(chunks[-1].split()[-1] if chunks else None)!r}")

    c("consecutive chunks overlap",
      len(chunks) < 2 or bool(set(chunks[0].split()) & set(chunks[1].split())),
      "chunk 1 and chunk 2 share no words - the stride is the full window")

    ok, why = spans_survive(words, chunks, span_len=16)
    c("every short span survives whole", ok, why or "the promise of a sliding window")

    if ok:
        hard = document(211, seed=17)
        ok2, why2 = spans_survive(hard.split(),
                                  mod.chunk(hard, size_tokens=40, overlap_tokens=12), 12)
        c("...and at a size that does not divide the document evenly", ok2, why2)

    short = "three words only"
    try:
        out = mod.chunk(short, size_tokens=64, overlap_tokens=16)
        c("a document shorter than one window yields one chunk",
          len(out) == 1 and out[0].split() == short.split(), f"got {out!r}")
    except Exception as exc:  # noqa: BLE001
        c("a document shorter than one window yields one chunk", False,
          f"{type(exc).__name__}: {exc}")

    try:
        z = mod.chunk(document(120, seed=3), size_tokens=32, overlap_tokens=0)
        total = sum(len(x.split()) for x in z)
        c("overlap of zero is allowed and tiles the document", total == 120,
          f"total words out: {total}")
    except Exception as exc:  # noqa: BLE001
        c("overlap of zero is allowed and tiles the document", False,
          f"{type(exc).__name__}: {exc}")

    try:
        mod.chunk(text, size_tokens=32, overlap_tokens=32)
        c("overlap >= size raises ValueError", False,
          "it returned instead. A window that never advances is a config error, not a default")
    except ValueError:
        c("overlap >= size raises ValueError", True)
    except Exception as exc:  # noqa: BLE001
        c("overlap >= size raises ValueError", False,
          f"raised {type(exc).__name__} instead: {exc}")

    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
