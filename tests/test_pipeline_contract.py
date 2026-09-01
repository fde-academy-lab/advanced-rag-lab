"""End-to-end contracts: the things a release gate would block on."""
from raglab import metrics, pipeline


def test_a_trace_can_replay_its_own_answer(system):
    _, _, pipe = system
    trace = pipe.run("Which organization acquired Tessera Analytics?")
    stored = pipe.trace_store.get(trace.trace_id)
    assert stored is not None
    assert stored.packed_ids == trace.packed_ids
    assert stored.answer == trace.answer
    assert stored.config["name"] == pipe.name


def test_every_citation_resolves_to_a_packed_chunk(system):
    bundle, _, pipe = system
    for q in bundle.questions[:30]:
        trace = pipe.run(q.query, qid=q.qid, acl_groups=bundle.personas.get(q.persona))
        for sid in trace.citations:
            assert trace._packed_obj.resolve(sid), f"{q.qid}: {sid} does not resolve"


def test_evidence_never_exceeds_the_token_cap(system):
    bundle, _, pipe = system
    for q in bundle.questions[:30]:
        trace = pipe.run(q.query, qid=q.qid, acl_groups=bundle.personas.get(q.persona))
        assert sum(b["tokens"] for b in trace.packed) <= pipe.cfg.evidence_token_cap


def test_baseline_quality_has_not_regressed(system):
    """A crude but real regression gate: these are the numbers in the README."""
    bundle, _, pipe = system
    rows = pipeline.evaluate(pipe, bundle.questions, pipe.chunks, personas=bundle.personas)
    s = metrics.summarize(rows)
    assert s["evidence_recall"] >= 0.70, s["evidence_recall"]
    assert s["full_chain_recall"] >= 0.40, s["full_chain_recall"]


def test_the_pipeline_is_deterministic(system):
    bundle, _, pipe = system
    a = pipeline.evaluate(pipe, bundle.questions[:40], pipe.chunks, personas=bundle.personas)
    b = pipeline.evaluate(pipe, bundle.questions[:40], pipe.chunks, personas=bundle.personas)
    assert [r["evidence_recall"] for r in a] == [r["evidence_recall"] for r in b]
