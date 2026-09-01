"""The L.A.B. Simulator engine.

The units have their own regression suite — `labsim selftest`, which grades each unit's worked
answer and decoys. This file tests the machinery underneath that: the pathway derivation, the
decision gate, the loader, and the pull-request plumbing.

The split matters. If the engine is wrong, every unit is wrong at once and the self-test cannot
see it, because the self-test runs *through* the engine.
"""
from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SIM = ROOT / "lab-simulator"
sys.path.insert(0, str(SIM))

pytest.importorskip("yaml")

from labsim import registry, report, selftest  # noqa: E402
from labsim.checkkit import Checker, SolutionError, load_solution  # noqa: E402
from labsim.grader import _grade_decision  # noqa: E402
from labsim.model import Bar, Unit  # noqa: E402

# --------------------------------------------------------------------- helpers

def make_unit(uid: str, prereqs: tuple[str, ...] = (), directory: Path | None = None,
              **kw) -> Unit:
    base = {"uid": uid, "slug": uid.lower(), "title": f"unit {uid}", "track": "retrieval",
            "difficulty": "easy", "minutes": 10, "mode": "implement", "teaches": (),
            "prereqs": prereqs, "bars": (), "artefact": None,
            "directory": directory or SIM / "units" / "nonexistent"}
    base.update(kw)
    return Unit(**base)


@pytest.fixture
def units(monkeypatch):
    """Swap the unit set for a synthetic one, cache included."""
    def install(*made: Unit):
        monkeypatch.setattr(registry.all_units, "__wrapped__", lambda: made, raising=False)
        monkeypatch.setattr(registry, "all_units", lambda: made)
        monkeypatch.setattr(report, "all_units", lambda: made)
        return made
    return install


# --------------------------------------------------------------------- the real units

def test_every_shipped_unit_is_structurally_sound():
    problems = registry.validate_all()
    assert not problems, "\n".join(f"{k}: {v}" for k, v in problems.items())


def test_the_pathway_starts_somewhere():
    """A pathway whose first wave is empty is a pathway nobody can enter."""
    waves = registry.pathway()
    assert waves and waves[0], "no unit has an empty prerequisite list"
    assert all(u.prereqs == () for u in waves[0])


def test_every_unit_is_reachable():
    reached = {u.uid for wave in registry.pathway() for u in wave}
    assert reached == {u.uid for u in registry.all_units()}


def test_estimated_minutes_are_plausible():
    for u in registry.all_units():
        assert 5 <= u.minutes <= 180, f"{u.uid} claims {u.minutes} minutes"


def test_briefs_name_the_unit_they_belong_to():
    for u in registry.all_units():
        head = (u.directory / "BRIEF.md").read_text().splitlines()[0]
        assert u.uid in head, f"{u.uid}'s brief opens with {head!r}"


# --------------------------------------------------------------------- pathway derivation

def test_waves_group_parallel_units_rather_than_inventing_an_order(units):
    units(make_unit("A"), make_unit("B"), make_unit("C", ("A", "B")))
    waves = registry.pathway()
    assert [[u.uid for u in w] for w in waves] == [["A", "B"], ["C"]]


def test_a_cycle_is_reported_rather_than_hanging(units):
    units(make_unit("A", ("B",)), make_unit("B", ("A",)))
    problems = registry.validate_all()
    assert any("cycle" in p for p in problems["A"])
    assert any("cycle" in p for p in problems["B"])


def test_a_cycle_does_not_make_pathway_loop_forever(units):
    units(make_unit("A", ("B",)), make_unit("B", ("A",)))
    waves = registry.pathway()
    assert [u.uid for u in waves[-1]] == ["A", "B"]


def test_a_prereq_that_does_not_exist_is_caught(units):
    units(make_unit("A", ("Z9",)))
    assert any("Z9 does not exist" in p for p in registry.validate_all()["A"])


