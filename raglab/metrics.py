"""
Measurement. Built before the improvement, as the build brief insists.

Retrieval metrics here are computed against gold *evidence*, not gold
documents. That distinction is the whole reason MultiHop-RAG exists: on a
two-hop question, document recall lets a half-answer look like a pass. The
number that predicts a correct answer is full-chain recall -- the fraction of
questions where *every* gold item made it into top-k -- and it is always lower
than the average people quote.

The other thing this module takes seriously is the noise band. Our pipeline is
deterministic, so re-running it changes nothing; the uncertainty that actually
matters is sampling variance over a finite eval set. `paired_bootstrap()`
measures it, and a delta smaller than its interval is not a result.
"""
from __future__ import annotations

import math
import re

_WS = re.compile(r"\s+")


def _norm(s):
    return _WS.sub(" ", str(s)).strip().lower()


# ------------------------------------------------------- gold resolution ----
# Normalising every chunk once per question is O(questions x chunks) regex work and
# dominates a full evaluation. The chunk list does not change inside a run, so memoise
# it -- keyed on identity, with a couple of slots because a notebook holds several
# chunkings at once.
_NORM_CACHE = {}


def _normed_chunks(chunks):
    key = id(chunks)
    entry = _NORM_CACHE.get(key)
    if entry is not None and entry[0] is chunks and len(entry[1]) == len(chunks):
        return entry[1]
    normed = [(c.chunk_id, _norm(c.text)) for c in chunks]
    if len(_NORM_CACHE) > 4:
        _NORM_CACHE.clear()
    _NORM_CACHE[key] = (chunks, normed)
    return normed


def resolve_gold(question, chunks):
    """Map each gold evidence anchor to the set of chunks that contain it.

    Resolution happens *against the current chunking*, which is the honest way
    to do it: change your chunk boundaries and the set of chunks that satisfy a
    gold item genuinely changes. An anchor no chunking can satisfy is a broken
    label, and `unresolved` surfaces it instead of silently scoring a zero.
    """
    mapping, unresolved = {}, []
    normed = _normed_chunks(chunks)
    for anchor in question.evidence_anchors:
        a = _norm(anchor)
        hits = {cid for cid, txt in normed if a and a in txt}
        if hits:
            mapping[anchor] = hits
        else:
            unresolved.append(anchor)
    return mapping, unresolved


def gold_chunk_ids(question, chunks):
    m, _ = resolve_gold(question, chunks)
    return {cid for s in m.values() for cid in s}


# --------------------------------------------------------------- metrics ----
def evidence_recall_at_k(retrieved_ids, gold_map, k=None):
    """|gold evidence found| / |gold evidence|, counted per evidence item."""
    if not gold_map:
        return None
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    found = sum(1 for _, cids in gold_map.items() if cids & got)
    return found / len(gold_map)


def full_chain_recall(retrieved_ids, gold_map, k=None):
    """1.0 only when every gold item is present. The multi-hop metric."""
    if not gold_map:
        return None
    got = set(retrieved_ids[:k] if k else retrieved_ids)
    return 1.0 if all(cids & got for cids in gold_map.values()) else 0.0


def mrr(retrieved_ids, gold_map):
    if not gold_map:
        return None
    gold = {cid for s in gold_map.values() for cid in s}
    for i, cid in enumerate(retrieved_ids, 1):
        if cid in gold:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved_ids, gold_map, k=10):
    """Graded nDCG where each distinct gold evidence item is worth 1.

    Rewards finding *different* gold items early rather than three chunks that
    all satisfy the same hop -- which is the failure mode a naive Recall@k
    cannot see.
    """
    if not gold_map:
        return None
    items = list(gold_map.values())
    dcg, seen = 0.0, set()
    for i, cid in enumerate(retrieved_ids[:k], 1):
        for j, cids in enumerate(items):
            if j not in seen and cid in cids:
                dcg += 1.0 / math.log2(i + 1)
                seen.add(j)
                break
    ideal = sum(1.0 / math.log2(i + 1) for i in range(1, min(len(items), k) + 1))
    return dcg / ideal if ideal else None


def context_precision(packed_ids, gold_map):
    """Share of packed chunks that carry any gold evidence.

    The complement is your distractor rate -- the slots a gold chunk could
    have used.
    """
    if not packed_ids:
        return 0.0
    gold = {cid for s in gold_map.values() for cid in s}
    return sum(1 for c in packed_ids if c in gold) / len(packed_ids)


# ------------------------------------------------- answer-side measures -----
def answer_correct(answer, gold_answer, mode="contains"):
    """Deliberately crude string scoring, used only where it is defensible.

    Numeric and named-entity answers can be scored this way honestly. Anything
    open-ended goes to the judge in `judge.py`, and the deck's warning applies:
    an answer-only metric can be right by accident while retrieval missed
    everything.
    """
    a, g = _norm(answer), _norm(gold_answer)
    if not a:
        return 0.0
    if mode == "exact":
        return 1.0 if a == g else 0.0
    key = [t for t in re.split(r"[^a-z0-9$%.]+", g) if len(t) > 2][:6]
    if not key:
        return 1.0 if g in a else 0.0
    return 1.0 if sum(1 for t in key if t in a) / len(key) >= 0.6 else 0.0


ABSTAIN = "INSUFFICIENT_EVIDENCE"


