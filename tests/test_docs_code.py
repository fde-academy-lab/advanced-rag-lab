"""Execute the reference solutions published in the interview-prep docs.

A candidate is going to learn these and write them at a whiteboard. Shipping one with an
off-by-one in it would be worse than shipping nothing, and prose examples rot silently because
nothing ever runs them. So they run here, with the assertions that catch the specific mistakes
the surrounding text warns about.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

CODING_DOC = Path(__file__).resolve().parent.parent / "docs" / "06-interview-prep" / "coding.md"


@pytest.fixture(scope="module")
def solutions() -> dict:
    """Every python block in coding.md, executed into one namespace."""
    blocks = re.findall(r"```python\n(.*?)```", CODING_DOC.read_text(), re.S)
    assert blocks, "coding.md has no python blocks — the doc moved or the fences changed"
    ns: dict = {}
    for block in blocks:
        exec(block, ns)  # noqa: S102  (our own documentation, executed deliberately)
    return ns


def test_bm25_ranks_the_right_document_first(solutions):
    docs = ["the cat sat on the mat", "a dog sat on a log",
            "cats and dogs living together", "the mat was flat"]
    assert solutions["bm25_rank"](docs, "cat mat")[0][0] == "the cat sat on the mat"


def test_bm25_survives_a_term_in_every_document(solutions):
    """Without the +0.5 smoothing this is log(0). The doc calls it a Jeffreys prior."""
    assert solutions["bm25_rank"](["a b", "a c", "a d"], "a")[0][1] >= 0


def test_bm25_handles_an_empty_corpus(solutions):
    assert solutions["bm25_rank"]([], "x") == []


def test_chunk_ends_on_sentence_boundaries(solutions):
    text = " ".join(f"Sentence number {i} here." for i in range(1, 80))
    chunks = solutions["chunk"](text, size=40, overlap=10)
    assert len(chunks) > 1
    assert all(c.strip().endswith(".") for c in chunks)


def test_chunk_refuses_an_overlap_that_cannot_advance(solutions):
    """overlap >= size is an infinite loop, not a slow chunker."""
    with pytest.raises(ValueError):
        solutions["chunk"]("x", size=10, overlap=10)


def test_rrf_ranks_from_one_not_zero(solutions):
    """enumerate(start=1). Starting at 0 gives rank 0 a score of 1/k — a real, subtle bug."""
    fused = dict(solutions["rrf"]([["a", "b", "c"], ["b", "a", "d"]]))
    assert fused["a"] == pytest.approx(1 / 61 + 1 / 62)


def test_evaluate_separates_per_piece_from_per_question(solutions):
    results = {"q1": ["d1", "d2", "d9"], "q2": ["d5", "d6"], "q3": []}
    gold = {"q1": {"d1", "d2"}, "q2": {"d5", "d7"}, "q3": {"d8"}}
    m = solutions["evaluate"](results, gold, k=10)
    assert m["recall@k"] == pytest.approx(0.5)        # per piece: 1.0, 0.5, 0.0
    assert m["full_chain@k"] == pytest.approx(1 / 3)  # only q1 has every piece
    assert m["mrr"] == pytest.approx(2 / 3)
    assert m["n"] == 3


def test_evaluate_reports_its_denominator(solutions):
    """A metric without n is not reportable, and an empty gold set must not divide by zero."""
    assert solutions["evaluate"]({}, {})["n"] == 0