def test_unlocked_respects_prerequisites(units):
    units(make_unit("A"), make_unit("B", ("A",)), make_unit("C", ("A", "B")))
    assert [u.uid for u in registry.unlocked(set())] == ["A"]
    assert [u.uid for u in registry.unlocked({"A"})] == ["B"]
    assert [u.uid for u in registry.unlocked({"A", "B"})] == ["C"]


# --------------------------------------------------------------------- bars

@pytest.mark.parametrize("direction,threshold,value,expected", [
    ("at_least", 0.78, 0.7891, True),
    ("at_least", 0.78, 0.7645, False),
    ("at_most", 0.0040, 0.0039, True),
    ("at_most", 0.0040, 0.0051, False),
])
def test_bar_direction(direction, threshold, value, expected):
    assert Bar("m", threshold, direction).passes(value) is expected


def test_a_measure_unit_without_a_bar_is_rejected():
    u = make_unit("M1", mode="measure")
    assert any("no metric bar" in p for p in u.validate())


def test_a_ship_unit_without_an_artefact_is_rejected():
    u = make_unit("S1", mode="ship")
    assert any("no artefact" in p for p in u.validate())


# --------------------------------------------------------------------- the decision gate

def write_decision(tmp_path: Path, **fields) -> Unit:
    body = "\n".join(f"{k}: {v!r}" for k, v in fields.items())
    (tmp_path / "decision.yaml").write_text(body)
    return make_unit("D1", mode="decide")


GOOD = {
    "decision": "Weighted score fusion with alpha near 0.2 on the dense leg",
    "why": "Fusion pays only when the legs fail on different queries, and here they do not",
    "rejected": "RRF, which would have been right if the legs failed on different queries",
    "would_change_if": "The per-query win rate between the legs moves toward an even split",
}


def gate(tmp_path, **overrides):
    fields = {**GOOD, **overrides}
    unit = write_decision(tmp_path, **fields)
    messages: list[str] = []
    return _grade_decision(unit, tmp_path, messages), messages


def test_a_complete_decision_passes(tmp_path):
    ok, messages = gate(tmp_path)
    assert ok, messages


def test_an_empty_field_is_caught(tmp_path):
    ok, messages = gate(tmp_path, why="")
    assert not ok and any("`why` is empty" in m for m in messages)


def test_a_left_in_placeholder_is_caught(tmp_path):
    ok, messages = gate(tmp_path, decision="<the rule you would ship, specifically>")
    assert not ok and any("placeholder" in m for m in messages)


def test_a_one_word_answer_is_caught(tmp_path):
    ok, messages = gate(tmp_path, decision="hybrid")
    assert not ok and any("words" in m for m in messages)


@pytest.mark.parametrize("falsifier", [
    "I would revisit this if the weighted approach turned out to be the wrong choice",
    "If it turns out to be wrong we will change the fusion rule we picked",
    "We would reconsider the whole thing if this approach does not work in practice",
    "I will change my mind about the fusion rule if I am wrong about the weighting",
])
def test_a_falsifier_that_names_the_conclusion_is_rejected(tmp_path, falsifier):
    """The commonest first-attempt shape, and the one the mode exists to train out."""
    ok, messages = gate(tmp_path, would_change_if=falsifier)
    assert not ok, f"accepted a tautology: {falsifier!r}"
    assert any("would_change_if" in m for m in messages)


def test_a_falsifier_that_restates_the_decision_is_rejected(tmp_path):
    ok, messages = gate(
        tmp_path,
        decision="Weighted score fusion with alpha near 0.2 on the dense leg",
        would_change_if="Weighted score fusion with alpha near 0.2 stops being the dense leg "
                        "rule")
    assert not ok and any("restates" in m for m in messages)


def test_a_real_observation_survives_the_tautology_filter(tmp_path):
    """The filter must not be so eager that it rejects honest falsifiers with 'wrong' in them."""
    ok, messages = gate(
        tmp_path,
        would_change_if="Latency at p95 crosses 400 ms on the fused path, or the tuned alpha "
                        "lands within the interval around 0.5")
    assert ok, messages


