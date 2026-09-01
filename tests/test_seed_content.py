"""Invariants on the seeded discussion content.

Seed data is prose, so nothing else checks it. These are the mistakes that would ship silently:
a thread aimed at a category that does not exist, a reply from a persona with no entry in the
register, an accepted answer in a category that cannot accept one, and — the one that actually
happened — a relative link that 404s because Discussions resolve relative URLs against the
discussion, not the repository root.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import seed_content as content  # noqa: E402
from seed.personas import PERSONAS  # noqa: E402

THREADS = content.DISCUSSIONS
BUILT_IN = {"Announcements", "General", "Ideas", "Q&A", "Show and tell", "Polls"}
DECLARED = {name for name, *_ in content.CATEGORIES} | BUILT_IN
ANSWERABLE = {name for name, _emoji, _desc, fmt in content.CATEGORIES if fmt == "ANSWER"} | {"Q&A"}


def test_every_thread_targets_a_declared_category():
    unknown = {t["category"] for t in THREADS} - DECLARED
    assert not unknown, f"threads aimed at categories nobody creates: {sorted(unknown)}"


def test_every_author_and_replier_is_in_the_register():
    used = {t.get("author", "maintainer") for t in THREADS}
    used |= {r["by"] for t in THREADS for r in t.get("replies", [])}
    assert not used - set(PERSONAS), f"unknown personas: {sorted(used - set(PERSONAS))}"


def test_accepted_answers_only_in_answerable_categories():
    """Marking an answer in a non-answerable category is an API error, not a no-op."""
    for t in THREADS:
        if any(r.get("accepted") for r in t.get("replies", [])):
            assert t["category"] in ANSWERABLE, (
                f"“{t['title'][:50]}” marks an answer but {t['category']} is not answerable")


def test_at_most_one_accepted_answer_per_thread():
    for t in THREADS:
        n = sum(1 for r in t.get("replies", []) if r.get("accepted"))
        assert n <= 1, f"“{t['title'][:50]}” marks {n} answers"


def test_no_relative_repo_links_in_seeded_bodies():
    """Discussions resolve relative links against the discussion URL, so ../blob/main 404s."""
    bad = []
    for t in THREADS:
        for label, body in [("body", t["body"])] + [
                (f"reply/{r['by']}", r["body"]) for r in t.get("replies", [])]:
            if "../blob/" in body or "](docs/" in body:
                bad.append(f"{t['title'][:40]} · {label}")
    assert not bad, f"relative repo links that will 404 inside a Discussion: {bad}"


def test_no_links_to_the_pre_restructure_docs_layout():
    stale = [t["title"][:44] for t in THREADS
             if "/docs/adr/" in t["body"]
             or any("/docs/adr/" in r["body"] for r in t.get("replies", []))]
    assert not stale, f"links to docs/adr/, which moved to docs/01-architecture/adr/: {stale}"


@pytest.mark.parametrize("thread", THREADS, ids=lambda t: t["title"][:40])
def test_threads_carry_a_real_conversation(thread):
    """A thread with no replies is the defect this content set exists to fix."""
    if thread["category"] == "Announcements":
        return  # announcements are posts, not conversations
    assert thread.get("replies"), "no replies — this is a noticeboard post, not a thread"


def test_the_corpus_is_substantial_enough_to_set_a_standard():
    replies = sum(len(t.get("replies", [])) for t in THREADS)
    answers = sum(1 for t in THREADS for r in t.get("replies", []) if r.get("accepted"))
    assert len(THREADS) >= 25, len(THREADS)
    assert replies >= 60, replies
    assert answers >= 10, answers
