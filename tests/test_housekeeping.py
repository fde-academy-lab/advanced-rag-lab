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


# --------------------------------------------------------------- provisioning preflight

class FakeError(Exception):
    def __init__(self, status, message="nope"):
        self.status, self.message = status, message
        super().__init__(message)


def _preflight_with(monkeypatch, responses):
    """Run preflight against a stubbed `request`, returning (ok, calls)."""
    import setup_github

    calls = []

    def fake_request(method, path, *a, **kw):
        calls.append(path)
        outcome = responses[path]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(setup_github, "request", fake_request)
    monkeypatch.setattr(setup_github, "GitHubError", FakeError)
    ok = setup_github.preflight("fde-academy-lab", "advanced-rag-lab")
    return ok, calls


def test_preflight_accepts_an_actions_installation_token(monkeypatch):
    """An Actions GITHUB_TOKEN has no /user identity. That is normal, not a failure.

    Treating the 403 as fatal is why provisioning only ever ran with a PAT, and why the
    housekeeping workflow — which deliberately holds no PAT — could not seed a discussion.
    """
    ok, calls = _preflight_with(monkeypatch, {
        "/user": FakeError(403, "Resource not accessible by integration"),
        "/repos/fde-academy-lab/advanced-rag-lab": {"visibility": "public"},
    })
    assert ok
    assert calls == ["/user", "/repos/fde-academy-lab/advanced-rag-lab"]


def test_preflight_still_rejects_a_bad_token(monkeypatch):
    ok, _ = _preflight_with(monkeypatch, {"/user": FakeError(401, "Bad credentials")})
    assert not ok


def test_preflight_rejects_a_token_that_cannot_see_the_repository(monkeypatch):
    """403 on both questions is a real permission problem, not an installation token."""
    ok, _ = _preflight_with(monkeypatch, {
        "/user": FakeError(403, "Resource not accessible by integration"),
        "/repos/fde-academy-lab/advanced-rag-lab": FakeError(403, "nope"),
    })
    assert not ok


def test_preflight_accepts_an_ordinary_pat(monkeypatch):
    ok, calls = _preflight_with(monkeypatch, {"/user": {"login": "akash-coded"}})
    assert ok and calls == ["/user"]


# --------------------------------------------------------------- seeded answers

def test_every_intended_answer_has_a_usable_fingerprint():
    """The repair path finds a comment by a stretch of the reply's own prose.

    It has to be non-empty (a reply starting with a blank line or a code fence would give
    nothing to match on) and unique across the whole seed (two replies opening with the same
    sentence would mark the wrong comment as the answer).
    """
    import seed_content
    from setup_github import answer_fingerprint

    accepted = [r for t in seed_content.DISCUSSIONS
                for r in t.get("replies", []) if r.get("accepted")]
    assert accepted, "the seed defines no accepted answers at all"

    prints = [answer_fingerprint(r) for r in accepted]
    assert all(len(p) > 20 for p in prints), \
        [p for p in prints if len(p) <= 20]
    assert len(set(prints)) == len(prints), "two accepted replies share an opening line"


def test_an_accepted_reply_is_only_in_a_category_that_can_hold_one():
    """Marking an answer in a non-answerable category is an API error, not a no-op."""
    import seed_content
    answerable = {n for n, _e, _d, fmt in seed_content.CATEGORIES if fmt == "ANSWER"}
    # GitHub's own defaults that are answerable but not declared in CATEGORIES.
    answerable |= {"Q&A"}
    offenders = sorted({t["category"] for t in seed_content.DISCUSSIONS
                        if any(r.get("accepted") for r in t.get("replies", []))
                        and t["category"] not in answerable})
    assert not offenders, offenders


def test_the_repository_query_selects_every_field_the_code_branches_on():
    """`answerable` was built from `isAnswerable` on a query that never selected it.

    So the set was always empty, no answer was ever marked, and 24 threads shipped without the
    resolution that makes them readable. A query and the code reading it drift silently; this
    checks the two against each other.
    """
    import re

    import setup_github as sg

    query = sg.REPO_Q
    for field in ("isAnswerable", "number", "title", "slug", "id"):
        assert re.search(rf"\b{field}\b", query), \
            f"code branches on {field!r} but REPO_Q does not select it"