def test_a_missing_decision_says_what_to_run(tmp_path):
    unit = make_unit("D1", mode="decide")
    messages: list[str] = []
    assert _grade_decision(unit, tmp_path, messages) is False
    assert any("labsim start" in m for m in messages)


def test_unparseable_yaml_is_a_message_not_a_traceback(tmp_path):
    (tmp_path / "decision.yaml").write_text("decision: [unclosed\n")
    unit = make_unit("D1", mode="decide")
    messages: list[str] = []
    assert _grade_decision(unit, tmp_path, messages) is False
    assert any("does not parse" in m for m in messages)


# --------------------------------------------------------------------- the loader

DATACLASS_MODULE = textwrap.dedent('''
    from __future__ import annotations
    import dataclasses

    @dataclasses.dataclass
    class Packed:
        text: str
        markers: dict[int, str]

    def pack_context(hits):
        return Packed(text="", markers={})
''')


def test_loader_handles_future_annotations_with_dataclasses(tmp_path):
    """`from __future__ import annotations` + @dataclass needs the module in sys.modules first.

    Without that registration the failure is `AttributeError: 'NoneType' object has no
    attribute '__dict__'`, which tells a learner nothing and is not their fault.
    """
    (tmp_path / "solution.py").write_text(DATACLASS_MODULE)
    mod = load_solution(tmp_path, required=("pack_context",))
    assert mod.pack_context([]).markers == {}


def test_a_missing_solution_names_the_command(tmp_path):
    with pytest.raises(SolutionError, match="labsim start"):
        load_solution(tmp_path)


def test_a_missing_function_is_named(tmp_path):
    (tmp_path / "solution.py").write_text("x = 1\n")
    with pytest.raises(SolutionError, match="pack_context"):
        load_solution(tmp_path, required=("pack_context",))


def test_an_import_time_error_is_readable(tmp_path):
    (tmp_path / "solution.py").write_text("raise ValueError('boom')\n")
    with pytest.raises(SolutionError, match="ValueError: boom"):
        load_solution(tmp_path)


def test_checker_tracks_failures():
    c = Checker()
    c("first", True)
    c("second", False, "because")
    assert c.failures == ["second"] and not c.ok


# --------------------------------------------------------------------- pull-request plumbing

DIFF = [
    "README.md",
    "lab-simulator/attempts/R1/solution.py",
    "lab-simulator/attempts/R2/decision.yaml",
    "raglab/retrieve.py",
]


def test_changed_paths_map_to_units():
    assert [u.uid for u in report.touched_attempts(DIFF)] == ["R1", "R2"]


def test_a_diff_with_no_attempts_grades_nothing():
    body, ok = report.attempt_report(["docs/README.md"])
    assert body == "" and ok


def test_editing_the_checks_that_grade_your_own_attempt_is_not_graded():
    """Not an accusation. A result produced by checks the same commit edited means nothing."""
    slug = report.all_units()[0].directory.name
    uid = report.all_units()[0].uid
    paths = [f"lab-simulator/attempts/{uid}/solution.py",
             f"lab-simulator/units/{slug}/check.py"]
    assert report.graded_units_are_also_edited(paths) == [uid]
    body, ok = report.attempt_report(paths)
    assert not ok and "Not graded" in body and report.MARKER in body


def test_editing_a_different_unit_is_fine():
    other = [u for u in report.all_units() if u.uid != "R1"][0]
    paths = ["lab-simulator/attempts/R1/solution.py",
             f"lab-simulator/units/{other.directory.name}/BRIEF.md"]
    assert report.graded_units_are_also_edited(paths) == []


def test_engine_changes_are_detected():
    assert report.touches_engine(["lab-simulator/labsim/grader.py"])
    assert not report.touches_engine(["lab-simulator/units/R1-x/check.py"])


# --------------------------------------------------------------------- the self-test itself

def test_a_unit_with_no_reference_is_reported_as_untrustworthy(tmp_path):
    gaps = selftest.structural_gaps(make_unit("X1", directory=tmp_path))
    assert any("reference/pass" in g for g in gaps)
    assert any("decoy" in g for g in gaps)


