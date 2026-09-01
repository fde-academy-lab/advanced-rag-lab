"""The branch sweeper's rule.

Deleting branches automatically is destructive and runs unattended on every push to main, so
the predicate is worth more tests than the code that calls it. Each case below is a branch this
repository has actually had.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from sweep_branches import protected, verdict  # noqa: E402

MERGED = {"number": 64, "state": "closed", "merged_at": "2026-09-01T11:29:00Z"}
OPEN = {"number": 66, "state": "open", "merged_at": None}
ABANDONED = {"number": 30, "state": "closed", "merged_at": None}


def test_a_branch_whose_pull_request_merged_goes():
    go, why = verdict("feat/lab-simulator", [MERGED], "main")
    assert go and "#64" in why


def test_a_branch_with_an_open_pull_request_stays():
    go, why = verdict("feat/labsim-codespaces", [OPEN], "main")
    assert not go and "#66" in why


def test_a_branch_closed_without_merging_stays():
    """Closing without merging is a decision, and the branch is the only record of it."""
    go, why = verdict("docs/13-retest", [ABANDONED], "main")
    assert not go and "closed without merging" in why


def test_a_branch_with_both_a_merged_and_an_open_pull_request_stays():
    assert not verdict("feat/x", [MERGED, OPEN], "main")[0]


def test_a_branch_nobody_opened_a_pull_request_for_is_never_touched():
    """Somebody pushed an experiment and told no one. That is not litter."""
    go, why = verdict("spike/try-a-real-encoder", [], "main")
    assert not go and "no pull request" in why


def test_the_default_branch_is_never_deleted():
    assert not verdict("main", [MERGED], "main")[0]
    assert not verdict("trunk", [MERGED], "trunk")[0]


@pytest.mark.parametrize("name", [
    "main", "master", "gh-pages", "release/1.0",
    "dependabot/pip/ruff-gte-0.16.5",
    "dependabot/github_actions/actions/labeler-7",
    "revert-64-feat/lab-simulator",
])
def test_protected_patterns(name):
    assert protected(name)


def test_dependabot_branches_survive_a_merged_pull_request():
    """Deleting a Dependabot ref closes its pull request. Ten are open here."""
    assert not verdict("dependabot/pip/ruff-gte-0.16.5", [MERGED], "main")[0]


@pytest.mark.parametrize("name", [
    "feat/lab-simulator", "docs/low-level-design", "fix/thing",
    "mainline", "release-notes",
])
def test_ordinary_branches_are_not_protected(name):
    assert not protected(name)
