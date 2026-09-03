"""What a unit is.

The design constraint that produced this shape: a practice problem where the only verb is
"implement" can teach syntax and cannot teach judgement. Retrieval work goes wrong through
*plausible* choices, so a unit has to be able to accept a plausible answer and tell you it is
worse — which means the grader needs a metric, not only a test.

Six modes, in the order a learner meets them:

    implement   fill the gap. The floor, and the only mode most practice sites have.
    diagnose    a working system is subtly broken. Find it, name the failure point, fix it.
    answer      no code. Commit to a number, a ranking or a choice before you look — a
                prediction the grader compares to what the harness actually measured.
    decide      no code. Commit a decision with its falsifier, before you are allowed to build.
    measure     implement, then clear a metric bar. Passing tests is not passing.
    ship        produce the artefact an FDE hands over: a PRD line, an ADR-lite, a dissection.

`decide` and `ship` are what make this a lab rather than a problem set, and they are the two
that carry the delivery lifecycle without ever announcing that they are doing so. `answer` is
what makes it a *calibration* lab: the difference between "I would expect recall to drop" and
"I expect 0.50 at k=3, and I was 0.15 too optimistic" is the whole of judgement.

Two kinds, orthogonal to mode:

    unit        25–45 minutes, three gates, a real corpus behind it. The pathway's spine.
    drill       5–15 minutes, one idea, one check that carries it. Bite-sized, tagged by
                difficulty, and the thing to do on a weekday evening. Drills sit in the same
                prerequisite graph as units, so clearing one unlocks the next.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

MODES = ("implement", "diagnose", "answer", "decide", "measure", "ship")
KINDS = ("unit", "drill")
DRILL_MAX_MINUTES = 15
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
class Coaching:
    """What to say when a particular check fails — written by the unit's author, not generated.

    `matches` is a case-insensitive substring of the check's name. `work_on` is one sentence
    naming the skill, not the fix. `read` is a repository path the learner can open. The reply
    is assembled from these, which is why it can be specific without being generated: every
    sentence in it was written by somebody who knew what the check was for.
    """
    matches: str
    work_on: str
    read: str = ""


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
    kind: str = "unit"            # unit | drill
    reading: tuple[str, ...] = ()           # repository paths worth opening after this
    coaching: tuple[Coaching, ...] = ()     # per-check "what to work on", see Coaching

    @property
    def is_drill(self) -> bool:
        return self.kind == "drill"

    @property
    def needs_answer(self) -> bool:
        """An `answer` unit is graded on answer.yaml rather than on code."""
        return self.mode == "answer"

    def coach(self, check: str) -> Coaching | None:
        """The note for a check, matched loosely in both directions.

        The grader passes a full check name and the note's `matches` is a fragment of it. A
        learner typing `/why strongest single leg` passes a fragment and the note's key may be
        the longer string. Either containment counts, so both callers find the same note.
        """
        low = check.lower().strip()
        if not low:
            return None
        return next((c for c in self.coaching
                     if c.matches.lower() in low or low in c.matches.lower()), None)

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
        if self.kind not in KINDS:
            problems.append(f"kind {self.kind!r} not in {KINDS}")
        if self.is_drill and self.minutes > DRILL_MAX_MINUTES:
            problems.append(f"a drill is {self.minutes} minutes; the cap is {DRILL_MAX_MINUTES}. "
                            "Longer than that is a unit, and should say so")
        if self.mode == "answer" and not (self.directory / "answer.template.yaml").exists():
            problems.append("mode is 'answer' but there is no answer.template.yaml to fill in")
        for c in self.coaching:
            if not c.work_on.strip():
                problems.append(f"coaching for {c.matches!r} has no `work_on` text")
            if c.read and not (self.directory.parents[2] / c.read).exists():
                problems.append(f"coaching for {c.matches!r} points at {c.read}, which "
                                "does not exist")
        for path in self.reading:
            if not (self.directory.parents[2] / path).exists():
                problems.append(f"reading points at {path}, which does not exist")
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
