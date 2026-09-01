#!/usr/bin/env python3
"""Run the evaluation suite and print the scorecard the release gate reads.

This is the CI entry point for `.github/workflows/eval-regression.yml`. It writes
`eval-report.json` so the workflow can diff it against the baseline committed at
`.github/eval-baseline.json` and fail the build on a regression.

    python scripts/run_eval.py                     # full set
    python scripts/run_eval.py --slice frozen      # the held-out slice only
    python scripts/run_eval.py --baseline          # rewrite the committed baseline
    python scripts/run_eval.py --fusion rrf        # one configuration, off the baseline
    python scripts/run_eval.py --compare           # every fusion rule, with paired bootstrap

`--compare` is what produced the table in docs/09-research/measurements/fusion-rules.md, and it
is here rather than in a notebook because a claim about which retriever wins should be
re-runnable by whoever doubts it, in one command, without reading anything first.
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

import raglab  # noqa: E402
from raglab import metrics, pipeline  # noqa: E402

BASELINE = ROOT / ".github" / "eval-baseline.json"
TOLERANCE = {"evidence_recall": 0.02, "full_chain_recall": 0.03, "answer_correct": 0.03}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", choices=["all", "dev", "frozen"], default="all")
    ap.add_argument("--baseline", action="store_true", help="rewrite the committed baseline")
    ap.add_argument("--out", default="eval-report.json")
    ap.add_argument("--fusion", choices=["rrf", "weighted", "dense", "lexical"],
                    help="override the tuned fusion rule")
    ap.add_argument("--alpha", type=float, help="override the dense weight for weighted fusion")
    ap.add_argument("--rerank", choices=["cross", "late", "none"], help="override the reranker")
    ap.add_argument("--k", type=int, help="override the number of chunks packed")
    ap.add_argument("--compare", action="store_true",
                    help="every fusion rule against every other, with a paired bootstrap")
    ap.add_argument("--sweep", action="store_true",
                    help="the weighted rule across the alpha grid, all four metrics")
    ap.add_argument("--ksweep", action="store_true",
                    help="three fusion arms across the k grid, with and without the reranker")
    args = ap.parse_args()

    if args.compare:
        return compare(args.slice)
    if args.sweep:
        return sweep(args.slice)
    if args.ksweep:
        return ksweep(args.slice)

    cfg = dict(raglab.TUNED)
    overridden = {k: v for k, v in
                  (("fusion", args.fusion), ("alpha", args.alpha),
                   ("rerank", args.rerank), ("k", args.k)) if v is not None}
    cfg.update(overridden)
    bundle, _, pipe = raglab.quickstart(**cfg, verbose=False)
    questions = [q for q in bundle.questions
                 if args.slice == "all" or q.slice == args.slice]
    rows = pipeline.evaluate(pipe, questions, pipe.chunks, personas=bundle.personas)
    summary = metrics.summarize(rows)

    report = {
        "config": pipe.name,
        "slice": args.slice,
        "n": len(questions),
        "metrics": {k: (round(v, 4) if isinstance(v, (int, float)) else v)
                    for k, v in summary.items() if v is not None},
        "by_question_type": json.loads(
            metrics.slice_report(rows).to_json(orient="records")),
    }
    pathlib.Path(args.out).write_text(json.dumps(report, indent=2))

    print(f"config   {report['config']}")
    print(f"slice    {args.slice} ({len(questions)} questions)")
    for key in ("evidence_recall", "full_chain_recall", "context_precision",
                "answer_correct", "abstention_recall", "cost_usd"):
        val = summary.get(key)
        if val is not None:
            print(f"  {key:<22} {val:.4f}")

    if args.baseline:
        BASELINE.write_text(json.dumps(report, indent=2))
        print(f"\nbaseline rewritten → {BASELINE.relative_to(ROOT)}")
        return 0

    if overridden:
        # The baseline is cut from one configuration. Gating a different one against it would
        # report a "regression" for every deliberate experiment, which is how a release gate
        # teaches people to ignore it.
        print(f"\nnot gated: running {overridden} rather than the baseline configuration")
        return 0

    if not BASELINE.exists():
        print("\nno committed baseline; nothing to gate against")
        return 0

    prior = json.loads(BASELINE.read_text())["metrics"]
    failures = []
    print("\ngate")
    for key, tol in TOLERANCE.items():
        before, after = prior.get(key), summary.get(key)
        if before is None or after is None:
            continue
        delta = after - before
        verdict = "BLOCK" if delta < -tol else "ok"
        if verdict == "BLOCK":
            failures.append(f"{key} {before:.4f} → {after:.4f} ({delta:+.4f}, tol {tol})")
        print(f"  {verdict:<6} {key:<22} {before:.4f} → {after:.4f}  ({delta:+.4f})")

    if failures:
        print("\nRELEASE BLOCKED:")
        for f in failures:
            print("  " + f)
        print("\nIf this change is intended, re-baseline in the same PR with:")
        print("  python scripts/run_eval.py --baseline")
        return 1
    print("\nall gated metrics within tolerance")
    return 0


# The configurations the fusion question is actually between. `alpha` is the *dense* weight.
ARMS = [
    ("bm25", {"fusion": "lexical", "alpha": 0.0}),
    ("dense", {"fusion": "dense", "alpha": 1.0}),
    ("rrf", {"fusion": "rrf", "alpha": 0.5}),
    ("w0.2", {"fusion": "weighted", "alpha": 0.2}),
    ("w0.5", {"fusion": "weighted", "alpha": 0.5}),
]
COMPARISONS = [("bm25", "rrf"), ("bm25", "dense"), ("dense", "rrf"), ("rrf", "w0.2"),
               ("rrf", "w0.5"), ("w0.2", "w0.5")]
KEYS = ("evidence_recall", "full_chain_recall", "ndcg", "answer_correct")


ALPHAS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.7)
KS = (3, 5, 8, 10, 20)
KSWEEP_ARMS = (("bm25", {"fusion": "lexical", "alpha": 0.0}),
               ("rrf", {"fusion": "rrf", "alpha": 0.5}),
               ("w0.2", {"fusion": "weighted", "alpha": 0.2}))


def ksweep(which_slice: str) -> int:
    """Evidence recall and context precision across k, with and without the reranker.

    Quoted in six seeded threads and in three exercise briefs and published nowhere, which is
    the condition both retracted findings were in. `context_precision` is on the same table
    deliberately: it moves the opposite way, monotonically, and the pair is the argument
    against gating on precision alone.
    """
    print(f"slice {which_slice}, rerank on the left, none on the right\n")
    head = (f"{'k':<5}" + "".join(f"{a:>12}" for a, _ in KSWEEP_ARMS)
            + f"{'ctx_prec':>12}" + "".join(f"{a + ' (raw)':>14}" for a, _ in KSWEEP_ARMS))
    print(head)
    print("-" * len(head))
    for k in KS:
        cells, raw = [], []
        prec = None
        for name, cfg in KSWEEP_ARMS:
            for rerank, sink in (("cross", cells), ("none", raw)):
                bundle, _, pipe = raglab.quickstart(
                    **{**raglab.TUNED, **cfg, "k": k, "rerank": rerank}, verbose=False)
                qs = [q for q in bundle.questions
                      if which_slice == "all" or q.slice == which_slice]
                s = metrics.summarize(pipeline.evaluate(pipe, qs, pipe.chunks,
                                                        personas=bundle.personas))
                sink.append(s["evidence_recall"])
                if rerank == "cross" and name == "bm25":
                    prec = s["context_precision"]
        print(f"{k:<5}" + "".join(f"{v:>12.4f}" for v in cells)
              + f"{prec:>12.4f}" + "".join(f"{v:>14.4f}" for v in raw))
    print("\nRecall rises with k and context precision falls, monotonically, because the")
    print("denominator is k and the gold set for a question is fixed. A target on precision")
    print("alone is therefore cleared by lowering k, which makes the system worse.")
    return 0


def sweep(which_slice: str) -> int:
    """The weighted rule across the alpha grid.

    `--compare` reports two points on this curve, w0.2 and w0.5, because those are the two the
    fusion decision was between. The curve itself kept being quoted from memory in threads and
    briefs with no command behind it, which is the shape of mistake ADR-0015 exists to prevent.
    It is one line now.

    No intervals here on purpose: adjacent alphas are not a decision anybody makes, and
    printing an interval per row would invite reading the grid as six comparisons. Use
    `--compare` for the two that matter.
    """
    print(f"slice {which_slice}, k={raglab.TUNED['k']}, rerank={raglab.TUNED['rerank']}, "
          "fusion=weighted; alpha is the DENSE weight\n")
    head = f"{'alpha':<8}" + "".join(f"{k:>19}" for k in KEYS)
    print(head)
    print("-" * len(head))
    for alpha in ALPHAS:
        bundle, _, pipe = raglab.quickstart(**{**raglab.TUNED, "fusion": "weighted",
                                               "alpha": alpha}, verbose=False)
        qs = [q for q in bundle.questions if which_slice == "all" or q.slice == which_slice]
        s = metrics.summarize(pipeline.evaluate(pipe, qs, pipe.chunks,
                                                personas=bundle.personas))
        marker = "  ← shipped" if abs(alpha - raglab.TUNED["alpha"]) < 1e-9 else ""
        print(f"{alpha:<8.1f}" + "".join(f"{s[k]:>19.4f}" for k in KEYS) + marker)
    print("\nEvidence recall and nDCG rise with the dense weight and answer correctness does")
    print("not move outside its noise band anywhere on this grid. That is the finding, and it")
    print("is why the shipped alpha has not been chased upward.")
    return 0


def compare(which_slice: str) -> int:
    """Every fusion rule, with the paired bootstrap that says which gaps are real.

    A table of means is not an answer to "which one should we ship", because a table of means
    cannot distinguish a 0.006 gap that would survive a corpus refresh from one that would not.
    That is the whole reason this prints intervals rather than a leaderboard.
    """
    rows = {}
    for name, cfg in ARMS:
        full = {**raglab.TUNED, **cfg}
        bundle, _, pipe = raglab.quickstart(**full, verbose=False)
        qs = [q for q in bundle.questions if which_slice == "all" or q.slice == which_slice]
        rows[name] = pipeline.evaluate(pipe, qs, pipe.chunks, personas=bundle.personas)

    print(f"slice {which_slice}, k={raglab.TUNED['k']}, rerank={raglab.TUNED['rerank']}\n")
    head = f"{'configuration':<16}" + "".join(f"{k:>19}" for k in KEYS)
    print(head)
    print("-" * len(head))
    for name, _ in ARMS:
        s = metrics.summarize(rows[name])
        print(f"{name:<16}" + "".join(f"{s[k]:>19.4f}" for k in KEYS))

    print("\npaired bootstrap over questions; delta is the second arm minus the first\n")
    for a, b in COMPARISONS:
        for key in KEYS:
            r = metrics.paired_bootstrap(rows[a], rows[b], key=key)
            print(f"  {a:>5} -> {b:<5} {key:<20} {r['delta']:+.4f}  "
                  f"ci({r['ci'][0]:+.4f}, {r['ci'][1]:+.4f})  {r['verdict']}")
        print()

    print("A difference inside the noise band is not a small difference. It is not a")
    print("difference, and shipping complexity to buy one is how a system accretes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
