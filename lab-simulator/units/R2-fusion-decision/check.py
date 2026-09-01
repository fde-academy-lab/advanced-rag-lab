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
    "which leg is actually stronger here":
        r"dense|lsa|latent|paraphrase|semantic|bm25 is (the )?weak|lexical is (the )?weak"
        r"|weaker leg|stronger leg|term overlap",
    "what fusion needs in order to pay":
        r"complement|different quer|disjoint|overlap of failure|fail together|orthogonal"
        r"|same quer|correlat",
    "a gap inside the interval is not a gap":
        r"noise band|interval|confidence|ci\b|straddl|crosses zero|contains zero|not "
        r"significant|indistinguishable|cannot measure|can.t measure",
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

    c("decision names a specific configuration, not just 'hybrid'",
      bool(re.search(r"weight|rrf|reciprocal|alpha|α|bm25|dense|lsa|lexical|rank|single leg"
                     r"|one leg|no fusion", decision, re.I)),
      "say which configuration you would ship, and with what weight if it has one")

    touched = [name for name, pattern in CONCEPTS.items() if re.search(pattern, prose)]
    for name in CONCEPTS:
        c(f"engages with: {name}", name in touched)
    if len(touched) < len(CONCEPTS):
        c.note("A mechanism-level answer says why the legs behaved as they did, not which row "
               "of the table was highest.")
        c.note("Two questions it has to survive: which leg is the weak one, and what would have "
               "had to be true for fusion to pay? See hints 3 and 4.")

    c("`rejected` names a condition, not only a choice",
      bool(re.search(r"\bif\b|\bwhen\b|\bwould\b|\bunless\b|\bonce\b", rejected, re.I)),
      "what would have made the rejected option right?")

    # A falsifier that only repeats the evidence you were handed is not a falsifier.
    falsifier = str(data.get("would_change_if", "")).lower()
    c("falsifier is forward-looking, not a restatement of the given evidence",
      not re.fullmatch(r"[^a-z]*(rrf|equal weight|fusion)[^a-z]*"
                       r"(lost|loses|is worse|tied|ties|did not help)[^a-z]*", falsifier),
      "name something you could observe later that would change your mind")

    # The number in the brief that most people read as "slightly ahead".
    c("does not treat a gap inside the interval as a result",
      not re.search(r"(rrf|fusion|fused)\b[^.]{0,60}(slightly|marginally|a (little|bit|touch)) "
                    r"(better|ahead|higher|above)", prose),
      "+0.0008 with an interval of (-0.0101, +0.0109) is not slightly better. It is the sign "
      "of noise, and calling it slightly better is how complexity gets shipped")

    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
