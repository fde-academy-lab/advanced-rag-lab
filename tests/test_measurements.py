"""Derived numbers, checked against the thing that derives them.

Two claims in this repository were wrong for months and neither was a typo. Both were figures
computed once, written into prose, and never re-derived — an aggregate table that said one
retriever beat another, and a `p^k` weighted over a question mixture that did not exist. CI could
not catch either, because CI compared the system against its own past self and never against
arithmetic.

So: every number the documentation quotes for the independence comparison is recomputed here from
the corpus and the committed baseline, and the test fails if the prose has drifted. It is fast —
the distribution needs chunking, not retrieval.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

NOTE = ROOT / "docs" / "09-research" / "measurements" / "multi-hop-independence.md"
QUOTING = [
    ROOT / "docs" / "04-evaluation" / "metrics.md",
    ROOT / "docs" / "01-architecture" / "lld" / "metrics.md",
    ROOT / "lab-simulator" / "units" / "E1-recall-that-means-something" / "BRIEF.md",
    ROOT / "lab-simulator" / "units" / "E1-recall-that-means-something" / "SOLUTION.md",
]

# The retracted figures. They may appear only inside an explicit retraction.
RETRACTED = ("0.6838", "128 single-hop", "61 two-hop", "18 three-or-more", "18 three-plus")
RETRACTION_WORDS = re.compile(
    r"corrected|retract|supersede|previously|used to read|published the opposite"
    r"|did not exist|got wrong|was wrong|the old version", re.I)
CONTEXT = 3          # a retracted figure may sit a few lines under the sentence retracting it


@pytest.fixture(scope="module")
def truth():
    from independence import summary
    return summary(measure=False)


def test_the_distribution_is_read_off_the_corpus(truth):
    """If the corpus generator changes, this is what tells you the prose is now stale."""
    sizes = truth["gold_pieces_per_question"]
    assert sum(sizes.values()) == truth["answerable"] == 207
    assert sizes == {"1": 21, "2": 59, "3": 21, "4": 100, "6": 6}, sizes


def test_the_prediction_and_the_verdict(truth):
    assert truth["prediction_macro"] == pytest.approx(0.4603, abs=5e-4)
    assert truth["full_chain_recall"] == pytest.approx(0.4686, abs=5e-4)
    # The sign is the whole finding: at or above independence means there is no correlated
    # failure structure to go looking for.
    assert truth["delta_macro"] > 0, (
        "measured full-chain recall has fallen below the independence prediction. That would be "
        "a real finding — correlated failure — and every document saying otherwise is now wrong.")


def test_the_exponent_is_pieces_not_hops():
    """The bug was `p^hops`. The corpus reports a hop field, and it is a different number."""
    from collections import Counter

    from raglab import chunking, corpus, metrics
    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy="structural")
    hops, pieces = Counter(), Counter()
    for q in bundle.questions:
        g = metrics.resolve_gold(q, chunks)[0]
        if g:
            hops[q.hops] += 1
            pieces[len(g)] += 1
    assert dict(hops) != dict(pieces), (
        "hops and gold-piece counts now agree, so the distinction this test guards is gone")
    assert max(pieces) > max(hops), "a question carries more evidence pieces than it has hops"


@pytest.mark.parametrize("path", QUOTING, ids=lambda p: p.name)
def test_the_prose_quotes_the_computed_numbers(path, truth):
    text = path.read_text()
    for value in (f"{truth['prediction_macro']:.4f}", f"{truth['full_chain_recall']:.4f}"):
        assert value in text, f"{path.name} does not quote {value}"


@pytest.mark.parametrize("path", QUOTING + [NOTE], ids=lambda p: p.name)
def test_retracted_figures_appear_only_inside_a_retraction(path):
    """The old numbers are allowed as history. They are not allowed as a claim.

    "Inside a retraction" means the line itself says so, it is quoted, or a line just above it
    does — a retracted figure usually sits a sentence or two under the sentence retracting it.
    """
    lines = path.read_text().splitlines()
    for i, line in enumerate(lines):
        for bad in RETRACTED:
            if bad not in line:
                continue
            window = lines[max(0, i - CONTEXT):i + 1]
            excused = (line.lstrip().startswith(">")
                       or any(RETRACTION_WORDS.search(w) for w in window))
            assert excused, (
                f"{path.name}:{i + 1}: {bad!r} appears outside a retraction:\n  {line.strip()}")


def test_the_measurement_note_names_its_command():
    text = NOTE.read_text()
    assert "scripts/independence.py" in text
    assert "supersedes" in text.lower()


# ────────────────────────────────────────────────── the failure-overlap figure ──
FUSION_NOTE = ROOT / "docs" / "09-research" / "measurements" / "fusion-rules.md"
R3 = ROOT / "lab-simulator" / "units" / "R3-fusion-measured"


@pytest.fixture(scope="module")
def overlap():
    """Recomputed from the corpus. Slower than the independence fixture — it retrieves."""
    from failure_overlap import summary
    return summary()


def test_the_overlap_is_read_off_the_corpus(overlap):
    assert overlap["answerable"] == 207
    assert (overlap["dense_misses"], overlap["lexical_misses"], overlap["both_miss"]) \
        == (95, 102, 92)
    assert overlap["conditional"] == pytest.approx(0.9684, abs=5e-5)
    assert overlap["jaccard"] == pytest.approx(0.8762, abs=5e-5)


def test_the_conditional_and_the_jaccard_stay_far_enough_apart_to_grade_between(overlap):
    """R3 places a bar between them so a wrong formula fails on a number, not on style.

    If the two ever converge, that bar stops discriminating and the unit silently starts
    accepting the answer it was built to reject.
    """
    bar = 0.9000
    assert overlap["jaccard"] < bar < overlap["conditional"], (
        f"R3's bar of {bar} no longer separates the conditional ({overlap['conditional']}) "
        f"from the Jaccard ({overlap['jaccard']}), so the decoy formula now passes")
    assert f"{bar:.4f}" in (R3 / "unit.yaml").read_text()


@pytest.mark.parametrize("path", [FUSION_NOTE, R3 / "BRIEF.md", R3 / "unit.yaml"],
                         ids=lambda p: p.name)
def test_the_prose_quotes_the_computed_overlap(path, overlap):
    text = path.read_text()
    for value in (f"{overlap['conditional']:.4f}", f"{overlap['jaccard']:.4f}"):
        assert value in text, f"{path.name} does not quote {value}"


def test_the_correction_quotes_the_computed_overlap(overlap):
    """The correction posted to the live thread is prose too, and it drifts the same way."""
    import seed_content
    text = seed_content.CORRECTED[
        "RRF or weighted fusion — and what actually decided it on this corpus"]
    for value in (str(overlap["dense_misses"]), str(overlap["lexical_misses"]),
                  str(overlap["both_miss"]), f"{overlap['conditional']:.4f}",
                  f"{overlap['jaccard']:.4f}"):
        assert value in text, f"the correction does not quote {value}"


def test_the_fusion_note_names_its_commands():
    text = FUSION_NOTE.read_text()
    assert "scripts/failure_overlap.py" in text, (
        "the overlap figures are quoted without the command that regenerates them — which is "
        "the exact shape of the two claims this file exists to prevent")
    assert "run_eval.py --compare" in text
