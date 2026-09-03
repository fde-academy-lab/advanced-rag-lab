#!/usr/bin/env python3
"""Checks for R1 · Make a citation resolve.

Shape checks are ordinary. The one that carries the unit is `resolvable`: over randomised hit
lists, every marker appearing in the assembled text must resolve through `markers` to a
chunk_id that was in the input. A format-only implementation passes the shape checks and fails
that one, which is the point.
"""
from __future__ import annotations

import dataclasses
import random
import re
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

MARKER = re.compile(r"\[(\d+)\]")


@dataclasses.dataclass
class Hit:
    chunk_id: str
    text: str
    doc_id: str
    ordinal: int
    score: float


def sample(n: int, seed: int) -> list[Hit]:
    rng = random.Random(seed)
    return [
        Hit(chunk_id=f"doc-{tag}:{i}:{tag[:4]}",
            text=f"Passage {i} about {tag} and the incident it describes.",
            doc_id=f"doc-{tag}", ordinal=i, score=round(rng.uniform(0.2, 0.95), 4))
        for i, tag in enumerate("".join(rng.choices(string.ascii_lowercase, k=6))
                                for _ in range(n))
    ]


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("pack_context",))
    c = Checker()

    hits = sample(3, seed=7)
    try:
        packed = mod.pack_context(hits)
    except Exception as exc:  # noqa: BLE001
        c("pack_context runs", False, f"{type(exc).__name__}: {exc}")
        return emit({}, c)

    text, markers = getattr(packed, "text", None), getattr(packed, "markers", None)
    if not c("returns .text (str) and .markers (dict)",
             isinstance(text, str) and isinstance(markers, dict),
             f"got text={type(text).__name__}, markers={type(markers).__name__}"):
        return emit({}, c)

    c("one marker per hit", set(markers) == {1, 2, 3}, f"keys were {sorted(markers)}")
    c("markers map to the input chunk_ids",
      all(markers.get(i + 1) == h.chunk_id for i, h in enumerate(hits)))

    order = [int(m) for m in MARKER.findall(text)]
    c("markers appear in the text in order", order == [1, 2, 3], f"found {order}")

    leaked = next((h.chunk_id for h in hits if h.chunk_id in text), None)
    c("chunk_id is not leaked into the text", leaked is None,
      f"{leaked} appears in the assembled text — that is internal")

    c("every doc_id appears", all(h.doc_id in text for h in hits))
    c("every passage appears", all(h.text in text for h in hits))
    c("score shown to two decimals", all(f"{h.score:.2f}" in text for h in hits),
      "expected e.g. 0.71, not the full float")

    marker_line = next((ln for ln in text.splitlines() if "[1]" in ln), "")
    c("provenance is its own line, before the passage",
      bool(marker_line) and hits[0].text not in marker_line,
      "the [1] line also contains the passage text")
    c("blocks separated by a blank line", "\n\n" in text)

    resolvable, why = True, ""
    for seed in (11, 23, 42, 99):
        hs = sample(random.Random(seed).randint(1, 6), seed)
        try:
            p = mod.pack_context(hs)
        except Exception as exc:  # noqa: BLE001
            resolvable, why = False, f"raised on {len(hs)} hits: {type(exc).__name__}: {exc}"
            break
        ids = {h.chunk_id for h in hs}
        dangling = [m for m in MARKER.findall(p.text) if p.markers.get(int(m)) not in ids]
        if dangling:
            resolvable = False
            why = (f"with {len(hs)} hits, marker(s) {dangling} in the text resolve to "
                   f"{[p.markers.get(int(m)) for m in dangling]}, which was not in the input")
            break
    c("every marker resolves to a real chunk_id, over random inputs", resolvable,
      why or "this is the property the unit is about")

    # Deliberately guarded. The no-results path is the one people forget, and an unhandled
    # traceback here would lose every named failure above it — the grader would report
    # "crashed" instead of "these three checks failed", which is strictly less useful.
    try:
        empty = mod.pack_context([])
        ok = isinstance(empty.text, str) and not empty.markers
        detail = "" if ok else f"got text={empty.text!r}, markers={empty.markers!r}"
    except Exception as exc:  # noqa: BLE001
        ok, detail = False, f"{type(exc).__name__}: {exc} — retrieval returns nothing sometimes"
    c("empty input yields no markers and does not crash", ok, detail)

    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
