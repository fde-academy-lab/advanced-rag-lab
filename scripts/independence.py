#!/usr/bin/env python3
"""Does full-chain recall sit above or below what independence predicts?

The question matters because the answer decides a roadmap. If measured full-chain recall is
well *below* independence, failures are correlated inside a question — some questions are hard
in a structural way, and the fix is to find what those share. If it sits at independence, there
is no structure to find: the multi-hop gap is entirely "you need k pieces and each is about
76% likely", and looking for a hidden cause is looking for something that is not there.

This repository asserted the first answer for months. It was arrived at by weighting `p^h` over
a hop mixture of "128 single-hop, 61 two-hop, 18 three-plus" — numbers that match neither the
`hops` field (77 / 130) nor the quantity the metric actually uses.

    full_chain_recall = 1.0 iff every gold *evidence piece* was retrieved

So the exponent is `len(gold_map)` — pieces of evidence — not hops. A two-hop question can carry
four pieces. Weighted over the real distribution the prediction moves from 0.6838 to 0.4603, and
the "21-point shortfall" it was built on disappears.

    python scripts/independence.py            # corpus + committed baseline, about a second
    python scripts/independence.py --measure  # also re-runs the eval for the micro rate
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from raglab.bootstrap import bootstrap  # noqa: E402

bootstrap(verbose=False, allow_install=False)

import raglab  # noqa: E402
from raglab import chunking, corpus, metrics, pipeline  # noqa: E402

BASELINE = ROOT / ".github" / "eval-baseline.json"


def gold_sizes(strategy: str = "structural") -> collections.Counter:
    """How many distinct pieces of evidence each answerable question needs."""
    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy=strategy)
    sizes = collections.Counter()
    for q in bundle.questions:
        g = metrics.resolve_gold(q, chunks)[0]
        if g:
            sizes[len(g)] += 1
    return sizes


def predict(sizes: collections.Counter, p: float) -> float:
    """Weighted `p^k` over the piece-count distribution."""
    return sum(n * (p ** k) for k, n in sizes.items()) / sum(sizes.values())


def summary(measure: bool = False) -> dict:
    sizes = gold_sizes()
    base = json.loads(BASELINE.read_text())["metrics"]
    macro, full = base["evidence_recall"], base["full_chain_recall"]

    out = {
        "answerable": sum(sizes.values()),
        "gold_pieces_per_question": {str(k): v for k, v in sorted(sizes.items())},
        "evidence_recall_macro": macro,
        "full_chain_recall": full,
        "prediction_macro": round(predict(sizes, macro), 4),
    }
    out["delta_macro"] = round(full - out["prediction_macro"], 4)

    if measure:
        bundle, _, pipe = raglab.quickstart(**raglab.TUNED, verbose=False)
        rows = pipeline.evaluate(pipe, bundle.questions, pipe.chunks, personas=bundle.personas)
        gold = {q.qid: metrics.resolve_gold(q, pipe.chunks)[0] for q in bundle.questions}
        found = total = 0
        for r in rows:
            g = gold.get(r["qid"])
            if not g:
                continue
            total += len(g)
            found += round(r["evidence_recall"] * len(g))
        micro = found / total
        out["evidence_recall_micro"] = round(micro, 4)
        out["prediction_micro"] = round(predict(sizes, micro), 4)
        out["delta_micro"] = round(full - out["prediction_micro"], 4)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--measure", action="store_true",
                    help="re-run the eval to get the micro per-piece rate (about 30s)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    s = summary(args.measure)
    if args.json:
        print(json.dumps(s, indent=2))
        return 0

    print(f"\n{s['answerable']} answerable questions\n")
    print("  pieces of gold evidence   questions")
    for k, n in s["gold_pieces_per_question"].items():
        print(f"      {k:>2}                    {n:>4}")

    print(f"\n  evidence_recall (macro)   {s['evidence_recall_macro']:.4f}"
          "   the number the scorecard reports")
    if "evidence_recall_micro" in s:
        print(f"  evidence_recall (micro)   {s['evidence_recall_micro']:.4f}"
              "   pieces found / pieces total")
    print(f"  full_chain_recall         {s['full_chain_recall']:.4f}   measured\n")

    for tag in ("macro", "micro"):
        if f"prediction_{tag}" not in s:
            continue
        pred, delta = s[f"prediction_{tag}"], s[f"delta_{tag}"]
        verdict = ("at independence" if abs(delta) < 0.02 else
                   "ABOVE independence" if delta > 0 else "BELOW independence")
        print(f"  independence prediction ({tag})  {pred:.4f}"
              f"   measured is {delta:+.4f} — {verdict}")

    print("\n  Below independence would mean failures cluster inside a question and there is")
    print("  structure to find. At or above it means there is not: the multi-hop gap is the")
    print("  arithmetic of needing k pieces, and nothing else.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
