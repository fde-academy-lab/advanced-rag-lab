"""Grading the graders.

A check that has never rejected anything is not evidence that it works. It is a function that
returns True, and there is no way to tell those apart by reading it.

So every unit ships a `reference/` directory with two kinds of subdirectory:

    reference/pass/            a worked answer. The grader must accept it.
    reference/fail-<name>/     a wrong answer that looks right. The grader must reject it,
                               and `expect.yaml` names *which* check has to catch it.

The decoys carry more weight than the reference. `fail-format-only` for R1 is a citation packer
that produces beautifully formatted blocks whose markers point at nothing — the exact thing a
learner ships when they read the brief as a formatting task. If the checks stop catching that,
the unit has quietly become a string-formatting exercise and nobody would notice from the
outside. This module is what notices.

It runs in CI on every change under `lab-simulator/`, and it is the reason a claim that a unit
is graded honestly is checkable rather than asserted.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

from .grader import grade
from .model import Unit
from .registry import ROOT, all_units


@dataclasses.dataclass
class Case:
    unit: Unit
    name: str            # "pass" or "fail-format-only"
    directory: Path
    should_pass: bool
    expect_failures: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.unit.uid}/{self.name}"


@dataclasses.dataclass
class CaseOutcome:
    case: Case
    ok: bool
    why: str
    duration: float = 0.0


def _expectations(directory: Path) -> tuple[str, ...]:
    path = directory / "expect.yaml"
    if not path.exists():
        return ()
    import yaml
    data = yaml.safe_load(path.read_text()) or {}
    return tuple(str(x) for x in (data.get("fails") or []))


def cases(unit: Unit) -> list[Case]:
    ref = unit.directory / "reference"
    if not ref.is_dir():
        return []
    out: list[Case] = []
    for d in sorted(p for p in ref.iterdir() if p.is_dir()):
        if d.name == "pass":
            out.append(Case(unit, d.name, d, should_pass=True))
        elif d.name.startswith("fail-"):
            out.append(Case(unit, d.name, d, should_pass=False,
                            expect_failures=_expectations(d)))
    return out


def structural_gaps(unit: Unit) -> list[str]:
    """What is missing before this unit can be trusted, independent of running anything."""
    found = cases(unit)
    gaps = []
    if not any(c.should_pass for c in found):
        gaps.append("no reference/pass — the grader has never been shown a correct answer, "
                    "so 'the checks pass' is an untested claim")
    if not any(not c.should_pass for c in found):
        gaps.append("no reference/fail-* decoy — a check that has never rejected anything is "
                    "indistinguishable from a check that always returns true")
    for c in found:
        if not c.should_pass and not c.expect_failures:
            gaps.append(f"{c.name}/expect.yaml does not name the check that must catch it; "
                        "a decoy rejected for the wrong reason is a passing test hiding a bug")
    return gaps


def run_case(case: Case) -> CaseOutcome:
    result = grade(case.unit, case.directory)
    if case.should_pass:
        if result.passed:
            return CaseOutcome(case, True, "accepted", result.duration)
        detail = "; ".join(result.failures) or "; ".join(result.messages[-3:]) or "no detail"
        return CaseOutcome(case, False,
                           f"the reference answer was REJECTED — {detail}", result.duration)

    if result.passed:
        return CaseOutcome(case, False,
                           "the decoy was ACCEPTED — this unit no longer discriminates",
                           result.duration)

    # Both, because the two gates report differently: check.py names its failures, while the
    # decision gate never runs check.py at all and speaks only through messages.
    caught = list(result.failures) + list(result.messages)
    missed = [want for want in case.expect_failures
              if not any(want.lower() in got.lower() for got in caught)]
    if missed:
        return CaseOutcome(
            case, False,
            "rejected, but not by the check that was supposed to catch it. Expected a failure "
            f"matching {missed!r}; got {sorted(set(caught)) or 'no named failures'}",
            result.duration)
    return CaseOutcome(case, True, "rejected, by the intended check", result.duration)


def run_all(units: list[Unit] | None = None) -> tuple[list[CaseOutcome], dict[str, list[str]]]:
    units = list(units if units is not None else all_units())
    gaps = {u.uid: g for u in units if (g := structural_gaps(u))}
    outcomes = [run_case(c) for u in units for c in cases(u)]
    return outcomes, gaps


def format_report(outcomes: list[CaseOutcome], gaps: dict[str, list[str]]) -> str:
    lines = []
    for uid, items in sorted(gaps.items()):
        for item in items:
            lines.append(f"  MISSING  {uid}  {item}")
    for o in outcomes:
        mark = "ok      " if o.ok else "BROKEN  "
        lines.append(f"  {mark} {o.case.label:<34} {o.why}")
    if not lines:
        lines.append("  nothing to self-test — no units define a reference/ directory")
    return "\n".join(lines)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
