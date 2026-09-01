"""The command line.

Shaped after what a learner actually asks, in the order they ask it: what should I do now,
what is this, let me start, did it work, where am I.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import progress, report, selftest
from .grader import attempt_dir, grade
from .model import Unit
from .registry import ROOT, all_units, by_id, pathway, unlocked, validate_all

DIM, BOLD, GREEN, YELLOW, RED, CYAN, RESET = (
    "\033[90m", "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[36m", "\033[0m")

DIFF_COLOUR = {"easy": GREEN, "medium": YELLOW, "hard": RED, "brutal": "\033[35m"}
MODE_GLYPH = {"implement": "⌨", "diagnose": "🔍", "decide": "⚖", "measure": "📐", "ship": "📦"}


def _row(u: Unit, done: set[str], ready: set[str]) -> str:
    if u.uid in done:
        status = f"{GREEN}✓ done   {RESET}"
    elif u.uid in ready:
        status = f"{CYAN}○ ready  {RESET}"
    else:
        status = f"{DIM}· locked {RESET}"
    diff = f"{DIFF_COLOUR.get(u.difficulty, '')}{u.difficulty:<7}{RESET}"
    glyph = MODE_GLYPH.get(u.mode, " ")
    return (f"  {status} {BOLD}{u.uid:<5}{RESET} {glyph} {u.title[:46]:<46} "
            f"{diff} {u.track:<12} {u.minutes:>3}m")


def cmd_list(args) -> int:
    done, ready = progress.completed(), {u.uid for u in unlocked(progress.completed())}
    units = [u for u in all_units()
             if (not args.track or u.track == args.track)
             and (not args.difficulty or u.difficulty == args.difficulty)
             and (not args.mode or u.mode == args.mode)]
    if not units:
        print("No units match. Tracks:", ", ".join(sorted({u.track for u in all_units()})))
        return 1
    print(f"\n  {DIM}{'status':<9}{'id':<6}{'':<2}{'title':<47}"
          f"{'difficulty':<8}{'track':<13}{'est':>4}{RESET}")
    for u in units:
        print(_row(u, done, ready))
    print(f"\n  {len(done)} of {len(all_units())} complete\n")
    return 0


def cmd_next(_args) -> int:
    done = progress.completed()
    ready = unlocked(done)
    if not ready:
        print(f"\n  {GREEN}Everything unlocked is done.{RESET}\n")
        return 0
    ready.sort(key=lambda u: (("easy", "medium", "hard", "brutal").index(u.difficulty), u.uid))
    u = ready[0]
    print(f"\n  {BOLD}Next: {u.uid} · {u.title}{RESET}")
    print(f"  {DIM}{u.track} · {u.difficulty} · {u.mode} · ~{u.minutes} min{RESET}\n")
    if u.summary:
        print(f"  {u.summary}\n")
    print(f"  {DIM}labsim brief {u.uid}{RESET}   read it")
    print(f"  {DIM}labsim start {u.uid}{RESET}   scaffold an attempt")
    if len(ready) > 1:
        print(f"\n  {DIM}Also unlocked: {', '.join(x.uid for x in ready[1:6])}{RESET}")
    print()
    return 0


def cmd_brief(args) -> int:
    u = by_id(args.id)
    if not u:
        print(f"No unit {args.id!r}")
        return 1
    print((u.directory / "BRIEF.md").read_text())
    return 0


def cmd_start(args) -> int:
    u = by_id(args.id)
    if not u:
        print(f"No unit {args.id!r}")
        return 1
    done = progress.completed()
    missing = [p for p in u.prereqs if p not in done]
    if missing and not args.force:
        print(f"\n  {YELLOW}{u.uid} is locked.{RESET} Needs: {', '.join(missing)}")
        print(f"  {DIM}Prerequisites are not bureaucracy here — {u.uid} reuses what they "
              f"build.{RESET}")
        print(f"  {DIM}--force to start anyway.{RESET}\n")
        return 1

    dest = attempt_dir(u)
    dest.mkdir(parents=True, exist_ok=True)
    created = []
    for name, target in (("starter.py", "solution.py"),
                         ("decision.template.yaml", "decision.yaml")):
        src = u.directory / name
        if src.exists() and not (dest / target).exists():
            shutil.copy2(src, dest / target)
            created.append(target)
    if not created:
        print(f"\n  {DIM}{dest.relative_to(ROOT)} already exists — pick up where you left "
              f"off.{RESET}\n")
    else:
        print(f"\n  {GREEN}Ready.{RESET} {dest.relative_to(ROOT)}")
        for c in created:
            print(f"    {c}")
        if "decision.yaml" in created:
            print(f"\n  {BOLD}Fill decision.yaml first.{RESET} The grader checks it before it "
                  f"runs a single test,\n  and it checks that your falsifier is an observation "
                  f"rather than the decision restated.")
        print(f"\n  {DIM}labsim check {u.uid}{RESET}\n")
    return 0


def cmd_check(args) -> int:
    u = by_id(args.id)
    if not u:
        print(f"No unit {args.id!r}")
        return 1
    print(f"\n  {BOLD}{u.uid} · {u.title}{RESET}  {DIM}{u.mode}{RESET}\n")
    result = grade(u)
    for m in result.messages:
        print(f"    {m}")
    if result.decision_ok is not None:
        mark = f"{GREEN}✓{RESET}" if result.decision_ok else f"{RED}✗{RESET}"
        print(f"\n    {mark} decision")
    if result.checks_ok is not None:
        mark = f"{GREEN}✓{RESET}" if result.checks_ok else f"{RED}✗{RESET}"
        print(f"    {mark} checks")
    for desc, ok, value in result.bars:
        mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        shown = f"{value:.4f}" if value is not None else "not reported"
        print(f"    {mark} {desc}  {DIM}(got {shown}){RESET}")

    progress.record(u.uid, result.passed, result.duration)
    if result.passed:
        print(f"\n  {GREEN}{BOLD}Passed.{RESET}  {DIM}{result.duration:.1f}s{RESET}")
        sol = u.directory / "SOLUTION.md"
        if sol.exists():
            print(f"  {DIM}How we did it: {sol.relative_to(ROOT)}{RESET}")
        newly = [x.uid for x in unlocked(progress.completed())]
        if newly:
            print(f"  {DIM}Now available: {chr(44).join(newly[:6])}{RESET}")
    else:
        print(f"\n  {RED}Not yet.{RESET}")
    print()
    if args.json:
        print(json.dumps(result.as_dict(), indent=2))
    return 0 if result.passed else 1


def cmd_progress(_args) -> int:
    data = progress.load()["units"]
    waves = pathway()
    done = progress.completed()
    print(f"\n  {BOLD}Pathway{RESET}\n")
    for i, wave in enumerate(waves, 1):
        got = sum(1 for u in wave if u.uid in done)
        bar = "█" * got + "░" * (len(wave) - got)
        print(f"  {DIM}wave {i}{RESET}  {bar}  {got}/{len(wave)}   "
              f"{DIM}{', '.join(u.uid for u in wave)}{RESET}")
    attempted = [(uid, e) for uid, e in data.items() if e["attempts"] > 1 and not e["passed"]]
    if attempted:
        print(f"\n  {YELLOW}Open, more than one attempt:{RESET}")
        for uid, e in sorted(attempted):
            print(f"    {uid}  {e['attempts']} attempts")
    print(f"\n  {len(done)} of {len(all_units())} complete\n")
    return 0


def cmd_validate(_args) -> int:
    problems = validate_all()
    if not problems:
        print(f"{GREEN}{len(all_units())} units, no structural problems.{RESET}")
        return 0
    for uid, issues in sorted(problems.items()):
        print(f"{RED}{uid}{RESET}")
        for i in issues:
            print(f"  {i}")
    return 1


def cmd_selftest(args) -> int:
    """Prove the graders still discriminate. This is CI's job, and yours before a PR."""
    units = report.resolve(args.id) if args.id else list(all_units())
    outcomes, gaps = selftest.run_all(units)
    print()
    print(selftest.format_report(outcomes, gaps))
    broken = [o for o in outcomes if not o.ok]
    print()
    if gaps or broken:
        print(f"  {RED}{len(broken)} case(s) misbehaving, "
              f"{sum(len(v) for v in gaps.values())} gap(s).{RESET}\n")
        return 1
    print(f"  {GREEN}{len(outcomes)} reference case(s) behaved as claimed.{RESET}\n")
    return 0


