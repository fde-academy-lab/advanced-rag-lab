#!/usr/bin/env python3
"""Q&A threads nobody has answered, kept in one instructor-facing tracking issue.

    python cohort-kit/scripts/unanswered_questions.py --owner O --repo R --hours 24 \
        --config cohort.yaml

"Answered" means: an answer is marked, or a person with the maintain or admin role in
cohort.yaml has commented. A learner's reply does not clear it; a peer answer that the asker
has not marked is still open from the instructor's point of view, and marking it is the
instructor's job when the asker forgets.

The pure parts (`overdue`, `render`) are tested; the GraphQL harvest shares its shape with
scripts/discussions_pulse.py.
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

ISSUE_TITLE = "Unanswered questions"
MARK = "<!-- cohort-kit:unanswered:v1 -->"
BOT_LOGINS = {"github-actions", "github-actions[bot]"}

Q = """
query($owner:String!,$name:String!,$cursor:String){
  repository(owner:$owner,name:$name){
    discussions(first:50, after:$cursor, orderBy:{field:CREATED_AT,direction:DESC}){
      pageInfo{ hasNextPage endCursor }
      nodes{
        number title url createdAt isAnswered
        category{ name isAnswerable }
        author{ login }
        comments(last:30){ nodes{ createdAt author{ login } } }
      }
    }
  }
}"""


@dataclass
class Question:
    number: int
    title: str
    url: str
    author: str
    created: datetime
    answered: bool
    category: str
    commenters: list[tuple[str, datetime]] = field(default_factory=list)


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def instructors(cfg: dict) -> set[str]:
    return {p["github"].lower() for p in cfg.get("people", [])
            if p.get("role") in {"maintain", "admin"}}


def overdue(questions: list[Question], staff: set[str], now: datetime,
            hours: int = 24) -> list[Question]:
    """The ones to list: answerable, not answered, older than `hours`, no staff comment since
    the question was asked."""
    cutoff = now - timedelta(hours=hours)
    out = []
    for q in questions:
        if q.answered or q.created > cutoff:
            continue
        if any(login.lower() in staff for login, _ in q.commenters):
            continue
        out.append(q)
    return sorted(out, key=lambda q: q.created)


def harvest(owner: str, repo: str, category_names: set[str] | None = None) -> list[Question]:
    from gh import graphql  # noqa: PLC0415
    out, cursor = [], None
    while True:
        data = graphql(Q, {"owner": owner, "name": repo, "cursor": cursor})
        page = data["repository"]["discussions"]
        for d in page["nodes"]:
            cat = d["category"]
            if not cat["isAnswerable"]:
                continue
            if category_names and cat["name"] not in category_names:
                continue
            out.append(Question(
                number=d["number"], title=d["title"], url=d["url"],
                author=(d.get("author") or {}).get("login", ""), created=_ts(d["createdAt"]),
                answered=bool(d["isAnswered"]), category=cat["name"],
                commenters=[((c.get("author") or {}).get("login", ""), _ts(c["createdAt"]))
                            for c in d["comments"]["nodes"]
                            if (c.get("author") or {}).get("login", "") not in BOT_LOGINS]))
        if not page["pageInfo"]["hasNextPage"]:
            return out
        cursor = page["pageInfo"]["endCursor"]


def render(items: list[Question], now: datetime, hours: int) -> str:
    head = [MARK, f"Questions with no marked answer and no instructor reply for {hours}h, "
            f"oldest first. Updated {now.strftime('%Y-%m-%d %H:%M UTC')} by "
            "`unanswered-questions.yml`.", ""]
    if not items:
        return "\n".join(head + ["Nothing is waiting. That is the whole report.", ""])
    rows = ["| Waiting | Category | Thread | Asked by |", "|---|---|---|---|"]
    for q in items:
        days = (now - q.created).total_seconds() / 86400
        rows.append(f"| {days:.1f}d | {q.category} | [{q.title}]({q.url}) | @{q.author} |")
    tail = ["", "Answer in the thread and **mark the answer**; the row disappears on the next "
            "run. A peer answer the asker has not marked still counts as open: mark it for "
            "them.", ""]
    return "\n".join(head + rows + tail)


def upsert_issue(owner: str, repo: str, body: str, assignees: list[str], dry: bool) -> str:
    from gh import request  # noqa: PLC0415
    existing = [i for i in request("GET", f"/repos/{owner}/{repo}/issues?state=open&per_page=100")
                if i["title"] == ISSUE_TITLE and "pull_request" not in i]
    payload = {"title": ISSUE_TITLE, "body": body, "assignees": assignees, "labels": ["cohort"]}
    if dry:
        what = f"update #{existing[0]['number']}" if existing else "create"
        return f"would {what} the tracking issue"
    if existing:
        request("PATCH", f"/repos/{owner}/{repo}/issues/{existing[0]['number']}", payload)
        return f"updated #{existing[0]['number']}"
    made = request("POST", f"/repos/{owner}/{repo}/issues", payload)
    return f"created #{made['number']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--config", default="cohort.yaml")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text()) if Path(args.config).exists() else {}
    staff = instructors(cfg)
    now = datetime.now(timezone.utc)
    items = overdue(harvest(args.owner, args.repo), staff, now, args.hours)
    body = render(items, now, args.hours)
    print(body)
    assignees = sorted(p["github"] for p in cfg.get("people", []) if p.get("role") == "maintain")
    print(upsert_issue(args.owner, args.repo, body, assignees, args.dry_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