def abstained(answer):
    return ABSTAIN.lower() in _norm(answer)


def abstention_scores(rows):
    """Precision / recall of refusal on the null set.

    A system that never abstains scores 0 recall here while every average-case
    metric stays flat -- which is the deck's point about null questions being
    the cheapest thing you can add to a client eval set.
    """
    tp = sum(1 for r in rows if r["is_null"] and r["abstained"])
    fp = sum(1 for r in rows if not r["is_null"] and r["abstained"])
    fn = sum(1 for r in rows if r["is_null"] and not r["abstained"])
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * prec * rec / (prec + rec)) if (prec and rec) else 0.0
    return {"abstention_precision": prec, "abstention_recall": rec, "abstention_f1": f1,
            "false_answers_on_null": fn, "over_refusals": fp}


def citation_accuracy(citations, packed_ids, gold_map):
    """Do the emitted source IDs resolve, and do they point at real evidence?

    Two different failures live here. A citation that does not resolve is a
    bug; a citation that resolves to a chunk that does not support the claim is
    a trust problem, and it is the one clients notice.
    """
    if not citations:
        return {"resolvable": None, "on_gold": None}
    resolvable = sum(1 for c in citations if c in packed_ids) / len(citations)
    gold = {cid for s in gold_map.values() for cid in s}
    on_gold = sum(1 for c in citations if c in gold) / len(citations)
    return {"resolvable": resolvable, "on_gold": on_gold}


# ------------------------------------------------------------- aggregate ----
def summarize(rows, keys=("evidence_recall", "full_chain_recall", "ndcg", "mrr",
                          "context_precision", "answer_correct")):
    out = {}
    for key in keys:
        vals = [r[key] for r in rows if r.get(key) is not None]
        out[key] = sum(vals) / len(vals) if vals else None
    out.update(abstention_scores(rows))
    out["n"] = len(rows)
    for key in ("tokens_in", "tokens_out", "latency_ms", "cost_usd"):
        vals = [r.get(key) for r in rows if r.get(key) is not None]
        if vals:
            out[key] = sum(vals) / len(vals)
            out[f"{key}_p95"] = sorted(vals)[max(0, int(0.95 * len(vals)) - 1)]
    return out


def slice_report(rows, by="question_type",
                 keys=("evidence_recall", "full_chain_recall", "answer_correct")):
    """Never ship an average without the slices underneath it."""
    import pandas as pd

    groups = {}
    for r in rows:
        groups.setdefault(r.get(by, "?"), []).append(r)
    out = []
    for name, grp in sorted(groups.items()):
        rec = {by: name, "n": len(grp)}
        for key in keys:
            vals = [g[key] for g in grp if g.get(key) is not None]
            rec[key] = round(sum(vals) / len(vals), 3) if vals else None
        out.append(rec)
    return pd.DataFrame(out)


# ---------------------------------------------------------- significance ----
def paired_bootstrap(rows_a, rows_b, key="full_chain_recall", n_boot=2000, seed=11):
    """Is the delta real, or is it the eval set being small?

    Resamples questions with replacement, keeping A and B paired on the same
    question -- pairing removes question difficulty from the comparison, which
    is why it detects smaller true differences than two independent samples.
    Returns the observed delta, a 95% interval, and the share of resamples in
    which B beat A.
    """
    import random

    ida = {r["qid"]: r for r in rows_a}
    idb = {r["qid"]: r for r in rows_b}
    common = [q for q in ida if q in idb
              and ida[q].get(key) is not None and idb[q].get(key) is not None]
    if not common:
        return {"delta": None, "ci": (None, None), "p_better": None, "n": 0}
    obs = (sum(idb[q][key] for q in common) - sum(ida[q][key] for q in common)) / len(common)
    rng = random.Random(seed)
    deltas = []
    for _ in range(n_boot):
        pick = [common[rng.randrange(len(common))] for _ in common]
        d = (sum(idb[q][key] for q in pick) - sum(ida[q][key] for q in pick)) / len(pick)
        deltas.append(d)
    deltas.sort()
    lo = deltas[int(0.025 * n_boot)]
    hi = deltas[int(0.975 * n_boot) - 1]
    verdict = "real" if lo > 0 else ("regression" if hi < 0 else "inside the noise band")
    return {"delta": obs, "ci": (lo, hi),
            "p_better": sum(1 for d in deltas if d > 0) / n_boot,
            "n": len(common), "metric": key, "verdict": verdict}


def cohens_kappa(a, b):
    """Agreement corrected for chance.

    Raw agreement flatters a judge on a skewed set: one that always says
    "pass" scores 90% on a set that is 90% passes and has learned nothing.
    Kappa is what makes a judge's verdict evidence.
    """
    assert len(a) == len(b) and a, "need equal, non-empty label lists"
    labels = sorted(set(a) | set(b))
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((a.count(l) / n) * (b.count(l) / n) for l in labels)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def agreement_report(judge, human):
    k = cohens_kappa(list(judge), list(human))
    raw = sum(1 for x, y in zip(judge, human) if x == y) / len(judge)
    band = ("poor" if k < 0.2 else "fair" if k < 0.4 else "moderate" if k < 0.6
            else "substantial" if k < 0.8 else "almost perfect")
    return {"cohens_kappa": round(k, 3), "raw_agreement": round(raw, 3), "strength": band,
            "n": len(judge)}
