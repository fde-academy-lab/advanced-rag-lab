"""The command line.

Shaped after what a learner actually asks, in the order they ask it: what should I do now,
what is this, let me start, did it work, where am I.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import brief as briefmod
from . import discussion, progress, report, selftest
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
    text = (u.directory / "BRIEF.md").read_text()
    if args.raw or not sys.stdout.isatty():
        print(text)
        return 0
    print(briefmod.render(text))
    print(f"\n  {DIM}labsim hint {u.uid}{RESET}    spend one when you are stuck")
    print(f"  {DIM}labsim start {u.uid}{RESET}   scaffold an attempt\n")
    return 0


def cmd_hint(args) -> int:
    """Hints, one at a time. Collapsed on GitHub, spent deliberately here."""
    u = by_id(args.id)
    if not u:
        print(f"No unit {args.id!r}")
        return 1
    items = briefmod.hints((u.directory / "BRIEF.md").read_text())
    if not items:
        print(f"\n  {u.uid} ships no hints — for a unit this size the brief is the hint.\n")
        return 0
    n = args.n or 1
    if n > len(items):
        print(f"\n  {YELLOW}{u.uid} has {len(items)} hints and you asked for {n}.{RESET}")
        print(f"  {DIM}The last one is spent. Run the checks and let them name the promise "
              f"your code breaks.{RESET}\n")
        return 1
    h = items[n - 1]
    print(f"\n  {DIM}{u.uid} · hint {n} of {len(items)}{RESET}\n")
    print(briefmod.render(f"**{h.summary}**\n\n{h.body}"))
    if n < len(items):
        print(f"\n  {DIM}labsim hint {u.uid} {n + 1}{RESET}   the next one\n")
    else:
        print(f"\n  {DIM}That was the last hint.{RESET}\n")
    return 0


def cmd_doctor(_args) -> int:
    """Is this machine able to run the lab? Answered before somebody blames their code."""
    import importlib.util
    import platform
    checks: list[tuple[str, bool, str]] = []
    v = sys.version_info
    checks.append(("python >= 3.10", v >= (3, 10), f"{v.major}.{v.minor}.{v.micro}"))
    # `raglab` lives one directory up. A unit's check.py puts the repository root on sys.path
    # before importing it, so the honest question is whether it resolves under that path — not
    # whether it happens to be installed into site-packages.
    root_on_path = str(ROOT.parent)
    added = root_on_path not in sys.path
    if added:
        sys.path.insert(0, root_on_path)
    try:
        for mod, why in (("yaml", "reading unit.yaml"), ("numpy", "the retrieval stack"),
                         ("raglab", "units graded on the real corpus"),
                         ("pytest", "the engine tests")):
            checks.append((f"import {mod}", importlib.util.find_spec(mod) is not None, why))
    finally:
        if added:
            sys.path.remove(root_on_path)
    checks.append(("units load", bool(all_units()), f"{len(all_units())} found"))
    problems = validate_all()
    checks.append(("units are structurally sound", not problems,
                   "; ".join(problems) if problems else "validate is clean"))
    checks.append(("attempts/ is writable", _writable(), str(ROOT / "attempts")))
    checks.append(("`code` on PATH (for --open)", bool(shutil.which("code")),
                   "optional — Codespaces and VS Code only"))

    print(f"\n  {BOLD}labsim doctor{RESET}  {DIM}{platform.platform()}{RESET}\n")
    hard_fail = False
    for name, good, detail in checks:
        mark = f"{GREEN}✓{RESET}" if good else f"{RED}✗{RESET}"
        print(f"    {mark} {name:<34} {DIM}{detail}{RESET}")
        if not good and "optional" not in detail:
            hard_fail = True
    if hard_fail:
        print(f"\n  {YELLOW}Fix:{RESET} pip install -e \".[dev]\" from the repository root\n")
        return 1
    print(f"\n  {GREEN}Ready.{RESET} {DIM}labsim next{RESET}\n")
    return 0


def _writable() -> bool:
    try:
        d = ROOT / "attempts"
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".labsim-write-probe"
        probe.write_text("")
        probe.unlink()
        return True
    except OSError:
        return False


def cmd_badge(_args) -> int:
    """A line for a CV, generated from what you actually cleared rather than what you claim."""
    done = progress.completed()
    units = all_units()
    by_track: dict[str, tuple[int, int]] = {}
    for u in units:
        got, total = by_track.get(u.track, (0, 0))
        by_track[u.track] = (got + (u.uid in done), total + 1)
    modes = sorted({u.mode for u in units if u.uid in done})
    print(f"\n  {BOLD}{len(done)} of {len(units)} units{RESET}\n")
    for track, (got, total) in sorted(by_track.items()):
        bar = "█" * got + "░" * (total - got)
        print(f"    {track:<13} {bar}  {got}/{total}")
    if not done:
        print(f"\n  {DIM}Nothing cleared yet — there is nothing to claim, which is the "
              f"point.{RESET}\n")
        return 0
    print(f"\n  {DIM}Paste-able:{RESET}\n")
    print(f"    L.A.B. Simulator — {len(done)}/{len(units)} units cleared "
          f"({', '.join(modes)}), graded against a live retrieval corpus.")
    print()
    return 0


def cmd_discuss(args) -> int:
    """What the Discussions bot runs. Kept here so the workflow file holds no logic."""
    import json
    event = json.loads(Path(args.event).read_text())
    disc = event.get("discussion") or {}
    comment = (event.get("comment") or {}).get("body")
    title, body = disc.get("title", ""), disc.get("body", "") or ""

    sub = discussion.parse_submission(title, body)
    action, reply, passed = "none", "", False

    def graded():
        u = by_id(sub.unit_id or "")
        if u is None or not sub.usable:
            return None, None
        discussion.materialise(sub)
        return u, grade(u)

    if comment:
        cmd = discussion.parse_command(comment)
        if cmd is None:
            # Write BOTH files before returning. The workflow's collect step runs
            # `cp "$RUNNER_TEMP/meta.json" out/meta.json` under `set -euo pipefail`, so a
            # missing meta.json fails the grade job — on every ordinary peer comment, which is
            # the interaction this whole feature exists to encourage. The respond job already
            # handles an empty reply.md (`[ -s out/reply.md ] || exit 0`); it has no way to
            # handle a file that is not there.
            print("no command in the comment; nothing to do")
            Path(args.out).write_text("")
            Path(args.meta).write_text(json.dumps(
                {"action": "none", "unit": sub.unit_id, "passed": False,
                 "discussion_node_id": disc.get("node_id"),
                 "number": disc.get("number")}, indent=2))
            return 0
        name, n = cmd
        action = name
        if name == "help":
            reply = discussion.render_help(args.repo)
        elif name == "status":
            reply = discussion.render_status(sub.unit_id)
        elif name == "hint":
            reply = discussion.render_hint(sub.unit_id or "", n)
        elif name == "solution":
            u, result = graded()
            passed = bool(result and result.passed)
            reply = discussion.render_solution(sub.unit_id or "", passed=passed)
        elif name == "check":
            u, result = graded()
            if result is None:
                reply = _cannot_grade(sub)
            else:
                passed = result.passed
                reply = discussion.render_grade(u.uid, result, repo=args.repo)
    else:
        action = "grade"
        u, result = graded()
        if result is None:
            reply = _cannot_grade(sub)
        else:
            passed = result.passed
            reply = discussion.render_grade(u.uid, result, repo=args.repo)

    Path(args.out).write_text(reply)
    Path(args.meta).write_text(json.dumps(
        {"action": action, "unit": sub.unit_id, "passed": passed,
         "discussion_node_id": disc.get("node_id"), "number": disc.get("number")}, indent=2))
    print(f"action={action} unit={sub.unit_id} passed={passed} reply={len(reply)} bytes")
    return 0


def _cannot_grade(sub) -> str:
    known = ", ".join(f"`{u.uid}`" for u in all_units())
    if not sub.unit_id:
        return (f"{discussion.MARKER}\n\nI could not tell which unit this is for. Put the id in "
                f"the title — `R1 · my attempt` — or use the category form.\n\nUnits: {known}")
    return (f"{discussion.MARKER}\n\nFound `{sub.unit_id}` but no code to grade. Paste your "
            "file inside a fenced block:\n\n````\n```python\ndef pack_context(hits):\n    "
            "...\n```\n````\n\nEdit the post and I re-grade automatically.")


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
    # `starter.py` becomes `solution.py`; anything named `<name>.template.<ext>` becomes
    # `<name>.<ext>`. The convention rather than a list, so a unit that needs a new kind of
    # artefact ships one file and needs no change here.
    scaffolds = [(u.directory / "starter.py", "solution.py")]
    scaffolds += [(src, src.name.replace(".template", ""))
                  for src in sorted(u.directory.glob("*.template.*"))]
    for src, target in scaffolds:
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
    if args.open:
        _open_in_editor(u, dest)
    return 0


def _open_in_editor(u: Unit, dest) -> None:
    """Brief on one side, your attempt on the other — the layout the work actually wants.

    `code` exists in Codespaces and in any VS Code with shell commands installed, and nowhere
    else. Missing it is not an error: the terminal is a perfectly good problem pane, which is
    why `labsim brief` renders rather than cats.
    """
    exe = shutil.which("code") or shutil.which("code-insiders")
    if not exe:
        print(f"  {DIM}--open needs the `code` command (Codespaces has it). "
              f"Meanwhile: labsim brief {u.uid}{RESET}\n")
        return
    targets = [u.directory / "BRIEF.md"]
    targets += [dest / n for n in ("decision.yaml", "solution.py", "measurement.md")
                if (dest / n).exists()]
    subprocess.run([exe, "--reuse-window", *[str(t) for t in targets]], check=False)
    print(f"  {DIM}Opened {len(targets)} files. ⌘K V (Ctrl+K V) renders the brief beside "
          f"your code.{RESET}\n")


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
    p.add_argument("--raw", action="store_true", help="the markdown source, unrendered")
    p.set_defaults(fn=cmd_brief)

    p = sub.add_parser("hint", help="spend one hint")
    p.add_argument("id")
    p.add_argument("n", nargs="?", type=int)
    p.set_defaults(fn=cmd_hint)

    sub.add_parser("doctor", help="can this machine run the lab?").set_defaults(fn=cmd_doctor)
    sub.add_parser("badge", help="what you have cleared, in a form you can paste"
                   ).set_defaults(fn=cmd_badge)

    p = sub.add_parser("discuss", help="grade a discussion event (used by the bot)")
    p.add_argument("--event", required=True, help="path to the GitHub event payload")
    p.add_argument("--out", default="reply.md")
    p.add_argument("--meta", default="meta.json")
    p.add_argument("--repo", default="")
    p.set_defaults(fn=cmd_discuss)

    p = sub.add_parser("start", help="scaffold an attempt")
    p.add_argument("id")
    p.add_argument("--force", action="store_true")
    p.add_argument("--open", action="store_true",
                   help="open the brief and your attempt in the editor (Codespaces / VS Code)")
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
