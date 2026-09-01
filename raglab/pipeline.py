"""
The pipeline: one object that holds a whole RAG configuration, and the harness
that runs an eval set through it.

The build brief says harness first -- runner, metrics and a results table
before any retrieval code, because if you cannot measure it you are not allowed
to change it. This is that harness. A configuration is a value you can copy and
mutate, so "change one thing, re-run, write down the delta" is three lines
rather than an afternoon.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, replace

from . import metrics as M
from .context import build_prompt
from .generate import ExtractiveGenerator
from .retrieve import (
    HybridRetriever,
    RetrievalConfig,
    make_reranker,
    pack_context,
    reranker_ceiling,
)
from .trace import Trace, TraceStore


@dataclass
class RagPipeline:
    index: object
    embedder: object
    cfg: RetrievalConfig = field(default_factory=RetrievalConfig)
    generator: object = None
    reranker: object = None
    trace_store: TraceStore = None
    name: str = "baseline"

    def __post_init__(self):
        self.retriever = HybridRetriever(self.index, self.embedder)
        self.generator = self.generator or ExtractiveGenerator()
        self.reranker = self.reranker or make_reranker(self.cfg.rerank, self.embedder)
        self.trace_store = self.trace_store or TraceStore()

    # ------------------------------------------------------------ variants --
    def variant(self, name=None, **cfg_updates):
        """A copy of this pipeline with some knobs changed. Change one thing."""
        new_cfg = replace(self.cfg, **cfg_updates)
        rr = self.reranker
        if "rerank" in cfg_updates:
            rr = make_reranker(new_cfg.rerank, self.embedder)
        return RagPipeline(self.index, self.embedder, new_cfg, self.generator, rr,
                           self.trace_store, name or self.name)

    # ---------------------------------------------------------------- run ---
    def run(self, query, qid="", persona="", acl_groups=None, record=True):
        cfg = self.cfg
        if acl_groups is not None:
            cfg = replace(cfg, acl_groups=tuple(acl_groups))
        stage_ms = {}

        t0 = time.perf_counter()
        candidates = self.retriever.search(query, cfg)
        stage_ms["retrieve"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        reranked = self.reranker.rerank(query, candidates, depth=cfg.rerank_depth)
        stage_ms["rerank"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        selected, used = pack_context(reranked, k=cfg.k, token_cap=cfg.evidence_token_cap,
                                      dedup=cfg.dedup, order=cfg.order)
        k_before_filter = len(selected)
        if cfg.filter_mode == "post" and cfg.acl_groups is not None:
            # The wrong design, implemented faithfully so its two failures are
            # measurable: k collapses (a narrowly-scoped user gets two chunks
            # instead of eight) and the restricted documents have already
            # influenced the ranking of everything around them.
            allowed = set(cfg.acl_groups)
            selected = [h for h in selected if allowed & set(h.acl)]
        packed = build_prompt(query, selected, k=cfg.k, token_cap=cfg.evidence_token_cap)
        stage_ms["pack"] = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        answer = self.generator.generate(query, packed)
        stage_ms["generate"] = (time.perf_counter() - t0) * 1000

        trace = Trace(
            trace_id=uuid.uuid5(uuid.NAMESPACE_URL, f"{self.name}|{qid}|{query}").hex[:16],
            qid=qid, query=query, persona=persona, index_version=cfg.index_version,
            config={"name": self.name, **{k: v for k, v in cfg.__dict__.items()}},
            stage_ms={k: round(v, 2) for k, v in stage_ms.items()},
            candidates=[{"chunk_id": h.chunk_id, "doc_id": h.doc_id, "score": round(h.score, 5),
                         "rank": h.rank, "method": h.method} for h in candidates],
            reranked=[{"chunk_id": h.chunk_id, "score": round(h.score, 5), "rank": h.rank}
                      for h in reranked[: max(cfg.k * 3, 24)]],
            k_collapse=k_before_filter - len(selected),
            packed=[{"sid": b["sid"], "chunk_id": b["chunk_id"], "doc_id": b["doc_id"],
                     "tokens": b["tokens"], "score": round(b["score"], 5)}
                    for b in packed.blocks],
            answer=answer.text, citations=answer.citations, usage=answer.usage,
        )
        trace._packed_obj = packed
        trace._answer_obj = answer
        trace._candidates = candidates
        trace._selected = selected
        if record:
            self.trace_store.put(trace)
        return trace


# ------------------------------------------------------------------ eval ----
def evaluate(pipeline, questions, chunks, k_report=None, personas=None, progress=False,
             rates=None):
    """Run an eval set and return one row per question plus the aggregate.

    Every row carries the retrieval metrics, the answer metrics, the token and
    latency counters, and the ids needed to attribute a failure -- which is
    what makes the fault-isolation tree runnable in notebook 01.
    """
    from .costs import Rates

    rates = rates or Rates()
    rows = []
    for i, q in enumerate(questions):
        acl = None
        if personas:
            acl = personas.get(q.persona)
        tr = pipeline.run(q.query, qid=q.qid, persona=q.persona, acl_groups=acl)
        gold_map, unresolved = M.resolve_gold(q, chunks)
        cand_ids = tr.candidate_ids
        packed_ids = tr.packed_ids
        kk = k_report or pipeline.cfg.k

        cites = [tr._packed_obj.resolve(c) for c in tr.citations]
        cites = [c for c in cites if c]
        row = {
            "qid": q.qid, "query": q.query, "question_type": q.question_type,
            "hops": q.hops, "difficulty": q.difficulty, "slice": q.slice,
            "persona": q.persona, "is_null": q.question_type == "null",
            "gold_items": len(gold_map), "unresolved_gold": len(unresolved),
            "evidence_recall": M.evidence_recall_at_k(packed_ids, gold_map),
            "evidence_recall_at_N": M.evidence_recall_at_k(cand_ids, gold_map),
            "full_chain_recall": M.full_chain_recall(packed_ids, gold_map),
            "full_chain_recall_at_N": M.full_chain_recall(cand_ids, gold_map),
            "ndcg": M.ndcg_at_k(cand_ids, gold_map, k=kk),
            "mrr": M.mrr(cand_ids, gold_map),
            "context_precision": M.context_precision(packed_ids, gold_map),
            "ceiling": reranker_ceiling(tr._candidates, {c for s in gold_map.values() for c in s}),
            "answer": tr.answer,
            "abstained": M.abstained(tr.answer),
            "answer_correct": (1.0 if M.abstained(tr.answer) else 0.0) if q.question_type == "null"
                              else M.answer_correct(tr.answer, q.answer),
            "citation_resolvable": M.citation_accuracy(cites, packed_ids, gold_map)["resolvable"],
            "citation_on_gold": M.citation_accuracy(cites, packed_ids, gold_map)["on_gold"],
            "tokens_in": tr.usage.get("input_tokens") or 0,
            "tokens_out": tr.usage.get("output_tokens") or 0,
            "latency_ms": round(sum(tr.stage_ms.values()), 2),
            "trace_id": tr.trace_id,
        }
        row["cost_usd"] = rates.cost(row["tokens_in"], row["tokens_out"])
        rows.append(row)
        if progress and (i + 1) % 20 == 0:
            print(f"  … {i + 1}/{len(questions)}")
    return rows


def results_frame(rows):
    import pandas as pd

    return pd.DataFrame(rows)


def scorecard(rows, name="run"):
    """The one-line summary a release gate reads."""
    s = M.summarize(rows)
    s["name"] = name
    return s


def compare_runs(named_rows, keys=("evidence_recall", "full_chain_recall", "answer_correct",
                                   "context_precision", "abstention_recall", "cost_usd",
                                   "latency_ms")):
    import pandas as pd

    out = []
    for name, rows in named_rows.items():
        s = M.summarize(rows)
        rec = {"run": name, "n": s["n"]}
        for key in keys:
            v = s.get(key)
            rec[key] = round(v, 4) if isinstance(v, (int, float)) else v
        out.append(rec)
    return pd.DataFrame(out)