def test_a_decoy_without_an_expectation_is_reported(tmp_path):
    (tmp_path / "reference" / "pass").mkdir(parents=True)
    (tmp_path / "reference" / "fail-something").mkdir(parents=True)
    gaps = selftest.structural_gaps(make_unit("X1", directory=tmp_path))
    assert any("expect.yaml" in g for g in gaps)


def test_every_shipped_unit_accepts_its_reference_and_rejects_its_decoys():
    """The end-to-end promise, run here as well as in its own workflow job.

    Slow enough to notice and cheap enough to keep: if this breaks, no unit in the pathway can
    be trusted, and that is worth finding in the ordinary test run.
    """
    outcomes, gaps = selftest.run_all()
    assert not gaps, gaps
    broken = [f"{o.case.label}: {o.why}" for o in outcomes if not o.ok]
    assert not broken, "\n".join(broken)


# --------------------------------------------------------------- briefs and hints

def test_every_unit_ships_hints():
    """`/hint` is the one affordance a stuck learner has in Discussions. It has to exist."""
    from labsim.brief import hints
    thin = {u.uid: len(hints((u.directory / "BRIEF.md").read_text()))
            for u in registry.all_units()}
    assert all(n >= 2 for n in thin.values()), thin


def test_hints_are_numbered_in_order():
    from labsim.brief import hints
    for u in registry.all_units():
        got = hints((u.directory / "BRIEF.md").read_text())
        assert [h.number for h in got] == list(range(1, len(got) + 1)), u.uid


def test_rendering_a_brief_hides_the_hint_bodies():
    """The point of a collapsed hint is that reading it is a decision."""
    from labsim.brief import hints, render
    unit = registry.by_id("R2")
    md = (unit.directory / "BRIEF.md").read_text()
    out = render(md, width=90, colour=False)
    for h in hints(md):
        body = " ".join(h.body.split())[:60]
        assert body not in " ".join(out.split()), f"hint {h.number} leaked into the render"
        assert h.summary.split("—")[0].strip() in out, "the hint's teaser should still show"


def test_rendering_strips_markup_but_keeps_tables():
    from labsim.brief import render
    md = "# Title\n\nSome **bold** and `code`.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    out = render(md, width=80, colour=False)
    assert "**" not in out and "`" not in out
    assert "| a | b |" in out


# --------------------------------------------------------------- the discussions bridge

FORM_BODY = """### Which unit

R1 — Make a citation resolve

### Your approach, before the code

Map each marker to the chunk it came from.

### Your solution.py

```python
def pack_context(hits):
    return None
```

### What surprised you

The randomised check.
"""


def test_a_form_submission_is_parsed():
    from labsim.discussion import parse_submission
    sub = parse_submission("R1 · attempt", FORM_BODY)
    assert sub.unit_id == "R1"
    assert "solution.py" in sub.files and "pack_context" in sub.files["solution.py"]
    assert sub.reflection.startswith("The randomised")
    assert sub.usable


def test_a_submission_that_ignored_the_form_is_still_parsed():
    """Refusing a submission on a formatting technicality is how you stop getting submissions."""
    from labsim.discussion import parse_submission
    sub = parse_submission("my go at R2", "here you are\n\n```yaml\ndecision: ship dense\n```")
    assert sub.unit_id == "R2" and "decision.yaml" in sub.files


def test_a_submission_naming_no_real_unit_is_not_usable():
    from labsim.discussion import parse_submission
    assert not parse_submission("Z9 · hello", "```python\nx = 1\n```").usable


@pytest.mark.parametrize("text,expected", [
    ("/check", ("check", None)),
    ("  /hint", ("hint", None)),
    ("stuck. /hint 3", ("hint", 3)),
    ("/solution please", ("solution", None)),
    ("nothing to see", None),
    ("see docs/check for this", None),
])
def test_commands_are_recognised_where_people_actually_write_them(text, expected):
    from labsim.discussion import parse_command
    assert parse_command(text) == expected


