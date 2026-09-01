"""Turning a grading run into something worth reading on a pull request.

A CI comment that says "3 checks failed" costs the reader a round trip into the log, and on a
learning repository that round trip is where people give up. So the comment carries the named
checks, the messages the unit wrote for exactly this failure, and — when the unit clears — what
it unlocked and where the worked answer lives.

There is one piece of integrity logic here rather than in the workflow file, because it is a
rule about the lab and not about YAML: a pull request that edits an attempt *and* the checks
that grade it is not graded. That is not an accusation. It is that the result would mean
nothing, and a green tick that means nothing is worse than a red one.
"""
from __future__ import annotations

import re
from pathlib import Path

from .grader import Result, grade
from .model import Unit
from .registry import all_units, by_id, unlocked
from .selftest import CaseOutcome, format_report

ATTEMPT_PATH = re.compile(r"^lab-simulator/attempts/([A-Za-z]\d+)/")
UNIT_PATH = re.compile(r"^lab-simulator/units/([^/]+)/")
ENGINE_PATH = re.compile(r"^lab-simulator/labsim/")
MARKER = "<!-- labsim-report -->"


def _changed(paths: list[str], pattern: re.Pattern) -> list[str]:
    seen = []
    for p in paths:
        m = pattern.match(p.strip())
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def touched_attempts(paths: list[str]) -> list[Unit]:
    """Units whose attempt directory changed, in pathway order."""
    ids = {uid.upper() for uid in _changed(paths, ATTEMPT_PATH)}
    return [u for u in all_units() if u.uid.upper() in ids]


def touched_units(paths: list[str]) -> list[str]:
    return _changed(paths, UNIT_PATH)


def touches_engine(paths: list[str]) -> bool:
    return any(ENGINE_PATH.match(p.strip()) for p in paths)


def graded_units_are_also_edited(paths: list[str]) -> list[str]:
    """Unit directories that were edited while one of their own attempts was submitted."""
    attempts = {u.uid.upper() for u in touched_attempts(paths)}
    clashing = []
    for slug in touched_units(paths):
        unit = next((u for u in all_units() if u.directory.name == slug), None)
        if unit and unit.uid.upper() in attempts:
            clashing.append(unit.uid)
    return clashing


# ---------------------------------------------------------------- rendering


def _result_block(r: Result) -> str:
    out = []
    head = "PASSED" if r.passed else "not yet"
    out.append(f"### {'✅' if r.passed else '❌'} `{r.unit.uid}` · {r.unit.title} — **{head}**")
    out.append("")
    meta = f"`{r.unit.mode}` · {r.unit.difficulty} · {r.unit.track} · graded in {r.duration:.1f}s"
    out.append(meta)
    out.append("")

    if r.decision_ok is not None:
        out.append(f"- {'✅' if r.decision_ok else '❌'} **decision** — filled, and the "
                   "falsifier names an observation")
    if r.checks_ok is not None:
        out.append(f"- {'✅' if r.checks_ok else '❌'} **checks**")
    for desc, ok, value in r.bars:
        shown = f"{value:.4f}" if value is not None else "not reported"
        out.append(f"- {'✅' if ok else '❌'} **bar** `{desc}` — got `{shown}`")
    out.append("")

    if r.failures:
        out.append("<details open><summary>Checks that failed</summary>")
        out.append("")
        for f in r.failures:
            out.append(f"- `{f}`")
        out.append("")
        out.append("</details>")
        out.append("")
    if r.messages:
        out.append("<details><summary>Grader output</summary>")
        out.append("")
        out.append("```")
        out.extend(m for m in r.messages if m.strip())
        out.append("```")
        out.append("")
        out.append("</details>")
        out.append("")

    if r.passed:
        sol = r.unit.directory / "SOLUTION.md"
        if sol.exists():
            # Deliberately a path and not a link: relative URLs in a pull-request comment
            # resolve against the PR page, not the tree, and produce a 404.
            out.append(f"How we did it, and the two things we got wrong first: "
                       f"`{sol.relative_to(sol.parents[3])}`")
        nxt = [u.uid for u in unlocked({r.unit.uid}) if r.unit.uid in u.prereqs]
        if nxt:
            out.append("")
            out.append(f"Unlocked: {', '.join(f'`{x}`' for x in nxt)}")
    else:
        out.append(f"Locally: `cd lab-simulator && python -m labsim check {r.unit.uid}` — "
                   "same code path, same result, faster loop.")
    out.append("")
    return "\n".join(out)


def attempt_report(paths: list[str]) -> tuple[str, bool]:
    """The PR comment for submitted attempts. Returns (markdown, everything_passed)."""
    units = touched_attempts(paths)
    if not units:
        return "", True

    clash = graded_units_are_also_edited(paths)
    if clash:
        body = (f"{MARKER}\n## 🧪 L.A.B. Simulator\n\n"
                f"**Not graded.** This pull request changes an attempt for "
                f"{', '.join(f'`{c}`' for c in clash)} and also changes the unit's own "
                f"`check.py` or brief.\n\n"
                "That is not an accusation — people fix typos in briefs while solving them. "
                "It is that a result produced by checks the same commit edited does not mean "
                "anything, and a green tick that means nothing is worse than a red one.\n\n"
                "Split it into two pull requests: the unit fix, then the attempt.\n")
        return body, False

    results = [grade(u) for u in units]
    passed = all(r.passed for r in results)
    n_ok = sum(1 for r in results if r.passed)

    head = (f"{MARKER}\n## 🧪 L.A.B. Simulator — {n_ok}/{len(results)} graded clear\n")
    return head + "\n" + "\n".join(_result_block(r) for r in results), passed


def selftest_report(outcomes: list[CaseOutcome], gaps: dict[str, list[str]]) -> str:
    broken = [o for o in outcomes if not o.ok]
    head = "## 🔬 Unit self-test\n"
    if not broken and not gaps:
        head += (f"\n{len(outcomes)} reference cases across "
                 f"{len({o.case.unit.uid for o in outcomes})} units behaved as the units claim "
                 "they do: every worked answer accepted, every decoy rejected by the check "
                 "that was supposed to catch it.\n")
        return head
    head += "\n```\n" + format_report(outcomes, gaps) + "\n```\n"
    if broken:
        head += ("\nA decoy that gets accepted means the unit has stopped discriminating: it "
                 "still passes, but it no longer teaches the thing it is named after.\n")
    return head


def resolve(ids: list[str]) -> list[Unit]:
    out = []
    for uid in ids:
        u = by_id(uid)
        if u is None:
            raise SystemExit(f"no unit {uid!r}")
        out.append(u)
    return out


def read_paths(source: str | None) -> list[str]:
    """Changed paths, from a file (one per line) or from stdin."""
    import sys
    if source and source != "-":
        return Path(source).read_text().splitlines()
    return sys.stdin.read().splitlines()
