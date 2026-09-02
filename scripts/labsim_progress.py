#!/usr/bin/env python3
"""Who is doing the hands-on work, and how it is going — per learner, from the bot's own tags.

The grading bot leaves a machine-readable tag on every reply. This reads them back and groups
them by the *thread author*, which is the learner: one row per person with attempts, clears,
retries and the units they have cleared. Three consumers:

    /progress on a thread   →  --login <author> --render reply.md   (the respond job)
    the Hands-on board      →  --board                              (weekly, needs a PAT)
    a human                 →  no flags: prints the table

Not a leaderboard, on purpose. Rows are sorted by login, not by score, and there is no score
column. Counting attempts and clears is *tracking*; ranking them on a public repository would
mostly rank who had a free weekend, and the weekly digest already declines to do that.

A retry is a graded attempt on a thread that already carried a fail. A clear counts once per
unit per learner, however many threads it took.
"""
from __future__ import annotations

import argparse
import collections
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lab-simulator"))
from gh import GitHubError, graphql, is_rate_limit, rate_limit_reset  # noqa: E402

TAG = re.compile(r"<!--\s*labsim:([A-Z]{1,2}\d{1,2}):(pass|fail|hint|no-result|why):?(.*?)-->",
                 re.S)
BOT_LOGINS = {"github-actions", "github-actions[bot]"}

Q = """
query($owner:String!,$name:String!,$cursor:String){
  repository(owner:$owner,name:$name){
    discussions(first:50, after:$cursor, orderBy:{field:UPDATED_AT,direction:DESC}){
      pageInfo{ hasNextPage endCursor }
      nodes{
        number title url createdAt updatedAt
        author{ login }
        category{ name }
        comments(last:60){ nodes{ body createdAt updatedAt author{ login } } }
      }
    }
  }
}"""


def simulator_category(name: str) -> bool:
    return re.sub(r"[^a-z]", "", (name or "").lower()) in {
        "labsimulator", "labsimulatorexercises", "exercisessubmissions"}


@dataclass
class Event:
    login: str
    unit: str
    kind: str                 # pass | fail | hint | why | no-result
    when: datetime
    thread: int
    title: str
    url: str


def harvest(owner: str, repo: str) -> list[Event]:
    """Every bot tag on every simulator thread, attributed to the thread's author."""
    events, cursor = [], None
    while True:
        page = graphql(Q, {"owner": owner, "name": repo,
                           "cursor": cursor})["repository"]["discussions"]
        for d in page["nodes"]:
            if not simulator_category(d["category"]["name"]):
                continue
            login = (d.get("author") or {}).get("login") or "ghost"
            for c in d["comments"]["nodes"]:
                if ((c.get("author") or {}).get("login") or "") not in BOT_LOGINS:
                    continue
                stamp = c.get("updatedAt") or c["createdAt"]
                when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
                for uid, kind, _payload in TAG.findall(c["body"] or ""):
                    events.append(Event(login, uid, kind, when, d["number"], d["title"], d["url"]))
        if not page["pageInfo"]["hasNextPage"]:
            return events
        cursor = page["pageInfo"]["endCursor"]


@dataclass
class Learner:
    login: str
    attempts: int = 0
    cleared: set[str] = field(default_factory=set)
    attempted: set[str] = field(default_factory=set)
    retries: int = 0
    hints: int = 0
    last_active: datetime | None = None
    threads: set[int] = field(default_factory=set)

    @property
    def open(self) -> set[str]:
        return self.attempted - self.cleared


def aggregate(events: list[Event]) -> dict[str, Learner]:
    """Pure. One Learner per login; retries are grades on a thread that already failed."""
    by_login: dict[str, Learner] = {}
    failed_threads: set[tuple[str, int]] = set()
    for e in sorted(events, key=lambda e: e.when):
        L = by_login.setdefault(e.login, Learner(e.login))
        L.threads.add(e.thread)
        L.last_active = max(L.last_active, e.when) if L.last_active else e.when
        if e.kind in ("pass", "fail"):
            L.attempts += 1
            L.attempted.add(e.unit)
            if (e.login, e.thread) in failed_threads:
                L.retries += 1
            if e.kind == "fail":
                failed_threads.add((e.login, e.thread))
            else:
                L.cleared.add(e.unit)
        elif e.kind == "hint":
            L.hints += 1
    return by_login


# ────────────────────────────────────────────────────────────────── rendering ──
def render_table(learners: dict[str, Learner], *, total_units: int) -> str:
    rows = ["| learner | attempts | cleared | open | retries | hints | last active |",
            "|---|---|---|---|---|---|---|"]
    for login in sorted(learners):
        L = learners[login]
        last = L.last_active.strftime("%Y-%m-%d") if L.last_active else "—"
        rows.append(f"| `{login}` | {L.attempts} | {len(L.cleared)}/{total_units} | "
                    f"{', '.join(sorted(L.open)) or '—'} | {L.retries} | {L.hints} | {last} |")
    return "\n".join(rows)


