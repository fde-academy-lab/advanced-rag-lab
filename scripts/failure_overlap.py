#!/usr/bin/env python3
"""Do the two retrieval legs fail on the same questions, or on different ones?

This is the diagnostic that decides whether fusion can pay at all, and almost nobody runs it
before choosing a fusion rule. Fusion recovers a question only when one leg finds evidence the
other missed. If the legs fail together, a merge has nothing to recover and every hour spent
tuning α is spent moving a number inside its own confidence interval.

    D = answerable questions the dense leg misses
    L = answerable questions the lexical leg misses

    P(lexical also misses | dense misses) = |D ∩ L| / |D|

A **conditional probability**, not a Jaccard index. Jaccard answers "how similar are these two
failure sets", which nobody asked; the question is "if dense missed it, is BM25 any help".
Both are printed here precisely because they are close enough to be mistaken for each other.

A question is a **miss** for a leg when that leg's top-k, after reranking, does not contain
*all* of its gold evidence — `evidence_recall < 1.0`. Not "scored zero": partial recall on a
four-piece question is still a failure of that question, and full-chain recall is the metric
this repository gates on.

    python scripts/failure_overlap.py                  # no network, no key
    python scripts/failure_overlap.py --with-personas  # through the shipped pipeline instead
    python scripts/failure_overlap.py --json

The default run deliberately has the persona ACL filter **off**, matching R3's grader and the
0.9684 the repository publishes. `--with-personas` runs the shipped pipeline instead, which is
the configuration the fusion table comes from. It answers 0.9910 — filtering by persona removes
reachable evidence, so both legs miss more and they miss it together. The conclusion is the
same either way, which is the useful part: it does not hinge on the configuration.

Written because the numbers it prints were quoted in a correction to a retracted finding, and a
number quoted in a retraction had better have a command behind it. That is the whole lesson of
ADR-0015.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from raglab.bootstrap import bootstrap  # noqa: E402

bootstrap(verbose=False, allow_install=False)

K = 8
N_CANDIDATES = 100

# Deliberately the same construction as `lab-simulator/units/R3-fusion-measured/check.py`,
# down to the encoder dimension and the absence of a persona filter. R3 grades a learner
# against `failure_overlap ≥ 0.9000` and tells them the true value is 0.9684; if this script
# and that check disagreed, one of them would be quietly wrong and the learner would be the
# one who found out. The ACL pre-filter is off for the same reason it is off there — the
# question is about the retrievers, and filtering by persona changes what is reachable.


def _legs():
    """The corpus, the index, the two unfused retrievers and the reranker."""
    from raglab import chunking, corpus, embed, retrieve, store

    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy="structural")
    emb = embed.LsaEmbedder(dim=96).fit([d.title + "\n" + d.body for d in bundle.documents])
    index = store.InMemoryIndex()
    index.upsert(chunks, emb.encode_documents([ch.text for ch in chunks]),
                 index_version="v1", embedder_tag=emb.info.tag)
    index.set_alias("live", "v1")

    cfg = retrieve.RetrievalConfig(n_candidates=N_CANDIDATES, k=K, fusion="rrf")
    return (bundle, chunks, cfg,
            {"dense": retrieve.DenseRetriever(index, emb),
             "lexical": retrieve.LexicalRetriever(index)},
            retrieve.make_reranker("cross", emb))


def summary_with_personas() -> dict:
    """The same quantity through the shipped pipeline, ACL filter and all."""
    import raglab
    from raglab import pipeline

    found: dict[str, set[str]] = {}
    total = 0
    for name, cfg in (("dense", {"fusion": "dense", "alpha": 1.0}),
                      ("lexical", {"fusion": "lexical", "alpha": 0.0})):
        bundle, _, pipe = raglab.quickstart(**{**raglab.TUNED, **cfg}, verbose=False)
        rows = pipeline.evaluate(pipe, bundle.questions, pipe.chunks, personas=bundle.personas)
        graded = [r for r in rows if r.get("evidence_recall") is not None]
        total = len(graded)
        found[name] = {r["qid"] for r in graded if r["evidence_recall"] < 1.0}
    return _ratios(total, found["dense"], found["lexical"])


def _ratios(total: int, d: set[str], l: set[str]) -> dict:
    both, union = d & l, d | l
    return {
        "answerable": total,
        "dense_misses": len(d),
        "lexical_misses": len(l),
        "both_miss": len(both),
        "conditional": round(len(both) / len(d), 4) if d else 0.0,
        "jaccard": round(len(both) / len(union), 4) if union else 0.0,
        "only_dense_misses": len(d - l),
        "only_lexical_misses": len(l - d),
    }


def summary() -> dict:
    from raglab import metrics

    bundle, chunks, cfg, legs, reranker = _legs()
    # A question with no gold evidence is the abstention question, not a retrieval failure.
    graded = [(q, g) for q in bundle.questions if (g := metrics.resolve_gold(q, chunks)[0])]

    found: dict[str, set[str]] = {"dense": set(), "lexical": set()}
    for q, gold in graded:
        for name, retriever in legs.items():
            hits = retriever.search(q.query, N_CANDIDATES, cfg)
            top = [h.chunk_id for h in reranker.rerank(q.query, hits[:N_CANDIDATES])[:K]]
            if metrics.evidence_recall_at_k(top, gold) < 1.0:
                found[name].add(q.qid)

    return _ratios(len(graded), found["dense"], found["lexical"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-personas", action="store_true",
                    help="run the shipped pipeline, ACL filter included, instead of R3's setup")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    s = summary_with_personas() if args.with_personas else summary()
    if args.json:
        print(json.dumps(s, indent=2))
        return 0

    how = "shipped pipeline, personas on" if args.with_personas else "R3's setup, personas off"
    print(f"\n{s['answerable']} answerable questions, k={K}, "
          f"n_candidates={N_CANDIDATES}, rerank=cross — {how}\n")
    print(f"  dense leg misses              {s['dense_misses']:>4}")
    print(f"  lexical leg misses            {s['lexical_misses']:>4}")
    print(f"  both miss                     {s['both_miss']:>4}")
    print(f"  only dense misses             {s['only_dense_misses']:>4}"
          "   ← questions fusion could recover from the lexical leg")
    print(f"  only lexical misses           {s['only_lexical_misses']:>4}"
          "   ← and from the dense leg\n")
    print(f"  P(lexical also misses | dense misses)   {s['conditional']:.4f}"
          "   ← the one that answers the question")
    print(f"  Jaccard of the two failure sets         {s['jaccard']:.4f}"
          "   ← the plausible wrong formula\n")

    verdict = ("near 1, so the legs fail together and fusion has almost nothing to recover"
               if s["conditional"] > 0.9 else
               "well below 1, so the legs are complementary and fusion has room to pay")
    print(f"  The conditional is {verdict}.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