def test_a_command_inside_a_code_fence_is_not_a_command():
    """A pasted diff containing /check must not re-grade somebody's thread."""
    from labsim.discussion import parse_command
    assert parse_command("look:\n\n```\nrm /check\n```\n") is None


def test_the_grade_reply_carries_a_machine_readable_tag():
    """The weekly digest tallies these. If the format drifts, the digest silently empties."""
    from labsim.discussion import render_grade
    from labsim.grader import grade
    unit = registry.by_id("R1")
    result = grade(unit, unit.directory / "reference" / "fail-cites-the-document")
    body = render_grade("R1", result, repo="o/r")
    assert "<!-- labsim-bot -->" in body
    assert re.search(r"<!-- labsim:R1:fail:[^>]*-->", body)
    assert "markers map to the input chunk_ids" in body


def test_solution_is_gated_until_the_thread_clears():
    from labsim.discussion import render_solution
    closed = render_solution("R1", passed=False)
    assert "stays closed" in closed and "SOLUTION.md" in closed
    opened = render_solution("R1", passed=True)
    assert "cleared" in opened


def test_hint_replies_walk_forward_and_stop():
    from labsim.discussion import render_hint
    first = render_hint("R2", None)
    assert "hint 1 of 4" in first and "/hint 2" in first
    last = render_hint("R2", 4)
    assert "last hint" in last
    past = render_hint("R2", 9)
    assert "asked for 9" in past


# --------------------------------------------------------------- the bot's sanitiser

def test_the_bot_neutralises_mentions_and_foreign_html():
    """The grade job runs a stranger's code and writes the reply. Assume the reply is hostile."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from discussion_bot import sanitise
    out = sanitise("<!-- labsim-bot -->\nping @everyone\n<!-- payload -->\n"
                   "<!-- labsim:R1:pass: -->")
    assert "`@everyone`" in out, "a mention must survive as text"
    assert not re.search(r"(?<!`)@everyone", out), "…but not as a live mention"
    assert "<!-- payload -->" not in out
    assert "<!-- labsim:R1:pass: -->" in out, "our own tags must survive"


def test_the_bot_adds_its_marker_when_missing():
    sys.path.insert(0, str(ROOT / "scripts"))
    from discussion_bot import sanitise
    assert sanitise("bare text").startswith("<!-- labsim-bot -->")


# ------------------------------------------- the form GitHub actually renders

def rendered_form(**fields) -> str:
    """A discussion body in the exact shape GitHub produces from a category form.

    Two details of that shape are load-bearing and neither is obvious from the YAML: an
    untouched optional textarea becomes the literal `_No response_` rather than being omitted,
    and every field label becomes an `###` heading — including the prose ones.
    """
    labels = [
        ("unit", "Which unit"),
        ("approach", "Your approach, before the code"),
        ("solution", "Your solution.py"),
        ("decision", "Your decision.yaml"),
        ("measurement", "Your measurement.md"),
        ("surprised", "What surprised you"),
    ]
    out = []
    for key, label in labels:
        out.append(f"### {label}\n\n{fields.get(key, '_No response_')}\n")
    out.append("### Before you post\n\n- [X] I read the brief\n")
    return "\n".join(out)


def test_the_form_labels_match_what_the_parser_looks_for():
    """The contract between the YAML and the parser, checked against the YAML itself."""
    import yaml as _yaml
    from labsim.discussion import _target_file
    form = _yaml.safe_load(
        (ROOT / ".github" / "DISCUSSION_TEMPLATE" / "lab-simulator.yml").read_text())
    labels = {f["attributes"]["label"]: f.get("id")
              for f in form["body"] if f.get("type") != "markdown"}
    for label, field_id in labels.items():
        target = _target_file(label)
        if field_id in ("solution", "decision", "measurement"):
            assert target, f"form field {label!r} feeds no file"
        else:
            assert target is None, (
                f"form field {label!r} is prose and would be written to {target}. "
                "'Your approach, before the code' contains 'code' — a loose match captures it.")


def test_an_untouched_optional_field_is_not_a_file():
    """`_No response_` is what GitHub writes for a blank optional textarea, not content.

    Taken at face value it becomes a file: a P1 attempt that left the note blank was graded
    against a measurement.md whose entire contents were the words "_No response_".
    """
    from labsim.discussion import parse_submission
    sub = parse_submission("[R1] attempt", rendered_form(
        unit="R1 — Make a citation resolve (implement, easy)",
        solution="```python\ndef pack_context(hits):\n    return None\n```",
        surprised="The randomised check."))
    assert sub.unit_id == "R1"
    assert list(sub.files) == ["solution.py"], sub.files
    assert sub.reflection == "The randomised check."


def test_code_in_the_approach_field_is_not_taken_as_the_solution():
    """Somebody sketching an approach in code must not be graded on that sketch."""
    from labsim.discussion import parse_submission
    sub = parse_submission("[R1] attempt", rendered_form(
        unit="R1 — Make a citation resolve",
        approach="Roughly:\n\n```python\n# map marker -> chunk_id, then format\n```",
        solution="```python\nREAL = True\n```"))
    assert sub.files["solution.py"].strip() == "REAL = True"


def test_an_approach_with_code_and_no_solution_submits_nothing():
    """Better to say 'no code to grade' than to grade the wrong field."""
    from labsim.discussion import parse_submission
    sub = parse_submission("[R1] attempt", rendered_form(
        unit="R1 — Make a citation resolve",
        approach="```python\n# just thinking out loud\n```"))
    assert not sub.files and not sub.usable


def test_the_unit_comes_from_the_dropdown_when_the_title_placeholder_is_left_in():
    """The form's title prefill is `[UNIT] · ` and people submit it unedited."""
    from labsim.discussion import parse_submission
    sub = parse_submission("[UNIT] · my first go", rendered_form(
        unit="R2 — Decide whether to fuse at all (decide, medium)",
        decision="```yaml\ndecision: ship dense alone\n```"))
    assert sub.unit_id == "R2" and list(sub.files) == ["decision.yaml"]


