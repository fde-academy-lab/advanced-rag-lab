#!/usr/bin/env python3
"""Checks for R2 · a decide-mode unit.

The grader has already enforced the generic decision gate — every field filled, and a falsifier
that is not the decision restated. This file adds what only this unit can judge: whether the
reasoning engages with the *mechanism* rather than summarising the table it was given.

That is checked by looking for the concepts a mechanism-level answer has to touch, not by
matching an expected answer. Several different decisions are defensible here; a decision that
never says why equal weight behaves as it does is not one of them.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, SolutionError, emit, run  # noqa: E402

# Concept -> the words that would appear if the writer engaged with it. Deliberately broad:
# this rewards touching the idea, not reproducing our phrasing.
CONCEPTS = {
    "the legs differ in strength": r"weak|strong|unequal|imbalanc|asymmetr|worse leg|better leg",
    "equal weight is the problem, not fusion": r"equal|parity|same weight|equally|uniform",
    "what rank-based fusion discards":
        r"scale|normali[sz]|score distribut|magnitude|discard|ignore",
}


def main(attempt: str) -> int:
    import yaml
    path = Path(attempt) / "decision.yaml"
    if not path.exists():
        raise SolutionError("No decision.yaml. Run `labsim start R2` and fill it in.")
    data = yaml.safe_load(path.read_text()) or {}
    c = Checker()

    decision = str(data.get("decision", ""))
    why = str(data.get("why", ""))
    rejected = str(data.get("rejected", ""))
    prose = f"{decision}\n{why}\n{rejected}".lower()

    c("decision names a specific rule, not just 'hybrid'",
      bool(re.search(r"weight|rrf|reciprocal|alpha|α|bm25|dense|rank", decision, re.I)),
      "say which rule, and with what weight")

    touched = [name for name, pattern in CONCEPTS.items() if re.search(pattern, prose)]
    for name in CONCEPTS:
        c(f"engages with: {name}", name in touched)
    if len(touched) < len(CONCEPTS):
        c.note("A mechanism-level answer explains *why* equal weight behaved as it did.")
        c.note("Summarising the table is not the same as explaining it — see hint 3.")

    c("`rejected` names a condition, not only a choice",
      bool(re.search(r"\bif\b|\bwhen\b|\bwould\b|\bunless\b|\bonce\b", rejected, re.I)),
      "what would have made the rejected option right?")

    # A falsifier that only repeats the evidence you were handed is not a falsifier.
    falsifier = str(data.get("would_change_if", "")).lower()
    c("falsifier is forward-looking, not a restatement of the given evidence",
      not re.fullmatch(r"[^a-z]*(rrf|equal weight)[^a-z]*(lost|loses|is worse)[^a-z]*", falsifier),
      "name something you could observe later that would change your mind")

    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
