"""The wiki is generated from wiki/ and held to three rules: every page is reachable from Home,
every page opens with its takeaways, and links obey the wiki's URL rules after rewriting."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from wiki_sync import rewrite, sync  # noqa: E402

WIKI = ROOT / "wiki"
PAGES = sorted(WIKI.glob("*.md"))


def test_there_is_a_wiki_with_a_home_page():
    assert (WIKI / "Home.md").exists() and len(PAGES) >= 10


def test_every_page_is_reachable_from_home_directly_or_through_an_index():
    reachable, frontier = set(), ["Home.md"]
    while frontier:
        name = frontier.pop()
        if name in reachable:
            continue
        reachable.add(name)
        prose = re.sub(r"`[^`]*`", "", (WIKI / name).read_text())      # examples in code spans are not links
        for target in re.findall(r"\]\(([A-Za-z0-9][A-Za-z0-9_-]*\.md)(?:#[^)]*)?\)", prose):
            assert (WIKI / target).exists(), f"{name} links to a page that does not exist: {target}"
            frontier.append(target)
    missing = {p.name for p in PAGES} - reachable
    assert not missing, f"not reachable from Home: {sorted(missing)}"


def test_every_page_puts_the_takeaway_before_the_first_section():
    for p in PAGES:
        if p.name in ("Home.md", "How-To.md", "Newsletter.md", "Contributing.md"):
            continue
        head = p.read_text().split("\n## ", 1)[0].split("\n### ", 1)[0]
        assert "**Takeaway" in head, f"{p.name} does not open with its takeaways"


def test_links_to_repository_files_are_absolute_because_the_wiki_is_another_site():
    for p in PAGES:
        prose = re.sub(r"`[^`]*`", "", p.read_text())
        for target in re.findall(r"\]\(([^)]+)\)", prose):
            if target.startswith(("http://", "https://", "#")):
                continue
            assert re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*\.md(#[^)]*)?", target), \
                f"{p.name} has a relative link the wiki cannot resolve: {target}"


def test_rewrite_strips_md_from_page_links_only():
    assert rewrite("[a](How-To.md) [b](How-To.md#x) [c](https://x/y.md) [d](Home.md)") == \
        "[a](How-To) [b](How-To#x) [c](https://x/y.md) [d](Home)"


def test_sync_writes_rewritten_pages_and_is_idempotent(tmp_path):
    first = sync(tmp_path)
    assert "Home.md" in first and "(How-To)" in (tmp_path / "Home.md").read_text()
    assert sync(tmp_path) == []


def test_newsletter_items_cite_a_source_and_offer_something_to_try():
    for p in WIKI.glob("Newsletter-*.md"):
        text = p.read_text()
        items = re.split(r"\n### \d+\. ", text)[1:]
        assert items, p.name
        for item in items:
            assert "https://" in item, f"{p.name}: an item without a source"
            assert "**Try today.**" in item, f"{p.name}: an item without an experiment"
            assert "**Why an FDE cares.**" in item, f"{p.name}: an item without the so-what"


def test_no_em_dashes_in_wiki_prose():
    for p in PAGES:
        assert "—" not in p.read_text(), p.name
