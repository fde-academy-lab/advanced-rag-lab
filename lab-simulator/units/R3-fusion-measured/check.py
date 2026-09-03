#!/usr/bin/env python3
"""Checks for R3 · Build the rule you rejected, and the measurement that rejected it.

This is the first unit graded against the real thing: it builds Client Zero, runs both retrieval
legs, puts the learner's fusion through the repository's own cross-encoder, and reports two
numbers to the grader's bars.

Structural checks run on synthetic legs first and the corpus is only built if they pass. A
learner with a syntax error should wait a second for the answer, not eight.
"""
from __future__ import annotations

import dataclasses
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

K = 60


@dataclasses.dataclass
class FakeHit:
    chunk_id: str
    score: float = 0.0
    rank: int = 0
    text: str = ""
    doc_id: str = ""


def leg(ids, start_rank=1):
    """A leg whose `.rank` field deliberately disagrees with the position in the list.

    An upstream pre-filter leaves gaps in `rank`. A fusion rule that trusts a field it did not
    compute inherits every upstream change silently, so the checks make the two disagree.
    """
    return [FakeHit(chunk_id=c, score=1.0 - i / 100, rank=start_rank + i * 7)
            for i, c in enumerate(ids)]


def ids_of(hits):
    return [h.chunk_id for h in hits]


def structural(mod, c: Checker) -> bool:
    rrf, overlap = mod.rrf, mod.failure_overlap

    out = rrf([leg(["a", "b", "c"])], k=K)
    if not c("returns hit objects, not ids or tuples",
             bool(out) and all(hasattr(h, "chunk_id") for h in out),
             f"got {type(out[0]).__name__ if out else 'nothing'}"):
        return False

    c("a single leg comes back in its own order", ids_of(out) == ["a", "b", "c"],
      f"got {ids_of(out)}")

    # Pin the rank origin exactly, without reading any internals. At k=0 the first rank must
    # score 1/(0+1) = 1 and the second 1/(0+2) = 0.5, so "a" (1 + 0.5) must outrank "b" (1).
    # An implementation that enumerates from 0 divides by 0+0 here and says so loudly.
    try:
        probe = rrf([leg(["a"]), leg(["b", "a"])], k=0)
        c("rank 1 in a single leg scores exactly 1/(k+1)", ids_of(probe)[:1] == ["a"],
          f"at k=0, 'a' scores 1 + 1/2 and 'b' scores 1, so 'a' leads. Got {ids_of(probe)}")
    except ZeroDivisionError:
        c("rank 1 in a single leg scores exactly 1/(k+1)", False,
          "dividing by zero at k=0 means the enumeration starts at 0. Use "
          "enumerate(leg, start=1) — starting at 0 makes the top hit score 1/k and the "
          "second 1/(k+1), inverting the gap at the only rank where it matters")

    fused = rrf([leg(["a", "b"]), leg(["b", "c"])], k=K)
    c("a chunk found by only one leg still survives", set(ids_of(fused)) == {"a", "b", "c"},
      f"got {sorted(ids_of(fused))} — dropping single-leg chunks makes this an intersection, "
      "and single-leg chunks are the reason for two retrievers")
    c("one entry per chunk_id", len(ids_of(fused)) == len(set(ids_of(fused))))
    c("a chunk in both legs outranks a chunk in one", ids_of(fused)[0] == "b",
      f"got {ids_of(fused)} — summing the two terms is the voting")

    c("position in the leg is used, not hit.rank",
      ids_of(rrf([leg(["x", "y"], start_rank=500)], k=K)) == ["x", "y"],
      "a leg whose .rank starts at 500 must fuse the same as one starting at 1")

    c("an empty leg is survivable",
      ids_of(rrf([leg(["a", "b"]), []], k=K)) == ["a", "b"],
      "a retriever returning nothing is a Tuesday, not an exception")
    c("no legs at all returns nothing", rrf([], k=K) == [])

    c("failure_overlap is conditional, not symmetric",
      abs(overlap({"q1", "q2", "q3", "q4"}, {"q1", "q2", "q3"}) - 0.75) < 1e-9,
      f"|D and L| / |D| = 3/4 = 0.75; got "
      f"{overlap({'q1', 'q2', 'q3', 'q4'}, {'q1', 'q2', 'q3'})}. Jaccard would give 0.75 here "
      "too — but 3/4 against |D|=4 and |union|=4 only coincide when L is a subset")
    c("failure_overlap divides by |D|, not by the union",
      abs(overlap({"q1", "q2"}, {"q2", "q3", "q4"}) - 0.5) < 1e-9,
      f"|D and L| / |D| = 1/2 = 0.5; got {overlap({'q1', 'q2'}, {'q2', 'q3', 'q4'})}. "
      "Jaccard here is 1/4 = 0.25")
    c("failure_overlap of nothing is 0.0", overlap(set(), {"q1"}) == 0.0,
      "a leg that misses nothing has no failures to overlap")
    return c.ok


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("rrf", "failure_overlap"))
    c = Checker()
    if not structural(mod, c):
        c.note("Structural checks failed, so the corpus was not built. Fix these first — the "
               "real run takes about eight seconds and it is not worth spending on a bug a "
               "synthetic leg can find.")
        return emit({}, c)

    c.note("Structural checks pass. Building Client Zero and measuring for real...")
    try:
        metrics_out = measure(mod, c)
    except Exception as exc:  # noqa: BLE001
        c("the real run completes", False, f"{type(exc).__name__}: {exc}")
        return emit({}, c)
    return emit(metrics_out, c)


