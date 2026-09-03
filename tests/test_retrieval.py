"""Properties that must hold no matter how the retriever is tuned."""
import numpy as np
import pytest

from raglab import metrics, retrieve
from raglab.store import InMemoryIndex


def test_identifiers_survive_the_analyzer(system):
    """The default FTS5 tokenizer splits ERR_CONN_RESET. Ours must not."""
    _, index, _ = system
    hits = index.lexical('"ERR_CONN_RESET"', n=10, fts_expr='"ERR_CONN_RESET"')
    assert hits, "identifier query returned nothing — check tokenchars in store.SCHEMA"
    assert all("ERR_CONN_RESET" in h.text for h in hits)


def test_reranking_can_never_exceed_the_first_stage_ceiling(system):
    """The single most important invariant in the whole pipeline."""
    bundle, _, pipe = system
    checked = 0
    for q in bundle.questions[:40]:
        gold_map, _ = metrics.resolve_gold(q, pipe.chunks)
        if not gold_map:
            continue
        candidates = pipe.retriever.search(q.query, pipe.cfg)
        ceiling = metrics.evidence_recall_at_k([h.chunk_id for h in candidates], gold_map)
        reranked = pipe.reranker.rerank(q.query, candidates, depth=pipe.cfg.rerank_depth)
        delivered = metrics.evidence_recall_at_k(
            [h.chunk_id for h in reranked[: pipe.cfg.k]], gold_map)
        assert delivered <= ceiling + 1e-9, f"{q.qid}: {delivered} > ceiling {ceiling}"
        checked += 1
    assert checked > 10


def test_ann_recall_rises_monotonically_with_ef_search(system):
    _, index, pipe = system
    qv = pipe.embedder.encode_queries(["Which organization acquired Tessera Analytics?"])[0]
    exact = {h.chunk_id for h in index.exact_vector(qv, n=20)}
    recalls = []
    for ef in (8, 32, 128, 512):
        got = {h.chunk_id for h in index.ann_vector(qv, n=20, ef_search=ef)}
        recalls.append(len(got & exact) / 20)
    assert recalls == sorted(recalls), f"ANN recall not monotonic in efSearch: {recalls}"
    assert recalls[-1] >= 0.9, "the graph is not navigable — check the long-range links"


def test_l2_normalisation_makes_cosine_and_dot_identical(system):
    _, _, pipe = system
    q = pipe.embedder.encode_queries(["revenue growth"])[0]
    d = pipe.embedder.encode_documents([pipe.chunks[0].text])[0]
    cosine = float(np.dot(q, d) / (np.linalg.norm(q) * np.linalg.norm(d)))
    assert abs(cosine - float(np.dot(q, d))) < 1e-5


@pytest.mark.parametrize("mode", ["pre", "post"])
def test_no_persona_ever_receives_a_chunk_outside_its_groups(system, mode):
    """The release-gate test from interview Q4, as a unit test."""
    import json

    bundle, index, pipe = system
    queries = ["What is the recommended fix for ERR_CONN_RESET?",
               "What risk did the integration review identify for Northwind Systems?"]
    for persona, groups in bundle.personas.items():
        for query in queries:
            trace = pipe.variant("t", filter_mode=mode).run(query, acl_groups=groups)
            for block in trace.packed:
                acl = set(json.loads(index.get(block["chunk_id"])["acl"]))
                assert acl & set(groups), f"{persona} saw {block['chunk_id']} with acl {acl}"


def test_post_filtering_collapses_k_and_pre_filtering_does_not(system):
    """Post-filtering satisfies 'cannot read it'. It does not satisfy 'not influenced by it'."""
    bundle, _, pipe = system
    query = "What is the recommended fix for ERR_CONN_RESET?"
    analyst = bundle.personas["analyst"]
    pre = pipe.variant("pre", filter_mode="pre").run(query, acl_groups=analyst)
    post = pipe.variant("post", filter_mode="post").run(query, acl_groups=analyst)
    assert pre.k_collapse == 0
    assert post.k_collapse > 0, "the k-collapse demonstration has stopped demonstrating"
    assert len(post.packed) < len(pre.packed)


def test_mixed_version_index_is_detected(system):
    """Vectors from two encoders are not comparable and cosine will not say so."""
    _, _, pipe = system
    idx = InMemoryIndex()
    vecs = pipe.embedder.encode_documents([c.text for c in pipe.chunks[:50]])
    idx.upsert(pipe.chunks[:50], vecs, "v1", "encoder-a@1.0")
    assert idx.mixed_version_check("v1")["ok"]
    idx.upsert(pipe.chunks[:10], vecs[:10], "v1", "encoder-b@2.0")
    assert not idx.mixed_version_check("v1")["ok"]


def test_rrf_is_rank_based_and_ignores_score_magnitude():
    from raglab.store import Hit

    a = [Hit("x", 1000.0, 1, "bm25"), Hit("y", 999.0, 2, "bm25")]
    b = [Hit("x", 0.001, 1, "dense"), Hit("y", 0.0009, 2, "dense")]
    scaled = [Hit(h.chunk_id, h.score * 1e6, h.rank, h.method) for h in b]
    assert [h.chunk_id for h in retrieve.rrf([a, b])] == \
           [h.chunk_id for h in retrieve.rrf([a, scaled])]