def cmd_ci(args) -> int:
    """Grade whatever a pull request touched, and write the comment body to a file.

    Kept in the CLI rather than in the workflow so the exact thing CI does can be run locally:

        git diff --name-only origin/main... | python -m labsim ci --paths -
    """
    paths = report.read_paths(args.paths)
    body, ok = report.attempt_report(paths)
    if not body:
        print("no attempts changed")
        if args.out:
            Path(args.out).write_text("")
        return 0
    if args.out:
        Path(args.out).write_text(body)
    print(body)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="labsim", description=__doc__)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("list", help="every unit and its status")
    p.add_argument("--track")
    p.add_argument("--difficulty")
    p.add_argument("--mode")
    p.set_defaults(fn=cmd_list)

    sub.add_parser("next", help="what to do now").set_defaults(fn=cmd_next)

    p = sub.add_parser("brief", help="read a unit's brief")
    p.add_argument("id")
    p.set_defaults(fn=cmd_brief)

    p = sub.add_parser("start", help="scaffold an attempt")
    p.add_argument("id")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_start)

    p = sub.add_parser("check", help="grade an attempt")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_check)

    sub.add_parser("progress", help="where you are").set_defaults(fn=cmd_progress)
    sub.add_parser("validate", help="check the units themselves").set_defaults(fn=cmd_validate)

    p = sub.add_parser("selftest", help="grade the graders against their reference answers")
    p.add_argument("id", nargs="*")
    p.set_defaults(fn=cmd_selftest)

    p = sub.add_parser("ci", help="grade the attempts a diff touched")
    p.add_argument("--paths", default="-", help="file of changed paths, or - for stdin")
    p.add_argument("--out", help="write the pull-request comment body here")
    p.set_defaults(fn=cmd_ci)

    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        return cmd_next(args)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
