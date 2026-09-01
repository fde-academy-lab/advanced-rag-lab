"""Grading an attempt.

Three gates, and they are checked in this order because that is the order in which failing
them is informative:

  1. **The decision.** If a unit ships a decision template, the attempt must fill it in — and
     the falsifier line must be a real observation, not a restatement of the decision. This
     gate exists because an engineer who writes the decision after the code has learned to
     rationalise rather than to decide, and no test can detect that afterwards.

  2. **The checks.** Ordinary assertions, run in a subprocess so a learner's infinite loop is a
     timeout rather than a hung grader.

  3. **The bars.** A metric threshold. Passing tests is not passing: a reranker that returns
     its input unchanged passes every structural test ever written for a reranker.
"""
from __future__ import annotations

import dataclasses
import json
import re
import subprocess
import sys
from pathlib import Path

from .model import Unit
from .registry import ROOT

CHECK_TIMEOUT = 600
PLACEHOLDER = re.compile(r"<[^>]{2,}>|TODO|FILL ?ME|\.\.\.$", re.I)

# A falsifier has to name something you could *observe*. These phrasings name the conclusion
# instead — "if it turns out to be wrong" is true of every decision ever made and tells the
# next reader nothing about when to revisit it. This is the commonest first-attempt shape.
TAUTOLOGY = re.compile(
    r"turn(s|ed)? out (to be|that).{0,20}(wrong|incorrect|bad|a mistake|not right)"
    r"|(is|was|were|proves? to be|proved) (the )?(wrong|incorrect|a mistake|not the right)"
    r"|does ?n.t work|doesn't work|did ?n.t work|didn't work"
    r"|if (it|this|that) fails|if we are wrong|if i am wrong|if it is wrong",
    re.I)


@dataclasses.dataclass
class Result:
    unit: Unit
    passed: bool
    decision_ok: bool | None
    checks_ok: bool | None
    bars: list[tuple[str, bool, float | None]]
    messages: list[str]
    duration: float = 0.0
    failures: tuple[str, ...] = ()      # the named checks that failed, from check.py

    def as_dict(self) -> dict:
        return {
            "id": self.unit.uid, "title": self.unit.title, "passed": self.passed,
            "decision_ok": self.decision_ok, "checks_ok": self.checks_ok,
            "bars": [{"bar": b, "passed": p, "value": v} for b, p, v in self.bars],
            "failures": list(self.failures),
            "messages": self.messages,
        }


def attempt_dir(unit: Unit) -> Path:
    return ROOT / "attempts" / unit.uid


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _grade_decision(unit: Unit, where: Path, out: list[str]) -> bool:
    """A filled decision, with a falsifier that is not the decision restated."""
    import yaml

    path = where / "decision.yaml"
    if not path.exists():
        out.append(f"No decision at {_rel(path)}. "
                   f"Run `labsim start {unit.uid}` and fill it in before writing code.")
        return False
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        out.append(f"decision.yaml does not parse: {exc}")
        return False

    ok = True
    for field in ("decision", "why", "rejected", "would_change_if"):
        value = str(data.get(field) or "").strip()
        if not value:
            out.append(f"decision.yaml: `{field}` is empty")
            ok = False
        elif PLACEHOLDER.search(value):
            out.append(f"decision.yaml: `{field}` still holds the template placeholder")
            ok = False
        elif len(value.split()) < 6:
            out.append(f"decision.yaml: `{field}` is {len(value.split())} words. "
                       "Six is a low bar and it is there to stop one-word answers")
            ok = False

    # The falsifier must name an observation, not the conclusion and not the decision.
    falsifier_raw = str(data.get("would_change_if") or "")
    if ok and TAUTOLOGY.search(falsifier_raw):
        out.append("decision.yaml: `would_change_if` names the conclusion rather than an "
                   "observation. \"If it turns out to be wrong\" is true of every decision "
                   "ever made. What would you *see*?")
        ok = False

    # It must also not simply repeat the decision.
    decision = str(data.get("decision") or "").lower()
    falsifier = str(data.get("would_change_if") or "").lower()
    if ok and decision and falsifier:
        shared = set(re.findall(r"[a-z]{4,}", decision)) & set(re.findall(r"[a-z]{4,}", falsifier))
        if len(shared) >= 4 and len(set(re.findall(r"[a-z]{4,}", falsifier)) - shared) < 4:
            out.append("decision.yaml: `would_change_if` mostly restates `decision`. "
                       "It has to name an observation that would make you wrong.")
            ok = False
    return ok