def test_a_prose_measurement_note_still_arrives_without_a_fence():
    """P1 says prose is fine. The `_No response_` guard must not break that."""
    from labsim.discussion import parse_submission
    sub = parse_submission("[P1] note", rendered_form(
        unit="P1 — Write the measurement note that survives you leaving",
        measurement="# Measurement\n\n- **Date** 2026-09-01\n- **Command** `x`"))
    assert "measurement.md" in sub.files
    assert sub.files["measurement.md"].startswith("# Measurement")


# ─────────────────────────────────────────── a grader that cannot be told nothing ──
#
# Every `reference/pass` and `reference/fail-*` directory holds a solution that loads, so
# `labsim selftest` only ever exercised check.py's normal path. Off it, the grader was
# reporting a pass for work that does not exist: `run()` turned a SolutionError into
# `emit({})`, which exits 0, and `grade()` took an exit code of 0 as "the checks passed". Four
# of the seven units declare `bars: []`, so for those there was nothing else left to fail on.
#
# These grade real units through the real entry point, because the bug lived in the seam
# between two functions that were each individually correct.
UNBARRED = ("R1", "E1", "F1", "P1")


@pytest.mark.parametrize("uid", UNBARRED)
def test_an_empty_attempt_directory_does_not_pass(uid, tmp_path):
    from labsim.grader import grade
    from labsim.registry import by_id
    result = grade(by_id(uid), tmp_path)
    assert result.passed is False, (
        f"{uid} graded an attempt directory with nothing in it as a pass")
    assert result.checks_ok is False
    assert result.failures, "the reason has to survive into the reply the learner sees"


