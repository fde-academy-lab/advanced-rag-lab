"""The learner-progress aggregation, which decides what a board and a `/progress` reply say.

Pure function, so every rule it encodes is a table here: what counts as an attempt, a clear, a
retry, and what happens when the same person clears a unit on two threads.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lab-simulator"))

from labsim_progress import Event, aggregate, render_for, stage_for  # noqa: E402

T0 = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)


def ev(login, unit, kind, minute, thread):
    return Event(login, unit, kind, T0 + timedelta(minutes=minute), thread, f"{unit} · t", "u")


def test_a_fail_then_a_pass_on_one_thread_is_two_attempts_one_retry_one_clear():
    L = aggregate([ev("ana", "R1", "fail", 0, 5), ev("ana", "R1", "pass", 10, 5)])["ana"]
    assert (L.attempts, L.retries, L.cleared, L.open) == (2, 1, {"R1"}, set())


def test_a_first_attempt_on_a_new_thread_is_not_a_retry():
    L = aggregate([ev("ana", "R1", "fail", 0, 5), ev("ana", "F1", "fail", 10, 6)])["ana"]
    assert L.retries == 0 and L.open == {"R1", "F1"}


def test_clearing_the_same_unit_on_two_threads_counts_once():
    L = aggregate([ev("ana", "R1", "pass", 0, 5), ev("ana", "R1", "pass", 10, 9)])["ana"]
    assert len(L.cleared) == 1 and L.attempts == 2


def test_hints_are_counted_but_are_not_attempts():
    L = aggregate([ev("ana", "R1", "hint", 0, 5), ev("ana", "R1", "hint", 1, 5)])["ana"]
    assert L.hints == 2 and L.attempts == 0 and not L.attempted


def test_learners_are_separate_even_on_similar_threads():
    out = aggregate([ev("ana", "R1", "fail", 0, 5), ev("ben", "R1", "pass", 1, 6)])
    assert out["ana"].open == {"R1"} and out["ben"].cleared == {"R1"}
    assert out["ana"].retries == 0 and out["ben"].retries == 0


def test_last_active_is_the_latest_event():
    L = aggregate([ev("ana", "R1", "fail", 0, 5), ev("ana", "R1", "pass", 30, 5)])["ana"]
    assert L.last_active == T0 + timedelta(minutes=30)


def test_stage_tracks_the_furthest_track_cleared():
    from labsim.registry import all_units
    units = all_units()
    starting = aggregate([ev("x", "R1", "fail", 0, 1)])["x"]
    assert stage_for(starting, units) == "Starting"
    ev1 = aggregate([ev("x", "F1", "pass", 0, 1), ev("x", "E1", "pass", 1, 2)])["x"]
    assert stage_for(ev1, units) == "Evaluation"
    done = aggregate([ev("x", u.uid, "pass", i, i) for i, u in enumerate(units)])["x"]
    assert stage_for(done, units) == "Complete"


def test_the_progress_reply_names_only_the_asker():
    from labsim.registry import all_units
    out = aggregate([ev("ana", "R1", "pass", 0, 5), ev("ben", "F1", "fail", 1, 6)])
    text = render_for("ana", out, all_units())
    assert "`ana`" in text and "1 of" in text and "R1" in text
    assert "ben" not in text, "another learner's row leaked into a personal reply"
    assert "<!-- labsim:progress -->" in text


def test_the_progress_reply_for_a_stranger_is_an_invitation():
    from labsim.registry import all_units
    text = render_for("nobody", {}, all_units())
    assert "nothing graded yet" in text and "`F1`" in text
