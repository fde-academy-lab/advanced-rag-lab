"""What a unit is.

The design constraint that produced this shape: a practice problem where the only verb is
"implement" can teach syntax and cannot teach judgement. Retrieval work goes wrong through
*plausible* choices, so a unit has to be able to accept a plausible answer and tell you it is
worse — which means the grader needs a metric, not only a test.

Five modes, in the order a learner meets them:

    implement   fill the gap. The floor, and the only mode most practice sites have.
    diagnose    a working system is subtly broken. Find it, name the failure point, fix it.
    decide      no code. Commit a decision with its falsifier, before you are allowed to build.
    measure     implement, then clear a metric bar. Passing tests is not passing.
    ship        produce the artefact an FDE hands over: a PRD line, an ADR-lite, a dissection.

`decide` and `ship` are what make this a lab rather than a problem set, and they are the two
that carry the delivery lifecycle without ever announcing that they are doing so.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

MODES = ("implement", "diagnose", "decide", "measure", "ship")
DIFFICULTIES = ("easy", "medium", "hard", "brutal")

# Ordered, because a pathway is an order. Tracks are traversed roughly in this sequence,
# though prerequisites are what actually gate a unit.
TRACKS = ("foundations", "retrieval", "context", "evaluation", "cost", "agentic", "delivery")


@dataclasses.dataclass(frozen=True)
class Bar:
    """A metric threshold a solution must clear.

    `direction` matters more than it looks. Recall must go up; context precision at a fixed k
    goes *down* when recall goes up, and a bar that ignores direction quietly rewards the wrong
    trade.
    """
    metric: str
    threshold: float
    direction: str = "at_least"   # at_least | at_most
    note: str = ""

    def passes(self, value: float) -> bool:
        return value >= self.threshold if self.direction == "at_least" else value <= self.threshold

    def describe(self) -> str:
        arrow = "≥" if self.direction == "at_least" else "≤"
        return f"{self.metric} {arrow} {self.threshold:.4f}"


@dataclasses.dataclass(frozen=True)
class Unit:
    uid: str                      # R2, E1 — stable, referenced by prereqs
    slug: str
    title: str
    track: str
    difficulty: str
    minutes: int
    mode: str
    teaches: tuple[str, ...]
    prereqs: tuple[str, ...]
    bars: tuple[Bar, ...]
    artefact: str | None          # approach-note | adr-lite | measurement | dissection
    directory: Path
    summary: str = ""

    @property
    def has_brief(self) -> bool:
        return (self.directory / "BRIEF.md").exists()

    @property
    def needs_decision(self) -> bool:
        """A unit that ships a decision template requires one before its checks count."""
        return (self.directory / "decision.template.yaml").exists()

    def validate(self) -> list[str]:
        problems = []
        # `id` and `title` used to be read with `meta["..."]`, so a unit.yaml missing either
        # raised while the registry was being built and took every other unit down with it.
        # They are read defensively now, which means validate() owes the report.
        if not self.uid:
            problems.append("unit.yaml has no `id`")
        if not self.title:
            problems.append("unit.yaml has no `title`")
        if self.mode not in MODES:
            problems.append(f"mode {self.mode!r} not in {MODES}")
        if self.difficulty not in DIFFICULTIES:
            problems.append(f"difficulty {self.difficulty!r} not in {DIFFICULTIES}")
        if self.track not in TRACKS:
            problems.append(f"track {self.track!r} not in {TRACKS}")
        if not self.has_brief:
            problems.append("no BRIEF.md — a unit without a brief is a puzzle, not a lesson")
        if not (self.directory / "check.py").exists():
            problems.append("no check.py")
        if self.mode == "measure" and not self.bars:
            problems.append("mode is 'measure' but no metric bar is set")
        if self.mode == "ship" and not self.artefact:
            problems.append("mode is 'ship' but no artefact is named")
        return problems