@pytest.mark.parametrize("uid", UNBARRED[:3])          # P1 grades prose, not a module
def test_a_solution_that_will_not_import_does_not_pass(uid, tmp_path):
    from labsim.grader import grade
    from labsim.registry import by_id
    (tmp_path / "solution.py").write_text("def broken(:\n")
    result = grade(by_id(uid), tmp_path)
    assert result.passed is False, f"{uid} graded a SyntaxError as a pass"
    assert any("SyntaxError" in f for f in result.failures), result.failures


@pytest.mark.parametrize("uid", UNBARRED[:3])
def test_a_solution_that_kills_the_process_does_not_pass(uid, tmp_path):
    """`import os; os._exit(0)` skips every check and exits 0. That used to be a pass.

    It matters more than an ordinary bug because the Discussions bot executes code written by
    strangers and publishes the verdict, so this is the shape of a grader that can be told
    what to say.
    """
    from labsim.grader import grade
    from labsim.registry import by_id
    (tmp_path / "solution.py").write_text("import os\nos._exit(0)\n")
    result = grade(by_id(uid), tmp_path)
    assert result.passed is False, f"{uid} graded a process that ran no check as a pass"
    assert any("no LABSIM_RESULT" in m for m in result.messages), result.messages


def test_emit_without_failures_still_returns_zero():
    """The fix must not turn a clean run red. `emit()` with no failures is still a pass."""
    from labsim.checkkit import emit
    assert emit({}) == 0
    assert emit({"x": 1}) == 0
    assert emit({}, failures=["no solution.py"]) == 1


def test_a_result_line_that_is_not_an_object_is_a_failure_not_a_crash(tmp_path, monkeypatch):
    """Valid JSON that is not a dict reached `payload.get` and raised AttributeError."""
    import subprocess

    from labsim import grader

    class Proc:
        stdout = 'LABSIM_RESULT:["not", "an", "object"]\n'
        stderr = ""
        returncode = 0

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: Proc())
    out: list[str] = []
    from labsim.registry import by_id
    ok, payload = grader._run_checks(by_id("R1"), tmp_path, out)
    assert ok is False and payload == {}
    assert any("not an object" in line for line in out), out


# ───────────────────────────────────── the contract the workflow depends on ──
def test_discuss_always_writes_both_files(tmp_path):
    """`labsim discuss` must write reply.md AND meta.json on every path it can take.

    The workflow's collect step is `cp "$RUNNER_TEMP/meta.json" out/meta.json` under
    `set -euo pipefail`. A comment with no slash command used to return early having written
    only reply.md, so `cp` exited 1 and the grade job went red — on every ordinary peer
    comment, which is the interaction the whole feature exists to encourage. `respond` has an
    `[ -s out/reply.md ] || exit 0` guard for an empty reply; it has none for an absent file.
    """
    import json
    import subprocess
    import sys

    body = rendered_form(**{
        "Which unit": "F1 — Chunk so the answer survives the cut (implement, easy)",
        "Your approach, before the code": "Slide a window.",
        "Your solution.py": "```python\ndef chunk(text, size_tokens=512, overlap_tokens=64):\n    return [text]\n```",
    })
    cases = {
        "no comment at all": None,
        "a comment with no command": "nice — your chunker drops the trailing sentence",
        "a command inside a fence": "look:\n\n```\n/check\n```\n",
        "an unknown slash word": "/deploy please",
        "a real command": "/status",
    }
    for label, comment in cases.items():
        event = {"discussion": {"title": "F1 · my attempt", "body": body,
                                "node_id": "D_abc", "number": 99}}
        if comment is not None:
            event["comment"] = {"body": comment}
        d = tmp_path / label.replace(" ", "_")
        d.mkdir()
        (d / "event.json").write_text(json.dumps(event))
        proc = subprocess.run(
            [sys.executable, "-m", "labsim", "discuss",
             "--event", str(d / "event.json"), "--out", str(d / "reply.md"),
             "--meta", str(d / "meta.json"), "--repo", "o/r"],
            cwd=str(ROOT / "lab-simulator"), capture_output=True, text=True, timeout=300)
        assert proc.returncode == 0, f"{label}: exited {proc.returncode}\n{proc.stderr[-800:]}"
        assert (d / "reply.md").exists(), f"{label}: no reply.md"
        assert (d / "meta.json").exists(), (
            f"{label}: no meta.json — the workflow's `cp` fails the grade job here")
        meta = json.loads((d / "meta.json").read_text())
        assert set(meta) >= {"action", "unit", "passed", "discussion_node_id", "number"}, meta
        assert meta["number"] == 99


