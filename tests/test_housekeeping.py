"""The branch sweeper's rule.

Deleting branches automatically is destructive and runs unattended on every push to main, so
the predicate is worth more tests than the code that calls it. Each case below is a branch this
repository has actually had.
"""
from __future__ import annotations

import re
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

    # The listing moved into its own paginated query, so check the pair.
    query = sg.REPO_Q + sg.DISCUSSIONS_PAGE_Q
    for field in ("isAnswerable", "number", "title", "slug", "id"):
        assert re.search(rf"\b{field}\b", query), \
            f"code branches on {field!r} but neither discussion query selects it"


def test_the_discussion_listing_is_paginated():
    """`first:100` is one page, not a listing, and the seeder decides what exists from it.

    Past a hundred threads an unpaginated read stops recognising the repository's own content
    and seeds a second copy of everything it cannot see. There are 44 defined.
    """
    import setup_github as sg
    assert "pageInfo" in sg.DISCUSSIONS_PAGE_Q and "endCursor" in sg.DISCUSSIONS_PAGE_Q
    src = (ROOT / "scripts" / "setup_github.py").read_text(encoding="utf-8")
    assert "existing = all_discussions(" in src, (
        "create_discussions no longer reads the paginated listing")
    assert 'discussions(first:100){' not in sg.REPO_Q, (
        "REPO_Q reads one page of discussions again")


# --------------------------------------------------------------- retired threads

def test_every_retired_thread_points_at_a_title_the_seed_still_defines():
    """A banner pointing at a thread that does not exist is worse than no banner."""
    import seed_content
    defined = {t["title"] for t in seed_content.DISCUSSIONS}
    for old, new in seed_content.RETIRED.items():
        assert new in defined, f"{old!r} is retired in favour of {new!r}, which no longer exists"
        assert old not in defined, f"{old!r} is both retired and still seeded"


def test_the_retirement_banner_formats_with_the_fields_the_code_passes():
    import seed_content
    out = seed_content.RETIREMENT_BANNER.format(
        replacement="The new title", url="/o/r/discussions/69", owner="o", repo="r")
    assert out.lstrip().startswith("> [!WARNING]"), "the banner must be a GitHub alert"
    assert "/o/r/discussions/69" in out and "0015-correct-the-fusion-finding" in out


def test_a_banded_thread_is_recognised_and_not_banded_twice():
    """The idempotence check is a prefix match on the live body — keep the two in step."""
    import seed_content
    banner = seed_content.RETIREMENT_BANNER.format(
        replacement="x", url="/u", owner="o", repo="r")
    assert (banner + "original body").lstrip().startswith("> [!WARNING]")


# ─────────────────────────────────────────────────────── the discussions guide ──
GUIDE = ROOT / "docs" / "10-community" / "discussions-guide.md"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def test_the_guide_documents_every_category_the_repository_creates():
    """A category the seeder creates and the guide omits is one nobody will post in."""
    import seed_content
    text = _guide()
    for name, *_ in seed_content.CATEGORIES:
        assert f"**{name}**" in text, f"the discussions guide never mentions {name!r}"


def test_the_guide_documents_every_discussion_label():
    import seed_content
    text = _guide()
    for name, *_ in seed_content.DISCUSSION_LABELS:
        assert f"`{name}`" in text, f"the discussions guide never explains the {name!r} label"


def test_the_play_count_in_the_heading_matches_the_plays():
    """The heading names a number. A table people add rows to will drift away from it."""
    text = _guide()
    words = {"twenty-one": 21, "twenty-two": 22, "twenty-three": 23, "twenty-four": 24,
             "twenty-five": 25, "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28}
    heading = re.search(r"^## The ([a-z-]+) plays$", text, re.M)
    assert heading, "the plays section has been renamed; this test names it explicitly"
    claimed = words.get(heading.group(1))
    assert claimed, f"unrecognised number word {heading.group(1)!r} — extend the map"

    section = text[text.index(heading.group(0)):text.index("## Lifecycle")]
    rows = [l for l in section.splitlines()
            if l.startswith("| ") and "---" not in l and not l.startswith("| Category |")]
    assert len(rows) == claimed, (
        f"the heading says {claimed} plays and the tables carry {len(rows)}")


def test_the_guide_does_not_claim_the_stale_bot_touches_discussions():
    """It does not — `actions/stale` supports issues and pull requests only.

    The guide said it did, in a table of bots, until somebody read the workflow. A wrong claim
    about automation is worse than no claim: people wait for a thing that will not happen.
    """
    stale = (ROOT / ".github" / "workflows" / "stale.yml").read_text(encoding="utf-8")
    assert "discussion" not in stale.lower(), (
        "stale.yml now touches discussions, so the guide's statement that nothing ages a "
        "discussion out is stale itself")
    assert "Nothing ages a discussion out" in _guide()


# ────────────────────────────────────────── a refused rename must not duplicate ──
def test_a_refused_rename_blocks_the_create_that_would_duplicate_it():
    """This is the bug that put nine duplicate pairs on the live forum.

    `rename_threads` reported each refusal and returned only a count. The create loop then saw
    nine canonical titles that were not live, created them, and left every renamed thread
    sitting beside a fresh copy of itself — arrived at through the error path of the function
    whose whole purpose is to prevent exactly that.

    The contract now: whatever could not be renamed is returned, and the create loop skips it.
    """
    import inspect

    import setup_github as sg

    src = inspect.getsource(sg.rename_threads)
    assert "refused.add(new)" in src, (
        "rename_threads no longer records the renames it could not apply")
    assert src.rstrip().endswith("return renamed, refused"), (
        "rename_threads must return the refused set, not just a count")

    create = inspect.getsource(sg.create_discussions)
    assert "renamed, rename_refused = rename_threads(" in create
    guard = create.index("for spec in content.DISCUSSIONS:")
    body = create[guard:]
    assert body.index("if title in rename_refused:") < body.index("if title in existing:"), (
        "the refused-rename guard must run before the exists check, or a thread whose rename "
        "was refused is created a second time")


def test_no_two_canonical_titles_could_collide_after_a_rename():
    """A rename whose target is already a distinct seeded title creates a title collision."""
    import seed_content
    titles = {t["title"] for t in seed_content.DISCUSSIONS}
    for old, new in seed_content.RENAMED.items():
        assert old not in titles, (
            f"{old!r} is both a rename source and a seeded title, so seeding recreates the "
            "thread the rename was meant to retitle")
        assert new in titles or new in seed_content.RETIRED, (
            f"{new!r} is a rename target that nothing seeds")
