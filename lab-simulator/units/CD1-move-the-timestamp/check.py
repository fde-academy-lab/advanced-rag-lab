#!/usr/bin/env python3
"""CD1 · two requests, and how many leading bytes they share."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

REQ_A = ("Which region did the lag start in?", ["[1] ingest lag began in ap-southeast-2"],
         "2026-09-01T10:00:00")
REQ_B = ("Who approved the rollback?", ["[1] the rollback for PagerDuty-4471 was approved"],
         "2026-09-01T10:00:07")


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("assemble",))
    c = Checker()
    a, b = mod.assemble(*REQ_A), mod.assemble(*REQ_B)
    shared = len(os.path.commonprefix([a, b]))
    stable = len(mod.SYSTEM) + len(mod.INSTRUCTIONS)
    c.note(f"the two prompts share {shared} leading bytes; the stable text alone is {stable}")

    c("stable blocks share a prefix across requests", shared >= stable,
      f"only {shared} bytes shared — something that changes per request sits in front of "
      "text that does not")
    c("the timestamp is still in the prompt", REQ_A[2] in a and REQ_B[2] in b,
      "the time was removed; the feature that needed it is gone")
    c("the evidence still comes before the question",
      a.find("Evidence:") != -1 and a.find("Evidence:") < a.find("Question:"),
      "the model reads blocks in order; evidence after the question is a different prompt")
    c("the system text still comes first", a.startswith(mod.SYSTEM[:40]),
      "the system block is the most stable thing you have; it belongs at the front")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
