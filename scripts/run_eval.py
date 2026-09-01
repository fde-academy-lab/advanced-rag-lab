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
    args = ap.parse_args()

    if args.compare:
        return compare(args.slice)

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
