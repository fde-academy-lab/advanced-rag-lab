#!/usr/bin/env python3
"""Timed interview drill over the question bank.

Reading questions is not practice. The gap between candidates at this level is rarely knowledge
— it is that one of them says in twenty seconds what the other takes ninety seconds to say, and
runs out of clock before the follow-up where the marks are. That is a timing skill and it only
improves under a timer.

    python interview-bank/practice.py                       # one random question
    python interview-bank/practice.py --drill models        # name the mental model first
    python interview-bank/practice.py --topic evaluation --tier senior
    python interview-bank/practice.py --loop 5              # five in a row, scored
    python interview-bank/practice.py --weakest             # what you have scored worst on

Scores go to interview-bank/.progress.json, which is gitignored — it is yours, not the repo's.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK = HERE / "questions.yaml"
PROGRESS = HERE / ".progress.json"

BANDS = ["misses", "screen", "mid", "senior"]
MODELS = ["two-timelines", "name-the-denominator", "cheapest-diagnostic-first", "the-third-case",
          "condition-not-law", "whose-budget", "what-would-make-this-false", "say-the-shape-first"]

DIM, BOLD, GREEN, YELLOW, RED, RESET = (
    "\033[90m", "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[0m")


def load_bank() -> list[dict]:
    try:
        import yaml
    except ImportError:
        sys.exit("pyyaml is needed:  pip install pyyaml   (or: pip install -e \".[dev]\")")
    return yaml.safe_load(BANK.read_text())["questions"]


def load_progress() -> dict:
    if PROGRESS.exists():
        try:
            return json.loads(PROGRESS.read_text())
        except ValueError:
            return {}
    return {}


def save_progress(p: dict) -> None:
    PROGRESS.write_text(json.dumps(p, indent=2, sort_keys=True) + "\n")


def ask(prompt: str, valid: list[str] | None = None) -> str:
    while True:
        try:
            answer = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n" + DIM + "stopped" + RESET)
            raise SystemExit(0) from None
        if not valid or answer in valid:
            return answer
        print(f"  {DIM}one of: {', '.join(valid)}{RESET}")


def run_one(q: dict, drill_models: bool, progress: dict) -> None:
    print(f"\n{DIM}{'─' * 74}{RESET}")
    print(f"{DIM}{q['id']} · {q['topic']} · {q['tier']}{RESET}\n")
    print(f"{BOLD}{q['q']}{RESET}\n")

    if drill_models:
        print(f"{DIM}Which mental model fires? (see mental-models.md){RESET}")
        for i, m in enumerate(MODELS, 1):
            print(f"  {i}. {m}")
        pick = ask("\n  number > ", [str(i) for i in range(1, len(MODELS) + 1)])
        guessed = MODELS[int(pick) - 1]
        if guessed == q["model"]:
            print(f"  {GREEN}✓ {guessed}{RESET}")
        else:
            print(f"  {YELLOW}the bank says {q['model']}{RESET} "
                  f"{DIM}(yours is not necessarily wrong — but be able to defend it){RESET}")

    print(f"\n{DIM}Answer out loud. 90 seconds. Enter when you are done.{RESET}")
    start = time.time()
    ask("")
    elapsed = time.time() - start

    colour = GREEN if elapsed <= 90 else (YELLOW if elapsed <= 120 else RED)
    print(f"  {colour}{elapsed:.0f}s{RESET}", end="")
    if elapsed > 120:
        print(f"  {DIM}— too long. In a real loop this eats the follow-up.{RESET}")
    else:
        print()

    print(f"\n{BOLD}The trap:{RESET} {q['trap']}")
    print(f"\n{BOLD}What each band sounds like:{RESET}")
    for band in reversed(BANDS):
        if band in q.get("signals", {}):
            print(f"  {band:<7} {q['signals'][band]}")
    if q.get("followups"):
        print(f"\n{BOLD}Queued follow-ups:{RESET}")
        for f in q["followups"]:
            print(f"  → {f}")
    print(f"\n{DIM}Full answer: {q['source']}{RESET}")

    band = ask(f"\n  Your band? [{'/'.join(BANDS)}/skip] > ", BANDS + ["skip"])
    if band != "skip":
        rec = progress.setdefault(q["id"], {"attempts": [], "seconds": []})
        rec["attempts"].append(band)
        rec["seconds"].append(round(elapsed))
        save_progress(progress)


def weakest(bank: list[dict], progress: dict) -> None:
    scored = [(qid, r) for qid, r in progress.items() if r.get("attempts")]
    if not scored:
        print("No attempts recorded yet. Run a few questions first.")
        return
    by_id = {q["id"]: q for q in bank}
    rows = []
    for qid, r in scored:
        worst = min(BANDS.index(a) for a in r["attempts"])
        latest = BANDS.index(r["attempts"][-1])
        rows.append((latest, worst, qid, r))
    rows.sort()
    print(f"\n{BOLD}Weakest first{RESET}\n")
    print(f"  {'id':<5} {'topic':<16} {'latest':<8} {'best':<8} {'attempts':<9} median s")
    for latest, worst, qid, r in rows:
        q = by_id.get(qid, {})
        secs = sorted(r["seconds"])
        median = secs[len(secs) // 2] if secs else 0
        best = BANDS[max(BANDS.index(a) for a in r["attempts"])]
        print(f"  {qid:<5} {q.get('topic', '?'):<16} {BANDS[latest]:<8} {best:<8} "
              f"{len(r['attempts']):<9} {median}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topic")
    ap.add_argument("--tier", choices=["screen", "mid", "senior", "staff"])
    ap.add_argument("--id", help="run one specific question")
    ap.add_argument("--drill", choices=["models"], help="name the mental model before answering")
    ap.add_argument("--loop", type=int, default=1, metavar="N", help="run N questions")
    ap.add_argument("--weakest", action="store_true", help="show your worst-scored questions")
    args = ap.parse_args()

    bank = load_bank()
    progress = load_progress()

    if args.weakest:
        weakest(bank, progress)
        return 0

    pool = bank
    if args.id:
        pool = [q for q in pool if q["id"].lower() == args.id.lower()]
    if args.topic:
        pool = [q for q in pool if q["topic"] == args.topic]
    if args.tier:
        pool = [q for q in pool if q["tier"] == args.tier]
    if not pool:
        sys.exit("No questions match those filters. Topics: "
                 + ", ".join(sorted({q["topic"] for q in bank})))

    # Prefer questions you have done least often, so a long session covers ground rather than
    # re-serving whatever the shuffle liked.
    pool.sort(key=lambda q: len(progress.get(q["id"], {}).get("attempts", [])))
    least = len(progress.get(pool[0]["id"], {}).get("attempts", []))
    front = [q for q in pool if len(progress.get(q["id"], {}).get("attempts", [])) == least]
    random.shuffle(front)
    chosen = (front + [q for q in pool if q not in front])[:max(1, args.loop)]

    for i, q in enumerate(chosen, 1):
        if args.loop > 1:
            print(f"\n{DIM}── {i} of {len(chosen)} ──{RESET}")
        run_one(q, args.drill == "models", progress)

    if args.loop > 1:
        print(f"\n{DIM}{'─' * 74}{RESET}")
        print("Run  python interview-bank/practice.py --weakest  to see where to go next.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
