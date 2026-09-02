#!/usr/bin/env python3
"""cohort.yaml → schedule page, calendar file, milestones.

One source, three outputs, all regenerable. The schedule page and the .ics are written into the
repository; the milestones are created on GitHub (idempotent, keyed by title) so each week has a
due date the Delivery board can group on.

    python cohort-kit/scripts/cohort_schedule.py --check            # validate only
    python cohort-kit/scripts/cohort_schedule.py                    # write schedule.md + .ics
    python cohort-kit/scripts/cohort_schedule.py --milestones --dry-run
    python cohort-kit/scripts/cohort_schedule.py --milestones

No calendar API exists on GitHub. The .ics file at a raw URL is what a calendar app can
subscribe to; the schedule page is what a person reads; the milestones are what the board reads.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def load(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path} is not a mapping")
    return data


def _date(value) -> dt.date:
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value))


def session_dates(cfg: dict) -> list[dict]:
    """Resolve each session to a date, a start and an end, in the cohort's timezone."""
    c = cfg["cohort"]
    tz = ZoneInfo(c["timezone"])
    start = _date(c["starts"])
    weekday = WEEKDAYS.index(c["weekly"]["day"].lower())
    # First session is the first `weekday` on or after `starts`.
    first = start + dt.timedelta(days=(weekday - start.weekday()) % 7)
    hour, minute = (int(x) for x in str(c["weekly"]["time"]).split(":"))
    out = []
    for s in cfg["sessions"]:
        day = _date(s["date"]) if s.get("date") else first + dt.timedelta(weeks=s["week"] - 1)
        begin = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
        out.append({**s, "date": day, "begin": begin,
                    "end": begin + dt.timedelta(minutes=int(c["weekly"]["minutes"]))})
    return out


def check(cfg: dict, root: Path = ROOT) -> list[str]:
    """Every problem a human would otherwise find on the day."""
    problems = []
    c = cfg.get("cohort", {})
    for key in ("id", "name", "starts", "ends", "timezone", "weekly"):
        if key not in c:
            problems.append(f"cohort.{key} is missing")
    if problems:
        return problems
    try:
        ZoneInfo(c["timezone"])
    except Exception:  # noqa: BLE001
        problems.append(f"cohort.timezone {c['timezone']!r} is not a known zone")
        return problems
    if c["weekly"]["day"].lower() not in WEEKDAYS:
        problems.append(f"cohort.weekly.day {c['weekly']['day']!r} is not a weekday")
        return problems
    sessions = session_dates(cfg)
    weeks = [s["week"] for s in sessions]
    if weeks != sorted(weeks) or len(set(weeks)) != len(weeks):
        problems.append("sessions must have unique, ascending week numbers")
    ends = _date(c["ends"])
    for s in sessions:
        if s["date"] > ends:
            problems.append(f"week {s['week']} falls on {s['date']}, after cohort.ends {ends}")
        for path in s.get("prereads", []):
            if not (root / path).exists():
                problems.append(f"week {s['week']} pre-read does not exist: {path}")
        units = root / "lab-simulator" / "units"
        for uid in s.get("drills", []) + s.get("units", []):
            if units.exists() and not any(p.name.startswith(f"{uid}-") for p in units.iterdir()):
                problems.append(f"week {s['week']} names a simulator id that does not exist: {uid}")
    for p in cfg.get("people", []):
        if p.get("role") not in {"admin", "maintain", "push", "triage", "pull"}:
            problems.append(f"person {p.get('github')!r} has an unknown role {p.get('role')!r}")
    return problems


