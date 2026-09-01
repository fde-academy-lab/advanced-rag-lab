"""The corpus is generated, so its invariants are testable rather than hoped for."""
from collections import Counter

from raglab import chunking, corpus, metrics


def test_corpus_is_deterministic():
    a, b = corpus.build_corpus(), corpus.build_corpus()
    assert [d.doc_id for d in a.documents] == [d.doc_id for d in b.documents]
    assert [d.content_hash for d in a.documents] == [d.content_hash for d in b.documents]
    assert [q.query for q in a.questions] == [q.query for q in b.questions]


def test_every_gold_anchor_resolves_under_the_shipped_chunking(system):
    """A label no chunking can satisfy is a broken label, not a hard question."""
    bundle, _, pipe = system
    unresolved = []
    for q in bundle.questions:
        _, missing = metrics.resolve_gold(q, pipe.chunks)
        unresolved += [(q.qid, m) for m in missing]
    assert not unresolved, f"{len(unresolved)} gold spans do not resolve: {unresolved[:3]}"


def test_null_questions_have_no_gold_evidence():
    bundle = corpus.build_corpus()
    for q in bundle.questions:
        if q.question_type == "null":
            assert not q.evidence_anchors, f"{q.qid} is null but carries evidence"


def test_eval_set_is_balanced_enough_to_slice():
    bundle = corpus.build_corpus()
    counts = Counter(q.question_type for q in bundle.questions)
    for qtype in ("inference", "comparison", "temporal", "null"):
        assert counts[qtype] >= 20, f"{qtype} slice too small to report on: {counts[qtype]}"


def test_frozen_slice_exists_and_is_roughly_fifteen_percent():
    bundle = corpus.build_corpus()
    frozen = sum(1 for q in bundle.questions if q.slice == "frozen")
    assert 0.10 <= frozen / len(bundle.questions) <= 0.20


def test_chunk_ids_are_stable_across_rebuilds():
    """doc_id + ordinal + content hash. This is what makes an upsert an upsert."""
    docs = corpus.build_corpus().documents[:20]
    a = chunking.chunk_corpus(docs, strategy="structural")
    b = chunking.chunk_corpus(docs, strategy="structural")
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]


def test_every_strategy_produces_chunks_and_keeps_provenance():
    docs = corpus.build_corpus().documents[:30]
    for name in chunking.STRATEGIES:
        chunks = chunking.chunk_corpus(docs, strategy=name)
        assert chunks, name
        assert all(c.doc_id and c.title and c.published for c in chunks), name