def _run_checks(unit: Unit, where: Path, out: list[str]) -> tuple[bool, dict]:
    """Run check.py in a subprocess. It prints a JSON line prefixed LABSIM_RESULT:."""
    proc = subprocess.run(
        [sys.executable, str(unit.directory / "check.py"), str(where)],
        capture_output=True, text=True, timeout=CHECK_TIMEOUT, cwd=str(ROOT.parent),
    )
    payload: dict = {}
    reported = False               # did check.py actually print a result block?
    for line in proc.stdout.splitlines():
        if line.startswith("LABSIM_RESULT:"):
            try:
                parsed = json.loads(line[len("LABSIM_RESULT:"):])
            except json.JSONDecodeError:
                continue
            # Valid JSON that is not an object used to reach `payload.get` and raise
            # AttributeError inside grade(). A malformed result is a failed run, not a crash.
            if isinstance(parsed, dict):
                payload, reported = parsed, True
            else:
                out.append("check.py reported a result that is not an object")
        else:
            out.append(line)
    if proc.returncode != 0 and not reported:
        tail = (proc.stderr or "").strip().splitlines()[-6:]
        out.extend(tail or ["check.py failed with no output"])
    # An exit code of 0 is not evidence that anything was checked.
    #
    # For the four units with no metric bar, `checks_ok` is the entire verdict, so a subprocess
    # that exits before running a single check was reported as cleared — `import os;
    # os._exit(0)` as solution.py graded green, and so did an attempt directory with no
    # solution.py in it at all. Requiring the result block makes "it ran and said nothing" a
    # failure, which is what it is.
    if proc.returncode == 0 and not reported:
        out.append("check.py exited cleanly without running any check — "
                   "no LABSIM_RESULT block was produced")
    return proc.returncode == 0 and reported, payload


def grade(unit: Unit, where: Path | None = None) -> Result:
    """Grade the work in `where`, defaulting to the learner's own attempt directory.

    The parameter is not decoration. CI grades a unit's *reference* directories with the same
    code path a learner runs, which is the only way a claim that the checks are trustworthy
    survives contact with the next person who edits a check.
    """
    import time
    started = time.time()
    where = attempt_dir(unit) if where is None else Path(where)
    messages: list[str] = []

    decision_ok = _grade_decision(unit, where, messages) if unit.needs_decision else None
    if decision_ok is False:
        return Result(unit, False, decision_ok, None, [], messages, time.time() - started)

    try:
        checks_ok, payload = _run_checks(unit, where, messages)
    except subprocess.TimeoutExpired:
        messages.append(f"checks did not finish in {CHECK_TIMEOUT}s — is something looping?")
        return Result(unit, False, decision_ok, False, [], messages, time.time() - started)

    metrics = payload.get("metrics", {}) or {}
    bar_results: list[tuple[str, bool, float | None]] = []
    for bar in unit.bars:
        value = metrics.get(bar.metric)
        if value is None:
            bar_results.append((bar.describe(), False, None))
            messages.append(f"check.py did not report `{bar.metric}`")
            continue
        ok = bar.passes(float(value))
        bar_results.append((bar.describe(), ok, float(value)))
        if not ok:
            messages.append(f"{bar.metric} = {float(value):.4f}, needs {bar.describe()}"
                            + (f" — {bar.note}" if bar.note else ""))

    passed = bool(checks_ok) and all(ok for _, ok, _ in bar_results) and decision_ok is not False
    return Result(unit, passed, decision_ok, checks_ok, bar_results, messages,
                  time.time() - started, tuple(payload.get("failures", []) or []))