def render_schedule(cfg: dict) -> str:
    c = cfg["cohort"]
    sessions = session_dates(cfg)
    lines = [f"# {c['name']} · schedule", "",
             f"Sessions on **{c['weekly']['day']}s at {c['weekly']['time']} "
             f"{c['timezone']}**, {c['weekly']['minutes']} minutes. "
             f"Subscribe to the calendar: `calendar/cohort-{c['id']}.ics` (raw URL).", "",
             "Generated from `cohort.yaml` by `cohort-kit/scripts/cohort_schedule.py`. "
             "Edit the YAML, not this page.", "",
             "| Week | Date | Session | Pre-reads | Drills | Units | Exercises |",
             "|---|---|---|---|---|---|---|"]
    for s in sessions:
        pre = ", ".join(f"[{Path(p).stem}](../../{p})" for p in s.get("prereads", [])) or ""
        lines.append(f"| {s['week']} | {s['date'].isoformat()} | {s['title']} | {pre} | "
                     f"{', '.join(f'`{d}`' for d in s.get('drills', []))} | "
                     f"{', '.join(f'`{u}`' for u in s.get('units', []))} | "
                     f"{', '.join(s.get('exercises', []))} |")
    lines += ["", "## Each week, in order", "",
              "1. Read the pre-reads before the session; the Announcements thread links them.",
              "2. Clear the drills in the LAB Simulator category; the bot replies within two "
              "minutes.",
              "3. Post the exercise in Exercises & Submissions: approach first, then the number "
              "with its interval.",
              "4. Owe one peer review before asking for one.",
              "5. Friday: the Standup thread. Moved, blocked, wrong about, numbers.", ""]
    return "\n".join(lines)


def _ics_stamp(when: dt.datetime) -> str:
    return when.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def render_ics(cfg: dict) -> str:
    """A minimal, valid iCalendar file. UTC stamps, so any client renders the right local time."""
    c = cfg["cohort"]
    out = ["BEGIN:VCALENDAR", "VERSION:2.0",
           "PRODID:-//FDE Academy//cohort_schedule.py//EN", "CALSCALE:GREGORIAN",
           f"X-WR-CALNAME:{c['name']}"]
    fixed = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)   # deterministic DTSTAMP
    for s in session_dates(cfg):
        out += ["BEGIN:VEVENT",
                f"UID:cohort-{c['id']}-week-{s['week']}@fde.academy",
                f"DTSTAMP:{_ics_stamp(fixed)}",
                f"DTSTART:{_ics_stamp(s['begin'])}",
                f"DTEND:{_ics_stamp(s['end'])}",
                f"SUMMARY:Week {s['week']} · {s['title']}",
                f"DESCRIPTION:{c['name']} · {c['track']}",
                "END:VEVENT"]
    out.append("END:VCALENDAR")
    return "\r\n".join(out) + "\r\n"


def milestone_specs(cfg: dict) -> list[dict]:
    return [{"title": f"Week {s['week']} · {s['title']}",
             "due_on": s["end"].astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
             "description": f"Cohort {cfg['cohort']['id']} · session on {s['date'].isoformat()}"}
            for s in session_dates(cfg)]


def create_milestones(cfg: dict, dry: bool) -> int:
    from gh import request  # noqa: PLC0415
    owner, repo = cfg["github"]["owner"], cfg["github"]["repo"]
    listing = request("GET", f"/repos/{owner}/{repo}/milestones?state=all&per_page=100")
    existing = {m["title"] for m in listing}
    made = 0
    for spec in milestone_specs(cfg):
        if spec["title"] in existing:
            print(f"  exists  {spec['title']}")
            continue
        if dry:
            print(f"  would create  {spec['title']}  due {spec['due_on']}")
        else:
            request("POST", f"/repos/{owner}/{repo}/milestones", spec)
            print(f"  created  {spec['title']}")
        made += 1
    return made


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "cohort.yaml"))
    ap.add_argument("--check", action="store_true", help="validate and stop")
    ap.add_argument("--milestones", action="store_true", help="create GitHub milestones")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-dir", default=str(ROOT))
    args = ap.parse_args()

    cfg = load(Path(args.config))
    problems = check(cfg)
    if problems:
        print("cohort.yaml has problems:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"cohort.yaml ok: {len(cfg['sessions'])} sessions, {len(cfg.get('people', []))} people")
    if args.check:
        return 0

    out = Path(args.out_dir)
    if args.milestones:
        n = create_milestones(cfg, args.dry_run)
        print(f"{'would create' if args.dry_run else 'created'} {n} milestone(s)")
        return 0

    schedule = out / "docs" / "11-cohort" / "schedule.md"
    ics = out / "calendar" / f"cohort-{cfg['cohort']['id']}.ics"
    for path, text in ((schedule, render_schedule(cfg)), (ics, render_ics(cfg))):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"  wrote {path.relative_to(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
