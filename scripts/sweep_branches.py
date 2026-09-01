#!/usr/bin/env python3
"""Delete branches whose pull request is finished, and nothing else.

The predicate is the whole design, so it is stated before the code:

    delete a branch when every pull request that ever pointed at it is **merged**,
    and none of them is open.

Two alternatives were rejected. *"Merged into main"* — an ancestry check — keeps exactly the
branches you most want gone, because a squash merge rewrites the commit and the branch tip never
appears in main's history. *"Older than N days"* deletes work in progress that somebody left
over a holiday.

Requiring a merged pull request also means a branch nobody ever opened one for is never touched:
if you pushed an experiment and told no one, this will not tidy it away.

    GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo DRY_RUN=true python scripts/sweep_branches.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import GitHubError, request  # noqa: E402

# Never touched, whatever their pull requests say.
#
# `dependabot/*` is on this list for a reason that is not obvious: Dependabot owns those refs,
# and deleting one closes its pull request. Ten of them are open on this repository, and a
# helpful sweep would silently close all ten.
PROTECTED = (
    re.compile(r"^(main|master|gh-pages|release/.*)$"),
    re.compile(r"^dependabot/"),
    re.compile(r"^revert-"),
)


def protected(name: str) -> bool:
    return any(p.match(name) for p in PROTECTED)


def verdict(name: str, related: list[dict], default: str) -> tuple[bool, str]:
    """Should this branch go, and why. Pure, so the rule is testable without a network."""
    if name == default or protected(name):
        return False, "protected"
    if not related:
        return False, "no pull request ever pointed here"
    if any(p["state"] == "open" for p in related):
        return False, ("open pull request "
                       + ", ".join(f"#{p['number']}" for p in related if p["state"] == "open"))
    if not all(p.get("merged_at") for p in related):
        closed = ", ".join(f"#{p['number']}" for p in related if not p.get("merged_at"))
        return False, (f"closed without merging ({closed}) — that is a decision, and the "
                       "branch is the record of it")
    return True, ", ".join(f"#{p['number']}" for p in related) + " merged"


def paged(path: str) -> list[dict]:
    out, page = [], 1
    while True:
        chunk = request("GET", f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        if not chunk:
            return out
        out.extend(chunk)
        if len(chunk) < 100:
            return out
        page += 1


def main() -> int:
    repo = os.environ["GITHUB_REPOSITORY"]
    dry = os.environ.get("DRY_RUN", "false").lower() == "true"
    default = request("GET", f"/repos/{repo}")["default_branch"]

    branches = [b["name"] for b in paged(f"/repos/{repo}/branches")]
    prs = paged(f"/repos/{repo}/pulls?state=all")

    by_head: dict[str, list[dict]] = {}
    for pr in prs:
        by_head.setdefault(pr["head"]["ref"], []).append(pr)

    deleted, kept = [], []
    for name in sorted(branches):
        go, why = verdict(name, by_head.get(name, []), default)
        if not go:
            kept.append((name, why))
            continue
        if dry:
            deleted.append((name, f"would delete — {why}"))
            continue
        try:
            request("DELETE", f"/repos/{repo}/git/refs/heads/{name}")
            deleted.append((name, f"deleted — {why}"))
        except GitHubError as exc:
            kept.append((name, f"delete failed: {exc.message[:70]}"))

    width = max((len(n) for n, _ in deleted + kept), default=10)
    print(f"\n{'DRY RUN — ' if dry else ''}{len(branches)} branches\n")
    for name, why in deleted:
        print(f"  ✂  {name:<{width}}  {why}")
    for name, why in kept:
        print(f"  ·  {name:<{width}}  {why}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(f"\n### Branch sweep{' (dry run)' if dry else ''}\n\n")
            fh.write(f"{len(deleted)} removed, {len(kept)} kept, of {len(branches)}.\n\n")
            if deleted:
                fh.write("| branch | |\n|---|---|\n")
                for name, why in deleted:
                    fh.write(f"| `{name}` | {why} |\n")
            fh.write("\n<sub>A branch goes only when every pull request that pointed at it is "
                     "merged and none is open. `dependabot/*` is never touched — deleting one "
                     "closes its pull request.</sub>\n")
    print(f"\n{len(deleted)} removed, {len(kept)} kept.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