def measure(mod, c: Checker) -> dict:
    from raglab import chunking, corpus, embed, metrics, retrieve, store

    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy="structural")
    emb = embed.LsaEmbedder(dim=96).fit([d.title + "\n" + d.body for d in bundle.documents])
    index = store.InMemoryIndex()
    index.upsert(chunks, emb.encode_documents([ch.text for ch in chunks]),
                 index_version="v1", embedder_tag=emb.info.tag)
    index.set_alias("live", "v1")

    cfg = retrieve.RetrievalConfig(n_candidates=100, k=8, fusion="rrf")
    lexical = retrieve.LexicalRetriever(index)
    dense = retrieve.DenseRetriever(index, emb)
    reranker = retrieve.make_reranker("cross", emb)

    graded = [(q, g) for q in bundle.questions
              if (g := metrics.resolve_gold(q, chunks)[0])]

    recalls: list[float] = []
    dense_misses: set[str] = set()
    lexical_misses: set[str] = set()

    for q, gold in graded:
        d_leg = dense.search(q.query, 100, cfg)
        l_leg = lexical.search(q.query, 100, cfg)

        fused = mod.rrf([d_leg, l_leg], k=60)
        top = [h.chunk_id for h in reranker.rerank(q.query, list(fused)[:100])[:8]]
        recalls.append(metrics.evidence_recall_at_k(top, gold))

        for legs, misses in ((d_leg, dense_misses), (l_leg, lexical_misses)):
            ids = [h.chunk_id for h in reranker.rerank(q.query, legs[:100])[:8]]
            if metrics.evidence_recall_at_k(ids, gold) < 1.0:
                misses.add(q.qid)

    evidence_recall = statistics.mean(recalls)
    reported = float(mod.failure_overlap(dense_misses, lexical_misses))
    truth = len(dense_misses & lexical_misses) / len(dense_misses)

    c("the real run completes", True)
    c.note(f"{len(graded)} answerable questions · dense missed {len(dense_misses)} · "
           f"lexical missed {len(lexical_misses)} · both missed "
           f"{len(dense_misses & lexical_misses)}")
    c("failure_overlap matches the conditional computed independently",
      abs(reported - truth) < 1e-6,
      f"you reported {reported:.4f}; |D and L|/|D| is {truth:.4f}")
    if abs(reported - truth) < 1e-6:
        c.note(f"{truth:.4f} of the questions the dense leg misses are also missed by BM25. "
               "That is what the fusion argument was about, and it took one line.")
    return {"evidence_recall": evidence_recall, "failure_overlap": reported}


if __name__ == "__main__":
    sys.exit(run(main))
