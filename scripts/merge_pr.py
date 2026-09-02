#!/usr/bin/env python3
"""Merge a pull request, with the checks that make it safe to do unattended.

This exists so that "let Claude merge pull requests" can be granted as a narrow permission
rather than a broad one. A rule allowing arbitrary `python -c` or `gh api` would let anything
through; a rule allowing *this file* allows exactly one operation, and the guards below are the
reason the grant is reasonable:

  * the repository is pinned to .identity.json — it cannot merge somewhere else
  * the pull request must be open, not a draft, and mergeable
  * **every check run must have completed successfully.** No override flag exists. A red build
    is the one case where a human should be in the loop, and adding `--force` here would quietly
    remove the only thing that makes the rest of this defensible
  * the merge method is squash by default, matching how this repository merges

    python scripts/merge_pr.py 66
    python scripts/merge_pr.py 66 --title "feat: …" --method merge
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from gh import GitHubError, request  # noqa: E402

# Statuses that are not a failure: a skipped job, a neutral one, and a check that GitHub never
# required. Anything else pending or failing stops the merge.
OK = {"success", "skipped", "neutral"}


def identity() -> tuple[str, str]:
    data = json.loads((ROOT / ".identity.json").read_text())
    return data["owner"], data["repo"]


def classify(check_runs: list[dict]) -> tuple[list[str], list[str]]:
    """Pending and failing check names. Pure, so the rule below is testable.

    **No check runs at all counts as pending.** GitHub registers a commit's checks a few
    seconds after the push; in that window the list is empty, and an empty list read as
    "nothing pending, nothing failing" merged — or refused — on no evidence at all.
    """
    if not check_runs:
        return ["(checks not registered yet)"], []
    pending = [c["name"] for c in check_runs if c["status"] != "completed"]
    failing = [f"{c['name']} ({c.get('conclusion')})" for c in check_runs
               if c["status"] == "completed" and c.get("conclusion") not in OK]
    return pending, failing


def check_state(owner: str, repo: str, sha: str) -> tuple[list[str], list[str]]:
    runs = request("GET", f"/repos/{owner}/{repo}/commits/{sha}/check-runs?per_page=100")
    return classify(runs["check_runs"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("number", type=int)
    ap.add_argument("--method", default="squash", choices=["squash", "merge", "rebase"])
    ap.add_argument("--title")
    ap.add_argument("--wait", type=int, default=0,
                    help="seconds to wait for pending checks (0 = do not wait)")
    ap.add_argument("--expect-head",
                    help="the commit you just pushed; wait until the PR's head is this sha "
                         "before reading any checks, so a fresh push is not judged on the "
                         "previous commit's results")
    args = ap.parse_args()

    owner, repo = identity()
    pr = request("GET", f"/repos/{owner}/{repo}/pulls/{args.number}")

    if pr["state"] != "open":
        print(f"#{args.number} is {pr['state']}"
              + (" and already merged" if pr.get("merged") else ""))
        return 1
    if pr.get("draft"):
        print(f"#{args.number} is a draft")
        return 1

    deadline = time.time() + args.wait
    while True:
        # Re-read the PR every iteration. The head sha was read once, before the loop, and a
        # merge attempted straight after a push judged the *previous* commit's red check.
        pr = request("GET", f"/repos/{owner}/{repo}/pulls/{args.number}")
        head = pr["head"]["sha"]
        if args.expect_head and not head.startswith(args.expect_head):
            if time.time() >= deadline:
                print(f"#{args.number} head is {head[:8]}, not the pushed {args.expect_head[:8]}")
                return 1
            print(f"  PR head is {head[:8]}, waiting for {args.expect_head[:8]}…")
            time.sleep(10)
            continue
        pending, failing = check_state(owner, repo, head)
        if failing:
            print(f"#{args.number} has failing checks, so it is not being merged:")
            for f in failing:
                print(f"  ✗ {f}")
            print("\nThere is no override. A red build is exactly the case where a person "
                  "should decide.")
            return 1
        if not pending:
            break
        if time.time() >= deadline:
            print(f"#{args.number} still has {len(pending)} check(s) running: "
                  + ", ".join(pending[:5]))
            print("\nRe-run with --wait <seconds> to wait for them.")
            return 1
        print(f"  {len(pending)} check(s) running, waiting…")
        time.sleep(20)

    if pr.get("mergeable") is False:
        print(f"#{args.number} has conflicts with {pr['base']['ref']}")
        return 1

    payload = {"merge_method": args.method}
    if args.title:
        payload["commit_title"] = args.title
    try:
        out = request("PUT", f"/repos/{owner}/{repo}/pulls/{args.number}/merge", payload)
    except GitHubError as exc:
        print(f"merge refused: {exc.message}")
        return 1

    print(f"merged #{args.number} ({args.method}) → {out.get('sha', '')[:10]}")
    print(f"  {pr['title']}")
    print(f"  https://github.com/{owner}/{repo}/pull/{args.number}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
