"""R3 · Build the rule you rejected, and the measurement that rejected it.

Implement both. Run `labsim check R3` when you want them graded — it builds the real corpus and
runs your fusion through the repository's own reranker, so the number you get is the number.
"""
from __future__ import annotations


def rrf(legs, k: int = 60):
    """Reciprocal rank fusion.  RRF(d) = sum over legs of 1 / (k + rank(d)).

    `legs` is a list of lists of hits, each ordered best first. A hit has .chunk_id, .score,
    .rank, .text, .doc_id. Return one entry per chunk_id, best first, each entry being one of
    the hit objects you were given.
    """
    agg: dict[str, float] = {}
    keep: dict[str, object] = {}

    for leg in legs:
        # TODO 1 — walk the leg. The rank is the position in THIS list, starting at 1,
        #          not hit.rank, which was computed by someone else.
        # TODO 2 — accumulate 1/(k + rank) into agg, and remember one hit object per chunk_id.
        pass

    # TODO 3 — sort by score descending and return the hit objects
    return []


def failure_overlap(dense_misses: set[str], lexical_misses: set[str]) -> float:
    """P(lexical also misses | dense misses) = |D and L| / |D|.

    A conditional probability, not a Jaccard index. Return 0.0 when dense_misses is empty.
    """
    # TODO 4
    return 0.0