def render_for(login: str, learners: dict[str, Learner], units) -> str:
    """The `/progress` reply: one person's own picture, and what to do next."""
    from labsim.registry import unlocked

    L = learners.get(login)
    marker = "<!-- labsim-bot -->\n<!-- labsim:progress -->\n\n"
    if L is None or not L.attempts:
        return (marker + f"### `{login}` · nothing graded yet\n\nPost a unit in this category and "
                "the bot grades it. `/status` shows the pathway; the two places it starts are "
                "`F1` and `R1`, and the drills (`FD1`, `RD1`, `ED1`, `CD1`) take under fifteen "
                "minutes each.")
    by_track: dict[str, list] = collections.defaultdict(list)
    for u in units:
        by_track[u.track].append(u)
    lines = [marker, f"### `{login}` · {len(L.cleared)} of {len(units)} cleared", "",
             f"{L.attempts} graded attempt{'s' if L.attempts != 1 else ''} across "
             f"{len(L.threads)} thread{'s' if len(L.threads) != 1 else ''} · {L.retries} "
             f"retr{'ies' if L.retries != 1 else 'y'} · {L.hints} "
             f"hint{'s' if L.hints != 1 else ''} spent",
             "", "| track | cleared | open |", "|---|---|---|"]
    for track, us in by_track.items():
        done = [u.uid for u in us if u.uid in L.cleared]
        opened = [u.uid for u in us if u.uid in L.open]
        if done or opened:
            lines.append(f"| {track} | {', '.join(f'`{x}`' for x in done) or '—'} | "
                         f"{', '.join(f'`{x}`' for x in opened) or '—'} |")
    nxt = [u for u in unlocked(set(L.cleared)) if u.uid not in L.attempted]
    nxt.sort(key=lambda u: (not u.is_drill, u.minutes, u.uid))
    if L.open:
        lines += ["", "**Open threads** are the ones to finish first — a retry after a named "
                      "failure is where most of the learning is."]
    if nxt:
        lines += ["", "**Unlocked and untouched:** " + " · ".join(
            f"`{u.uid}` {u.title} ({'drill' if u.is_drill else 'unit'}, ~{u.minutes} min)"
            for u in nxt[:4])]
    if L.retries and L.attempts and L.retries / L.attempts > 0.5:
        lines += ["", "More than half your attempts are retries. That is not a problem — but if "
                      "the same check keeps catching you, `/why <check name>` on that thread says "
                      "what it is guarding against."]
    lines += ["", "<sub>Counted from the grading bot's own replies on threads you opened. Not a "
                  "ranking: nobody else's row is shown here.</sub>"]
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────── the board ──
BOARD_TITLE = "L.A.B. Simulator — Hands-on"
BOARD_FIELDS = {          # name → (dataType, options)
    "Attempts": ("NUMBER", None),
    "Cleared": ("NUMBER", None),
    "Retries": ("NUMBER", None),
    "Hints": ("NUMBER", None),
    "Open units": ("TEXT", None),
    "Cleared units": ("TEXT", None),
    "Last active": ("DATE", None),
    "Stage": ("SINGLE_SELECT", ["Starting", "Foundations", "Retrieval", "Evaluation",
                                "Cost & context", "Agentic", "Delivery", "Complete"]),
}

OWNER_Q = """query($login:String!){ repositoryOwner(login:$login){ id __typename
  ... on User { projectsV2(first:50){ nodes{ id title number } } }
  ... on Organization { projectsV2(first:50){ nodes{ id title number } } } } }"""
CREATE_PROJECT_M = """mutation($ownerId:ID!,$title:String!){
  createProjectV2(input:{ownerId:$ownerId,title:$title}){ projectV2 { id number url } } }"""
FIELDS_Q = """query($id:ID!){ node(id:$id){ ... on ProjectV2 {
  fields(first:50){ nodes{
    ... on ProjectV2Field { id name dataType }
    ... on ProjectV2SingleSelectField { id name dataType options { id name } } } }
  items(first:100){ nodes{ id content { ... on DraftIssue { id title } } } } } } }"""
CREATE_FIELD_M = """mutation($projectId:ID!,$name:String!,$type:ProjectV2CustomFieldType!){
  createProjectV2Field(input:{projectId:$projectId,dataType:$type,name:$name}){
    projectV2Field { ... on ProjectV2Field { id } } } }"""
CREATE_SELECT_M = """mutation($projectId:ID!,$name:String!,
                            $options:[ProjectV2SingleSelectFieldOptionInput!]!){
  createProjectV2Field(input:{projectId:$projectId,dataType:SINGLE_SELECT,name:$name,
                              singleSelectOptions:$options}){
    projectV2Field { ... on ProjectV2SingleSelectField { id } } } }"""
ADD_DRAFT_M = """mutation($projectId:ID!,$title:String!,$body:String!){
  addProjectV2DraftIssue(input:{projectId:$projectId,title:$title,body:$body}){
    projectItem { id } } }"""
