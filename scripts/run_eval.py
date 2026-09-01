#!/usr/bin/env python3
"""Run the evaluation suite and print the scorecard the release gate reads.

This is the CI entry point for `.github/workflows/eval-regression.yml`. It writes
`eval-report.json` so the workflow can diff it against the baseline committed at
`.github/eval-baseline.json` and fail the build on a regression.

    python scripts/run_eval.py                     # full set
    python scripts/run_eval.py --slice frozen      # the held-out slice only
    python scripts/run_eval.py --baseline          # rewrite the committed baseline
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
    args = ap.parse_args()

    bundle, _, pipe = raglab.quickstart(**raglab.TUNED, verbose=False)
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


if __name__ == "__main__":
    sys.exit(main())
