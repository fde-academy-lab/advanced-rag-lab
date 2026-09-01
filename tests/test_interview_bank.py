"""Integrity of the machine-readable question bank.

The bank is an index into the prose banks, not a second copy. That only works if the pointers
resolve — a `source:` anchor that has drifted sends a candidate to a heading that no longer
exists, and nothing else would catch it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BANK_FILE = ROOT / "interview-bank" / "questions.yaml"
MODELS_FILE = ROOT / "interview-bank" / "mental-models.md"
TIERS = {"screen", "mid", "senior", "staff"}
BANDS = {"misses", "screen", "mid", "senior", "staff"}


@pytest.fixture(scope="module")
def bank():
    yaml = pytest.importorskip("yaml")
    return yaml.safe_load(BANK_FILE.read_text())["questions"]


def _anchor(heading: str) -> str:
    """GitHub's heading-slug algorithm.

    Each whitespace character becomes one hyphen — runs are *not* collapsed. "R1 · The opener"
    drops the middot and leaves two spaces, so the anchor carries a double hyphen. Collapsing
    the run produces a slug that looks right and resolves to nothing.
    """
    slug = re.sub(r"[^\w\s-]", "", heading.lower()).strip()
    return re.sub(r"\s", "-", slug)


def test_ids_are_unique(bank):
    ids = [q["id"] for q in bank]
    assert len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1]


def test_every_question_has_the_required_fields(bank):
    for q in bank:
        missing = {"id", "topic", "tier", "model", "q", "trap", "signals", "source"} - set(q)
        assert not missing, f"{q.get('id')} missing {sorted(missing)}"


def test_tiers_and_bands_are_from_the_vocabulary(bank):
    for q in bank:
        assert q["tier"] in TIERS, f"{q['id']}: tier {q['tier']!r}"
        assert set(q["signals"]) <= BANDS, f"{q['id']}: bands {sorted(set(q['signals']) - BANDS)}"


def test_every_model_named_is_documented(bank):
    documented = set(re.findall(r"^## \d+ · (.+)$", MODELS_FILE.read_text(), re.M))
    slugs = {re.sub(r"[^a-z]+", "-", m.lower()).strip("-") for m in documented}
    for q in bank:
        assert q["model"] in slugs, (
            f"{q['id']} names model {q['model']!r}, which mental-models.md does not define. "
            f"Defined: {sorted(slugs)}")


def test_every_source_file_exists(bank):
    for q in bank:
        path = ROOT / q["source"].split("#")[0]
        assert path.exists(), f"{q['id']} points at {q['source']}, which does not exist"


def test_every_source_anchor_resolves(bank):
    """A drifted anchor sends a candidate to a heading that is not there."""
    cache: dict[Path, set[str]] = {}
    broken = []
    for q in bank:
        file_part, _, anchor = q["source"].partition("#")
        if not anchor:
            continue
        path = ROOT / file_part
        if path not in cache:
            cache[path] = {_anchor(h) for h in re.findall(r"^#+\s+(.+)$", path.read_text(), re.M)}
        if anchor not in cache[path]:
            broken.append(f"{q['id']} → {q['source']}")
    assert not broken, broken


def test_the_bank_covers_every_topic_file(bank):
    topics = {q["topic"] for q in bank}
    expected = {"retrieval", "evaluation", "mathematics", "systems-design", "coding",
                "behavioural"}
    assert expected <= topics, f"no questions for {sorted(expected - topics)}"


def test_questions_carry_followups(bank):
    """The follow-up is where the marks are; a question without one under-trains the candidate."""
    without = [q["id"] for q in bank if not q.get("followups")]
    assert not without, f"no follow-ups on {without}"