SET_M = """mutation($projectId:ID!,$itemId:ID!,$fieldId:ID!,$value:ProjectV2FieldValue!){
  updateProjectV2ItemFieldValue(input:{projectId:$projectId,itemId:$itemId,
                                       fieldId:$fieldId,value:$value}){
    projectV2Item { id } } }"""


def stage_for(L: Learner, units) -> str:
    if not L.cleared:
        return "Starting"
    if L.cleared >= {u.uid for u in units}:
        return "Complete"
    order = ["foundations", "retrieval", "evaluation", "context", "cost", "agentic", "delivery"]
    by_uid = {u.uid: u for u in units}
    furthest = max((order.index(by_uid[u].track) for u in L.cleared if u in by_uid), default=0)
    return {"foundations": "Foundations", "retrieval": "Retrieval", "evaluation": "Evaluation",
            "context": "Cost & context", "cost": "Cost & context", "agentic": "Agentic",
            "delivery": "Delivery"}[order[furthest]]


def ensure_board(owner: str, dry: bool) -> tuple[str | None, dict]:
    """Find or create the board, then find or create every field. Returns (project_id, fields)."""
    data = graphql(OWNER_Q, {"login": owner})["repositoryOwner"]
    existing = next((p for p in data["projectsV2"]["nodes"] if p["title"] == BOARD_TITLE), None)
    if existing is None:
        if dry:
            print(f"would create board {BOARD_TITLE!r}")
            return None, {}
        made = graphql(CREATE_PROJECT_M, {"ownerId": data["id"], "title": BOARD_TITLE})
        existing = made["createProjectV2"]["projectV2"]
        print("created board", existing["url"])
    pid = existing["id"]
    node = graphql(FIELDS_Q, {"id": pid})["node"]
    fields = {f["name"]: f for f in node["fields"]["nodes"] if f}
    for name, (dtype, options) in BOARD_FIELDS.items():
        if name in fields:
            continue
        if dry:
            print(f"would create field {name} ({dtype})")
            continue
        try:
            if dtype == "SINGLE_SELECT":
                opts = [{"name": o, "description": "", "color": "GRAY"} for o in options]
                graphql(CREATE_SELECT_M, {"projectId": pid, "name": name, "options": opts})
            else:
                graphql(CREATE_FIELD_M, {"projectId": pid, "name": name, "type": dtype})
            print("created field", name)
        except GitHubError as exc:
            print(f"::warning::field {name!r} was refused and is skipped: {exc.message[:140]}")
    node = graphql(FIELDS_Q, {"id": pid})["node"]
    fields = {f["name"]: f for f in node["fields"]["nodes"] if f}
    fields["__items__"] = {i["content"]["title"]: i["id"]
                           for i in node["items"]["nodes"] if i.get("content")}
    return pid, fields


def _value(field: dict, raw):
    t = field["dataType"]
    if t == "NUMBER":
        return {"number": float(raw)}
    if t == "DATE":
        return {"date": raw}
    if t == "SINGLE_SELECT":
        opt = next((o["id"] for o in field["options"] if o["name"] == raw), None)
        return {"singleSelectOptionId": opt} if opt else None
    return {"text": str(raw)}


def sync_board(owner: str, learners: dict[str, Learner], units, dry: bool) -> int:
    pid, fields = ensure_board(owner, dry)
    if pid is None:
        return 0
    items = fields.pop("__items__", {})
    total = len(units)
    written = 0
    for login in sorted(learners):
        L = learners[login]
        title = f"@{login}"
        body = (f"Tracked from the L.A.B. Simulator grading bot's replies on threads opened by "
                f"@{login}. {len(L.cleared)}/{total} cleared. Threads: "
                + ", ".join(f"#{n}" for n in sorted(L.threads)))
        values = {
            "Attempts": L.attempts, "Cleared": len(L.cleared), "Retries": L.retries,
            "Hints": L.hints, "Open units": ", ".join(sorted(L.open)) or "—",
            "Cleared units": ", ".join(sorted(L.cleared)) or "—",
            "Last active": L.last_active.date().isoformat() if L.last_active else None,
            "Stage": stage_for(L, units),
        }
        if dry:
            print(f"would upsert {title}: {values}")
            continue
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
                print(f"  {title} {name}: {exc.message[:70]}")
        written += 1
        print("upserted", title, values["Stage"])
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--login", help="render one learner's /progress reply")
    ap.add_argument("--render", help="write the reply here (with --login)")
    ap.add_argument("--board", action="store_true", help="upsert one draft item per learner")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    from labsim.registry import all_units
    units = all_units()
    learners = aggregate(harvest(args.owner, args.repo))

    if args.login:
        text = render_for(args.login, learners, units)
        if args.render:
            Path(args.render).write_text(text)
        print(text)
        return 0
    if args.board:
        n = sync_board(args.owner, learners, units, args.dry_run)
        print(f"{n} learner(s) on the board")
        return 0
    print(render_table(learners, total_units=len(units)))
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