def test_a_measurement_note_with_its_own_headings_survives_whole():
    """`###` inside a field's content is not a new field.

    The P1 template a note is graded against opens with `### The table`, so every `###` being
    treated as a form boundary truncated the note at its first sub-heading and graded the
    fragment. The unit's own brief tells people to use those headings.
    """
    from labsim.discussion import parse_submission
    body = rendered_form(
        unit="P1 — Write the measurement note that survives you leaving (ship, medium)",
        approach="Wrote it against the template.",
        measurement=(
            "# Measurement · does the reranker pay\n\n"
            "- **Command** `python scripts/run_eval.py --rerank cross`\n\n"
            "### The table\n\n| arm | evidence_recall |\n|---|---|\n| none | 0.6486 |\n\n"
            "### What this does not say\n\nIt does not say the reranker is free."),
        surprised="How much of it was the command line.")
    note = parse_submission("P1 · my note", body).files.get("measurement.md", "")
    assert "### The table" in note, "the note was cut at its first sub-heading"
    assert "What this does not say" in note
    assert "How much of it was the command line" not in note, (
        "the note swallowed the next form field")


def test_r2_documents_what_its_decision_gate_actually_does(tmp_path):
    """SOLUTION.md said three example falsifiers were "all rejected". One is accepted.

    Documentation about a gate has to be checkable against the gate, or it is a claim about
    software that nobody runs. This grades all three and compares the verdicts against the
    table that describes them.
    """
    import yaml
    from labsim.grader import _grade_decision
    from labsim.registry import by_id

    unit = by_id("R2")
    base = yaml.safe_load(
        (ROOT / "lab-simulator/units/R2-fusion-decision/reference/pass/decision.yaml")
        .read_text(encoding="utf-8"))
    expected = {
        "If it turns out to be the wrong choice": False,
        "If fusion stops beating the single leg": True,      # the gate lets this through
        "If the numbers change": False,
    }
    for falsifier, want in expected.items():
        d = tmp_path / falsifier[:12].replace(" ", "_")
        d.mkdir()
        (d / "decision.yaml").write_text(
            yaml.safe_dump({**base, "would_change_if": falsifier}))
        got = _grade_decision(unit, d, [])
        assert got is want, (
            f"{falsifier!r}: the gate {'accepts' if got else 'rejects'} it, and the table in "
            f"SOLUTION.md says it {'accepts' if want else 'rejects'} it")

    text = (ROOT / "lab-simulator/units/R2-fusion-decision/SOLUTION.md").read_text(
        encoding="utf-8")
    assert "all rejected" not in text, "the table claims all three are rejected again"
    assert "**accepts it**" in text


def test_a_malformed_unit_is_reported_rather_than_fatal(tmp_path, monkeypatch):
    """`labsim validate` exists to find a broken unit.yaml. It could not survive one.

    `meta["title"]` raised while the registry was being built, so one malformed unit took out
    the other six along with the command whose job was to name it.
    """
    from labsim import registry

    (tmp_path / "Z9-broken").mkdir()
    (tmp_path / "Z9-broken" / "unit.yaml").write_text(
        "id: Z9\ntrack: retrieval\ndifficulty: easy\nmode: implement\n")   # no title
    (tmp_path / "Z9-broken" / "check.py").write_text("")
    monkeypatch.setattr(registry, "UNITS_DIR", tmp_path)
    registry.all_units.cache_clear()
    try:
        problems = registry.validate_all()
    finally:
        registry.all_units.cache_clear()
    assert "Z9" in problems, problems
    assert any("title" in p for p in problems["Z9"]), problems["Z9"]
