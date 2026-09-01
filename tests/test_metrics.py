"""Metrics have to be right before anything they measure can be believed."""
import pytest

from raglab import metrics


@pytest.fixture
def gold():
    return {"hop A": {"c1", "c2"}, "hop B": {"c9"}}


def test_evidence_recall_counts_items_not_chunks(gold):
    assert metrics.evidence_recall_at_k(["c1"], gold) == 0.5
    assert metrics.evidence_recall_at_k(["c1", "c2"], gold) == 0.5   # same hop twice
    assert metrics.evidence_recall_at_k(["c1", "c9"], gold) == 1.0


def test_full_chain_recall_is_all_or_nothing(gold):
    assert metrics.full_chain_recall(["c1"], gold) == 0.0
    assert metrics.full_chain_recall(["c1", "c9"], gold) == 1.0


def test_full_chain_is_never_above_evidence_recall(gold):
    for retrieved in (["c1"], ["c9"], ["c1", "c9"], []):
        er = metrics.evidence_recall_at_k(retrieved, gold)
        fc = metrics.full_chain_recall(retrieved, gold)
        assert fc <= er + 1e-9


def test_ndcg_rewards_finding_different_hops_early(gold):
    early = metrics.ndcg_at_k(["c1", "c9"], gold, k=10)
    late = metrics.ndcg_at_k(["c1", "c2", "x", "y", "c9"], gold, k=10)
    assert early > late


def test_cohens_kappa_punishes_a_judge_that_always_passes():
    human = ["pass"] * 90 + ["fail"] * 10
    lazy = ["pass"] * 100
    assert metrics.cohens_kappa(lazy, human) == pytest.approx(0.0, abs=1e-6)
    agreement = sum(1 for a, b in zip(lazy, human) if a == b) / len(human)
    assert agreement == 0.9      # raw accuracy flatters it; kappa does not


def test_paired_bootstrap_calls_a_zero_delta_noise():
    rows = [{"qid": f"q{i}", "m": i % 2} for i in range(60)]
    out = metrics.paired_bootstrap(rows, list(rows), key="m")
    assert out["delta"] == 0.0
    assert out["verdict"] == "inside the noise band"


def test_paired_bootstrap_detects_a_real_improvement():
    a = [{"qid": f"q{i}", "m": 0.0} for i in range(80)]
    b = [{"qid": f"q{i}", "m": 1.0} for i in range(80)]
    out = metrics.paired_bootstrap(a, b, key="m")
    assert out["verdict"] == "real" and out["delta"] == 1.0


def test_abstention_scores_reward_refusing_only_the_nulls():
    rows = [{"is_null": True, "abstained": True}, {"is_null": True, "abstained": False},
            {"is_null": False, "abstained": False}]
    s = metrics.abstention_scores(rows)
    assert s["abstention_precision"] == 1.0
    assert s["abstention_recall"] == 0.5
    assert s["false_answers_on_null"] == 1
