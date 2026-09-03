#!/usr/bin/env python3
"""What is happening in Discussions this week — as a board rather than a feeling.

Discussions cannot be added to a Projects v2 board; only issues, pull requests and draft items
can. So this mirrors each thread that had activity in the window as a **draft item**, keyed by
number, with the fields a facilitator actually scans: category, how many comments landed this
week, whether anybody answered, when it last moved, and a heat score. Threads that went quiet
drop out of the window but stay on the board with their last numbers, so a facilitator can see
what *stopped* being discussed as well as what started.

It also writes one item per week summarising what changed in the repository's content —
docs, notebooks, units — from the git log, so "new content added" is visible on the same
board as "what people are talking about".

    python scripts/discussions_pulse.py --owner X --repo Y --days 7          # print
    python scripts/discussions_pulse.py --owner X --repo Y --days 7 --board  # upsert (PAT)
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import GitHubError, graphql, is_rate_limit, rate_limit_reset  # noqa: E402

Q = """
query($owner:String!,$name:String!,$cursor:String){
  repository(owner:$owner,name:$name){
    discussions(first:50, after:$cursor, orderBy:{field:UPDATED_AT,direction:DESC}){
      pageInfo{ hasNextPage endCursor }
      nodes{
        number title url createdAt updatedAt isAnswered
        author{ login }
        category{ name isAnswerable }
        labels(first:10){ nodes{ name } }
        reactions{ totalCount }
        comments(last:100){ totalCount nodes{ createdAt updatedAt author{ login }
                                              reactions{ totalCount } } }
      }
    }
  }
}"""

BOT_LOGINS = {"github-actions", "github-actions[bot]"}


@dataclass
class Thread:
    number: int
    title: str
    url: str
    category: str
    answerable: bool
    answered: bool
    author: str
    labels: list[str]
    comments_total: int
    comments_window: int
    humans_window: int         # distinct human commenters in the window
    reactions: int
    last_activity: datetime
    created: datetime

    @property
    def needs_answer(self) -> bool:
        return self.answerable and not self.answered

    @property
    def heat(self) -> int:
        """Comments in the window count most; distinct humans and reactions break ties."""
        return self.comments_window * 3 + self.humans_window * 2 + self.reactions


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def harvest(owner: str, repo: str, since: datetime) -> list[Thread]:
    out, cursor = [], None
    while True:
        page = graphql(Q, {"owner": owner, "name": repo,
                           "cursor": cursor})["repository"]["discussions"]
        for d in page["nodes"]:
            nodes = d["comments"]["nodes"]
            in_window = [c for c in nodes if _ts(c.get("updatedAt") or c["createdAt"]) >= since]
            humans = {(c.get("author") or {}).get("login") for c in in_window
                      if (c.get("author") or {}).get("login") not in BOT_LOGINS}
            last = max([_ts(d["updatedAt"])] + [_ts(c["createdAt"]) for c in nodes])
            out.append(Thread(
                number=d["number"], title=d["title"], url=d["url"],
                category=d["category"]["name"], answerable=d["category"]["isAnswerable"],
                answered=bool(d.get("isAnswered")),
                author=(d.get("author") or {}).get("login") or "ghost",
                labels=[n["name"] for n in d["labels"]["nodes"]],
                comments_total=d["comments"]["totalCount"], comments_window=len(in_window),
                humans_window=len(humans - {None}),
                reactions=d["reactions"]["totalCount"]
                + sum(c["reactions"]["totalCount"] for c in in_window),
                last_activity=last, created=_ts(d["createdAt"])))
        if not page["pageInfo"]["hasNextPage"]:
            return out
        cursor = page["pageInfo"]["endCursor"]


def active(threads: list[Thread], since: datetime) -> list[Thread]:
    """Threads that moved in the window, hottest first."""
    live = [t for t in threads if t.last_activity >= since or t.comments_window]
    return sorted(live, key=lambda t: (-t.heat, -t.last_activity.timestamp()))


def content_changes(root: Path, days: int) -> dict[str, list[str]]:
    """Files under the teaching surfaces that changed in the window, grouped by area."""
    try:
        out = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--name-status", "--pretty=format:",
             "--", "docs", "notebooks", "lab-simulator/units", "concepts-and-case-studies",
             "interview-bank"],
            cwd=root, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    groups: dict[str, set[str]] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0][0], parts[-1]
        area = path.split("/")[0] if "/" in path else path
        if path.startswith("lab-simulator/units/"):
            area = "lab-simulator/units"
        groups.setdefault(area, set()).add(f"{'+' if status == 'A' else '~'} {path}")
    return {k: sorted(v) for k, v in sorted(groups.items())}


# ─────────────────────────────────────────────────────────────── rendering ──
def render(threads: list[Thread], changes: dict[str, list[str]], days: int) -> str:
    lines = [f"## Discussions · pulse, last {days} days", ""]
    if not threads:
        lines.append("Nothing moved. That is a fact about the week.")
    else:
        lines += ["| heat | thread | category | comments (window / total) | people | state |",
                  "|---|---|---|---|---|---|"]
        for t in threads[:25]:
            state = ("**needs an answer**" if t.needs_answer else
                     "answered" if t.answerable else "open")
            lines.append(f"| {t.heat} | [#{t.number} {t.title[:60]}]({t.url}) | {t.category} "
                         f"| {t.comments_window} / {t.comments_total} | {t.humans_window} | "
                         f"{state} |")
        unanswered = [t for t in threads if t.needs_answer]
        if unanswered:
            lines += ["", f"**{len(unanswered)} answerable thread(s) with no accepted answer.** "
                          "Those are the queue."]
    if changes:
        lines += ["", "### Content that changed", ""]
        for area, files in changes.items():
            lines.append(f"- **{area}** — {len(files)} file(s)")
            for f in files[:8]:
                lines.append(f"  - `{f}`")
            if len(files) > 8:
                lines.append(f"  - … and {len(files) - 8} more")
    lines += ["", "<sub>`scripts/discussions_pulse.py`. Heat = comments in window ×3 + distinct "
                  "people ×2 + reactions. Not a ranking of people; a ranking of *threads*, which "
                  "is what a facilitator triages.</sub>"]
    return "\n".join(lines) + "\n"


# ────────────────────────────────────────────────────────────────── board ──
BOARD_TITLE = "Discussions — Pulse"
# The first live run was refused on createProjectV2Field with "Name cannot have a reserved
# value". GitHub does not publish the reserved list and the docs were unreachable from the
# session that fixed this, so the three single-word names that could plausibly collide with a
# built-in were renamed rather than guessed at one by one. A refused field is now a warning.
BOARD_FIELDS = {
    "Thread category": ("TEXT", None),
    "Heat": ("NUMBER", None),
    "Comments (window)": ("NUMBER", None),
    "Comments (total)": ("NUMBER", None),
    "People (window)": ("NUMBER", None),
    "Last activity": ("DATE", None),
    "Attention": ("SINGLE_SELECT", ["Needs an answer", "Answered", "Open", "Content change"]),
    "Opened by": ("TEXT", None),
}

from labsim_progress import (  # noqa: E402  (shared board plumbing)
    ADD_DRAFT_M,
    CREATE_FIELD_M,
    CREATE_PROJECT_M,
    CREATE_SELECT_M,
    FIELDS_Q,
    OWNER_Q,
    SET_M,
    _value,
)


def ensure_board(owner: str, dry: bool):
    data = graphql(OWNER_Q, {"login": owner})["repositoryOwner"]
    existing = next((p for p in data["projectsV2"]["nodes"] if p["title"] == BOARD_TITLE), None)
    if existing is None:
        if dry:
            print(f"would create board {BOARD_TITLE!r}")
            return None, {}
        existing = graphql(CREATE_PROJECT_M, {"ownerId": data["id"],
                                              "title": BOARD_TITLE})["createProjectV2"]["projectV2"]
        print("created board", existing["url"])
    pid = existing["id"]
    fields = {f["name"]: f for f in graphql(FIELDS_Q, {"id": pid})["node"]["fields"]["nodes"] if f}
    for name, (dtype, options) in BOARD_FIELDS.items():
        if name in fields:
            continue
        if dry:
            print(f"would create field {name}")
            continue
        try:
            if dtype == "SINGLE_SELECT":
                opts = [{"name": o, "description": "", "color": "GRAY"} for o in options]
                graphql(CREATE_SELECT_M, {"projectId": pid, "name": name, "options": opts})
            else:
                graphql(CREATE_FIELD_M, {"projectId": pid, "name": name, "type": dtype})
            print("created field", name)
        except GitHubError as exc:
            # One refused field used to abort the whole sync, after the board had already
            # been created: an empty board and a red run. The upsert skips values for fields
            # that do not exist, so the rest of the board still fills in.
            print(f"::warning::field {name!r} was refused and is skipped: {exc.message[:140]}")
    node = graphql(FIELDS_Q, {"id": pid})["node"]
    fields = {f["name"]: f for f in node["fields"]["nodes"] if f}
    items = {i["content"]["title"]: i["id"] for i in node["items"]["nodes"] if i.get("content")}
    return pid, (fields, items)


def _upsert(pid, fields, items, title, body, values, dry) -> None:
    if dry:
        print(f"would upsert {title[:60]!r}: {values}")
        return
    item_id = items.get(title)
    if item_id is None:
        made = graphql(ADD_DRAFT_M, {"projectId": pid, "title": title, "body": body})
        item_id = made["addProjectV2DraftIssue"]["projectItem"]["id"]
    for name, raw in values.items():
        if raw is None or name not in fields:
            continue
        val = _value(fields[name], raw)
        if val is None:
            continue
        try:
            graphql(SET_M, {"projectId": pid, "itemId": item_id,
                            "fieldId": fields[name]["id"], "value": val})
        except GitHubError as exc:
            print(f"  {title[:40]} {name}: {exc.message[:70]}")


def sync_board(owner, threads, changes, since, dry) -> int:
    pid, extra = ensure_board(owner, dry)
    if pid is None:
        return 0
    fields, items = extra
    n = 0
    for t in threads:
        title = f"#{t.number} · {t.title}"[:250]
        state = ("Needs an answer" if t.needs_answer else "Answered" if t.answerable else "Open")
        _upsert(pid, fields, items, title, t.url,
                {"Thread category": t.category, "Heat": t.heat,
                 "Comments (window)": t.comments_window,
                 "Comments (total)": t.comments_total, "People (window)": t.humans_window,
                 "Last activity": t.last_activity.date().isoformat(), "Attention": state,
                 "Opened by": t.author}, dry)
        n += 1
    if changes:
        week = since.strftime("%Y-%m-%d")
        body = "\n".join(f"**{area}**\n" + "\n".join(f"- `{f}`" for f in files)
                         for area, files in changes.items())
        _upsert(pid, fields, items, f"Content changed · week of {week}", body,
                {"Thread category": "repository", "Heat": sum(len(v) for v in changes.values()),
                 "Last activity": datetime.now(timezone.utc).date().isoformat(),
                 "Attention": "Content change"}, dry)
        n += 1
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--board", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", help="write the rendered pulse here as well")
    args = ap.parse_args()

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    threads = active(harvest(args.owner, args.repo, since), since)
    changes = content_changes(Path(__file__).resolve().parents[1], args.days)
    text = render(threads, changes, args.days)
    print(text)
    if args.out:
        Path(args.out).write_text(text)
    if args.board:
        n = sync_board(args.owner, threads, changes, since, args.dry_run)
        print(f"{n} item(s) on the board")
    return 0


def explain(exc: GitHubError) -> str:
    """One readable sentence for a refusal, with the fix the message itself does not name."""
    msg = (exc.message or "").strip().replace("\n", " ")
    low = msg.lower()
    if "reserved value" in low:
        return (f"GitHub refused a field name it reserves: {msg[:160]}. Rename that entry in "
                "BOARD_FIELDS; the token is fine.")
    if "createprojectv2" in low or "projectsv2" in low or "projects" in low and "scope" in low:
        return (f"GitHub refused a Projects v2 call: {msg[:160]}. The token needs the classic "
                "`project` scope or fine-grained account permission Projects: read/write.")
    if exc.status in (401, 403):
        return f"HTTP {exc.status}: {msg[:160]}. The token is present but not allowed to do this."
    return f"HTTP {exc.status}: {msg[:200]}"


def _run() -> int:
    try:
        return main()
    except GitHubError as exc:
        # Both branches also write a `::error::` line. A workflow annotation is the one part of
        # a failed run that the REST API exposes from a restricted network; the job log is not.
        # Two board runs failed with the PAT present and the only readable fact was "exit 1".
        if is_rate_limit(exc):
            # A traceback for a spent quota sends somebody reading code that is not wrong.
            when = rate_limit_reset()
            print(f"\nGitHub API rate limit exceeded for this token. It resets at "
                  f"{when}. Nothing is broken; re-run the workflow then.")
            print(f"::error::rate limit exceeded; resets at {when}")
            return 1
        reason = explain(exc)
        print(f"\n{reason}")
        print(f"::error::{reason}")
        return 1


if __name__ == "__main__":
    sys.exit(_run())
