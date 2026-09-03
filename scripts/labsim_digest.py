#!/usr/bin/env python3
"""What the simulator learned this week, from its own grading history.

The bot leaves a machine-readable tag on every reply — `<!-- labsim:R1:fail:check;check -->` —
and this reads them back. The output is deliberately **not** a leaderboard.

A leaderboard measures learners, which on a public repository mostly measures who had a free
weekend. The histogram of *which check fails most often* measures the units, and that is a
number with a decision attached: a check almost everyone trips is either the lesson working, or
a brief that failed to set it up, and the two are distinguishable by whether people clear it on
the second attempt.

Nothing here needs a PAT. `discussions: read` on the built-in token is enough.

    python scripts/labsim_digest.py --owner X --repo Y --days 7 --out digest.md
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lab-simulator"))
from gh import graphql  # noqa: E402

TAG = re.compile(r"<!--\s*labsim:([A-Z]{1,2}\d{1,2}):(pass|fail|hint|no-result):?(.*?)-->", re.S)

Q = """
query($owner:String!,$name:String!,$cursor:String){
  repository(owner:$owner,name:$name){
    discussions(first:50, after:$cursor, orderBy:{field:UPDATED_AT,direction:DESC}){
      pageInfo{ hasNextPage endCursor }
      nodes{
        number title url updatedAt
        category{ name }
        comments(last:50){ nodes{ body createdAt updatedAt author{ login } } }
      }
    }
  }
}"""


def simulator_category(name: str) -> bool:
    return re.sub(r"[^a-z]", "", (name or "").lower()) in {
        "labsimulator", "labsimulatorexercises", "exercisessubmissions"}


def harvest(owner: str, repo: str, since: datetime) -> list[dict]:
    events, cursor = [], None
    while True:
        data = graphql(Q, {"owner": owner, "name": repo, "cursor": cursor})
        page = data["repository"]["discussions"]
        for d in page["nodes"]:
            if not simulator_category(d["category"]["name"]):
                continue
            for c in d["comments"]["nodes"]:
                # `updatedAt`, because the bot edits its verdict comment in place rather
                # than appending. Filtering on creation time makes every re-grade on a thread
                # older than the window invisible — which is exactly the activity a weekly
                # digest exists to see.
                stamp = c.get("updatedAt") or c["createdAt"]
                when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                if when < since:
                    continue
                for uid, kind, payload in TAG.findall(c["body"] or ""):
                    events.append({"unit": uid, "kind": kind, "when": when,
                                   "checks": [x.strip() for x in payload.split(";") if x.strip()],
                                   "thread": d["number"], "title": d["title"], "url": d["url"]})
        if not page["pageInfo"]["hasNextPage"]:
            return events
        cursor = page["pageInfo"]["endCursor"]


def render(events: list[dict], days: int) -> str:
    if not events:
        return ("## L.A.B. Simulator · weekly digest\n\nNo graded activity in the last "
                f"{days} days.\n\nThat is a fact about the week, not a problem to fix. The "
                "digest exists to make the histogram visible when there *is* one.\n")

    grades = [e for e in events if e["kind"] in ("pass", "fail")]
    passes = [e for e in grades if e["kind"] == "pass"]
    per_unit = collections.Counter(e["unit"] for e in grades)
    cleared = collections.Counter(e["unit"] for e in passes)
    checks = collections.Counter(c for e in grades if e["kind"] == "fail" for c in e["checks"])
    hints = collections.Counter(e["unit"] for e in events if e["kind"] == "hint")

    lines = ["## L.A.B. Simulator · weekly digest", "",
             f"{len(grades)} graded submission{'s' if len(grades) != 1 else ''} across "
             f"{len(per_unit)} unit{'s' if len(per_unit) != 1 else ''} in the last {days} days, "
             f"{len(passes)} of them clearing.", "",
             "### Where people are", "",
             "| unit | graded | cleared | hints spent |", "|---|---|---|---|"]
    for unit, n in per_unit.most_common():
        lines.append(f"| `{unit}` | {n} | {cleared[unit]} | {hints[unit]} |")

    lines += ["", "### The checks that caught people", "",
              "This is the useful half, and it is feedback on the **units** rather than on "
              "anybody working them.", "",
              "| times | check |", "|---|---|"]
    for name, n in checks.most_common(10):
        lines.append(f"| {n} | `{name}` |")

    if checks:
        top, n = checks.most_common(1)[0]
        share = n / max(len([e for e in grades if e['kind'] == 'fail']), 1)
        lines += ["", f"`{top}` accounted for {share:.0%} of failed submissions. Two readings, "
                  "and they need different responses: the check is the lesson landing, or the "
                  "brief failed to set it up. They are distinguishable — if people clear it on "
                  "the second attempt it is the lesson, and if they clear it only after "
                  "spending a hint the brief is doing too little work."]

    lines += ["", "<sub>Generated by `scripts/labsim_digest.py` from the grading bot's own "
              "replies. Deliberately not a leaderboard: ranking learners on a public "
              "repository mostly ranks who had a free weekend.</sub>"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", default="digest.md")
    args = ap.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    events = harvest(args.owner, args.repo, since)
    text = render(events, args.days)
    Path(args.out).write_text(text)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
