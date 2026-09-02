"""The pure parts of the discussions pulse: which threads count as active, and how they order."""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "lab-simulator"))

from discussions_pulse import Thread, active, content_changes, render  # noqa: E402

NOW = datetime(2026, 9, 8, 7, 0, tzinfo=timezone.utc)
SINCE = NOW - timedelta(days=7)


def thread(number, *, window=0, total=0, humans=0, reactions=0, days_ago=1, answerable=True,
           answered=False, category="Q&A"):
    return Thread(number=number, title=f"t{number}", url="u", category=category,
                  answerable=answerable, answered=answered, author="a", labels=[],
                  comments_total=total, comments_window=window, humans_window=humans,
                  reactions=reactions, last_activity=NOW - timedelta(days=days_ago),
                  created=NOW - timedelta(days=30))


def test_heat_is_a_weighted_sum_and_orders_hottest_first():
    """heat = comments ×3 + people ×2 + reactions ×1. The weights are the whole policy."""
    ts = [thread(1, window=1, humans=1),                 # 5
          thread(2, window=3, humans=1),                 # 11
          thread(3, window=1, humans=3),                 # 9
          thread(4, window=1, humans=1, reactions=5)]    # 10
    assert [t.heat for t in ts] == [5, 11, 9, 10]
    assert [t.number for t in active(ts, SINCE)] == [2, 4, 3, 1]


def test_a_thread_that_did_not_move_is_not_active():
    ts = [thread(1, days_ago=20), thread(2, days_ago=2)]
    assert [t.number for t in active(ts, SINCE)] == [2]


def test_needs_answer_only_in_answerable_categories():
    assert thread(1, answerable=True, answered=False).needs_answer
    assert not thread(2, answerable=True, answered=True).needs_answer
    assert not thread(3, answerable=False, category="Ideas").needs_answer


def test_render_counts_the_unanswered_queue():
    ts = [thread(1, window=2), thread(2, window=1, answered=True), thread(3, window=1)]
    text = render(active(ts, SINCE), {}, 7)
    assert "2 answerable thread(s) with no accepted answer" in text
    assert "**needs an answer**" in text


def test_content_changes_groups_units_together(tmp_path):
    """The git-log parser groups everything under lab-simulator/units as one area."""
    import subprocess
    repo = tmp_path
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    for rel in ("docs/a.md", "lab-simulator/units/X1-a/BRIEF.md", "lab-simulator/units/Y1-b/check.py",
                "notebooks/n.ipynb", "raglab/core.py"):
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=repo, check=True)
    groups = content_changes(repo, days=1)
    assert set(groups) == {"docs", "lab-simulator/units", "notebooks"}, groups
    assert len(groups["lab-simulator/units"]) == 2
    assert all(f.startswith("+ ") for fs in groups.values() for f in fs)
