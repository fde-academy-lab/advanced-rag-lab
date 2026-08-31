#!/usr/bin/env python3
"""One-time GitHub provisioning for this repository.

Creates everything that cannot live in the git tree: repository settings, labels, milestones,
seeded issues (open and closed), Discussions with their categories and seeded threads, and a
Projects v2 board with custom fields and items.

    export GITHUB_TOKEN=github_pat_...
    python scripts/setup_github.py --owner OWNER --repo nanorag

Idempotent: safe to re-run. Anything that already exists is skipped rather than duplicated.

    --dry-run     print what would happen, change nothing
    --only        create,settings,labels,milestones,issues,discussions,project,push
    --private     create the repository private (default public)
    --skip        same vocabulary, inverted

Token permissions needed (fine-grained PAT):
    Repository → Administration: read/write   (settings, labels, enabling Discussions)
                 Contents:       read/write
                 Issues:         read/write
                 Discussions:    read/write
                 Pull requests:  read/write
    Account    → Projects:       read/write   (only for the board)

If the Projects permission is unavailable, everything else still runs and the board step is
reported as skipped with the manual instructions.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import seed_content as content  # noqa: E402
from gh import GitHubError, fail, graphql, ok, request, skip, warn  # noqa: E402
from gh import token as gh_token  # noqa: E402

STEPS = ("create", "settings", "labels", "milestones", "issues", "discussions",
         "project", "push")




def preflight(owner):
    """Prove the token works and report who it is, before anything is created.

    Every later failure is easier to read once this has run: a 404 means the repository is
    missing rather than the token being wrong, and a 403 means a permission is missing rather
    than the credential being bad.
    """
    try:
        me = request("GET", "/user")
    except GitHubError as exc:
        if exc.status == 401:
            print("\n\033[31mGITHUB_TOKEN is not valid.\033[0m  GitHub answered: "
                  f"{exc.message}")
            print("\nMost often this is the placeholder pasted verbatim, an expired token, or")
            print("one copied with a trailing space. Check with:")
            print('  curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" '
                  "https://api.github.com/user")
            print("\nA working token prints your account JSON; a bad one prints "
                  '{"message":"Bad credentials"}.')
        else:
            print(f"\n\033[31mCannot authenticate: {exc.message}\033[0m")
        return False
    preflight.login = me.get("login")
    detail = "" if preflight.login.lower() == owner.lower() else \
        f"  \033[33m(--owner is {owner} — an org, or a typo?)\033[0m"
    print(f"  authenticated as \033[1m{preflight.login}\033[0m{detail}")
    return True


preflight.login = None



def run_step(name, fn, *args):
    """Run one provisioning step, reporting a failure instead of aborting the rest.

    The steps are independent. A token without Projects access, or a session whose egress
    proxy serves no GraphQL, should still get labels, milestones, issues and settings.
    """
    try:
        return fn(*args)
    except GitHubError as exc:
        fail(name, exc.message[:160])
        return None


def existing_state(path, dry, default):
    """Read current state, tolerating a repository that does not exist yet under --dry-run.

    A dry run has to work before the repository is created, otherwise the only way to preview
    the plan is to first do the thing you wanted to preview.
    """
    try:
        return request("GET", path)
    except GitHubError:
        if dry:
            return default
        raise


# ────────────────────────────────────────────────────────────────── creation ──
def create_repository(owner, repo, private, dry):
    """Create the repository if it does not exist yet. Returns the repo object or None.

    Repository creation is the one call that is not repository-scoped, so it is also the one
    call a repo-pinned session cannot make. Run this step from a machine with an ordinary PAT.
    """
    try:
        info = request("GET", f"/repos/{owner}/{repo}")
        skip(f"{owner}/{repo}", f"already exists · {info['visibility']}")
        return info
    except GitHubError:
        pass

    payload = {
        "name": repo,
        "private": bool(private),
        "description": ("Runnable retrieval / RAG / evaluation curriculum — 10 notebooks and a "
                        "toolkit that run entirely in memory, with an eval gate in CI"),
        "homepage": f"https://{owner}.github.io/{repo}/",
        "has_issues": True,
        "has_projects": True,
        "has_wiki": False,
        "auto_init": False,
    }
    if dry:
        ok(f"{owner}/{repo}", "would create")
        return None

    # /user/repos when the token's own login owns it, /orgs/{owner}/repos otherwise.
    # preflight() has already proved the token works, so a None login here means the owner is
    # genuinely an organisation rather than an authentication failure in disguise.
    login = preflight.login
    path = "/user/repos" if login and login.lower() == owner.lower() else f"/orgs/{owner}/repos"
    try:
        info = request("POST", path, payload)
    except GitHubError as exc:
        fail(f"{owner}/{repo}", exc.message)
        print(f"    tried POST {path}")
        if path.startswith("/orgs/"):
            print(f"    the token authenticates as {login!r}, which is not {owner!r}, so this "
                  "was\n    treated as an organisation. If it is your own account, check the "
                  "spelling\n    of --owner.")
        print("    a fine-grained PAT needs Administration: read/write on the target account,")
        print("    or use:  gh repo create "
              f"{owner}/{repo} --{'private' if private else 'public'}")
        return None
    ok(f"{owner}/{repo}", f"created · {info['visibility']}")
    return info


def push_repository(owner, repo, dry):
    """Point origin at the new repository and push the full phased history.

    The push authenticates with GITHUB_TOKEN rather than falling through to git's interactive
    prompt. GitHub stopped accepting account passwords for git operations in August 2021, so
    that prompt can only ever fail — and it fails after asking for a secret, which is the worst
    possible shape for a credential error.

    The token reaches git through GIT_ASKPASS, reading it from the environment. It is never
    written into the remote URL (which persists in .git/config, survives the run, and gets
    copied by anyone who clones your working tree), never passed on a command line (visible in
    ps to every user on the box), and never written to the askpass script itself.
    """
    import os
    import stat
    import subprocess
    import tempfile

    root = Path(__file__).resolve().parent.parent
    url = f"https://github.com/{owner}/{repo}.git"

    def git(*a, check=True, env=None):
        return subprocess.run(["git", "-C", str(root), *a], check=check,
                              capture_output=True, text=True, env=env)

    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    existing = git("remote", "get-url", "origin", check=False)
    if existing.returncode == 0 and existing.stdout.strip() != url:
        warn("origin", f"already points at {existing.stdout.strip()} — leaving it alone")
        return
    if dry:
        ok("push", f"would push {branch} to {url}")
        return
    if existing.returncode != 0:
        git("remote", "add", "origin", url)
        ok("origin", url)

    askpass = tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False)
    askpass.write(
        "#!/bin/sh\n"
        "case \"$1\" in\n"
        "  *[Uu]sername*) printf 'x-access-token' ;;\n"
        "  *) printf '%s' \"$GH_PUSH_TOKEN\" ;;\n"
        "esac\n")
    askpass.close()
    os.chmod(askpass.name, stat.S_IRWXU)  # 0700 — readable only by this user

    env = {**os.environ,
           "GIT_ASKPASS": askpass.name,
           "GH_PUSH_TOKEN": gh_token(),
           "GIT_TERMINAL_PROMPT": "0"}  # fail loudly rather than hanging on a hidden prompt
    try:
        res = git("push", "-u", "origin", branch, check=False, env=env)
    finally:
        os.unlink(askpass.name)

    if res.returncode != 0:
        detail = (res.stderr or res.stdout).strip()
        fail("push", detail.splitlines()[-1] if detail else "failed")
        if "403" in detail or "not accessible" in detail or "denied" in detail:
            print("    the token authenticated but is not allowed to write here — a "
                  "fine-grained PAT\n    needs Contents: read/write on this repository.")
        print(f"    or push by hand:  git push -u origin {branch}")
        print("    (at the password prompt paste the token, not your account password)")
        return
    ok("push", f"{branch} → {url}")


# ────────────────────────────────────────────────────────────────── settings ──
def configure_repository(owner, repo, dry):
    """Description, topics, features, merge policy, branch protection."""
    payload = {
        "description": ("Runnable retrieval / RAG / evaluation curriculum — 10 notebooks and a "
                        "toolkit that run entirely in memory, with an eval gate in CI"),
        "homepage": f"https://{owner}.github.io/{repo}/",
        "has_issues": True,
        "has_projects": True,
        "has_discussions": True,
        "has_wiki": False,
        "allow_squash_merge": True,
        "allow_merge_commit": False,
        "allow_rebase_merge": True,
        "delete_branch_on_merge": True,
        "allow_auto_merge": True,
        "squash_merge_commit_title": "PR_TITLE",
        "squash_merge_commit_message": "PR_BODY",
    }
    if dry:
        skip("settings", "would set description, topics, enable Discussions")
        return
    try:
        request("PATCH", f"/repos/{owner}/{repo}", payload)
        ok("repository settings", "Discussions + Projects enabled, squash-merge only")
    except GitHubError as exc:
        fail("repository settings", exc.message[:120])

    topics = ["rag", "retrieval-augmented-generation", "information-retrieval", "bm25",
              "reranking", "vector-search", "llm-evaluation", "evaluation", "bedrock",
              "jupyter-notebooks", "teaching-materials", "python", "sqlite", "fts5",
              "hybrid-search", "llm-as-a-judge"]
    try:
        request("PUT", f"/repos/{owner}/{repo}/topics", {"names": topics})
        ok("topics", f"{len(topics)} set")
    except GitHubError as exc:
        warn("topics", exc.message[:100])

    # Branch protection: require CI + the eval gate, and a review. Best-effort — this needs
    # Administration:write and is unavailable on some plans for private repos.
    protection = {
        "required_status_checks": {
            "strict": True,
            "contexts": ["Lint", "Tests (py3.11)",
                         "One-click promise (fresh machine, no pip install)"],
        },
        "enforce_admins": False,
        "required_pull_request_reviews": {
            "required_approving_review_count": 1,
            "dismiss_stale_reviews": True,
        },
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    }
    try:
        request("PUT", f"/repos/{owner}/{repo}/branches/main/protection", protection)
        ok("branch protection", "main requires CI + 1 review")
    except GitHubError as exc:
        warn("branch protection", f"skipped — {exc.message[:90]}")


# ──────────────────────────────────────────────────────────────────── labels ──
def create_labels(owner, repo, dry):
    existing = {l["name"] for l in
                existing_state(f"/repos/{owner}/{repo}/labels?per_page=100", dry, [])}
    created = updated = 0
    for name, color, description in content.LABELS:
        if dry:
            skip(f"label {name}")
            continue
        payload = {"name": name, "color": color, "description": description}
        try:
            if name in existing:
                request("PATCH", f"/repos/{owner}/{repo}/labels/{name.replace(' ', '%20')}",
                        payload)
                updated += 1
            else:
                request("POST", f"/repos/{owner}/{repo}/labels", payload)
                created += 1
        except GitHubError as exc:
            warn(f"label {name}", exc.message[:80])
    # Remove GitHub's defaults we do not use, so the label list stays legible.
    for junk in ("bug", "enhancement", "question", "invalid", "wontfix", "duplicate"):
        if junk in existing and not dry:
            try:
                request("DELETE", f"/repos/{owner}/{repo}/labels/{junk}")
            except GitHubError:
                pass
    ok("labels", f"{created} created, {updated} updated")


# ──────────────────────────────────────────────────────────────── milestones ──
def create_milestones(owner, repo, dry):
    existing = {m["title"]: m for m in
                existing_state(f"/repos/{owner}/{repo}/milestones?state=all&per_page=100",
                               dry, [])}
    mapping = {}
    for title, description, state in content.MILESTONES:
        if title in existing:
            mapping[title] = existing[title]["number"]
            continue
        if dry:
            skip(f"milestone {title}")
            continue
        try:
            m = request("POST", f"/repos/{owner}/{repo}/milestones",
                        {"title": title, "description": description, "state": state})
            mapping[title] = m["number"]
        except GitHubError as exc:
            warn(f"milestone {title}", exc.message[:80])
    ok("milestones", f"{len(mapping)} present")
    return mapping


# ──────────────────────────────────────────────────────────────────── issues ──
def create_issues(owner, repo, milestones, dry):
    existing = {i["title"] for i in
                existing_state(f"/repos/{owner}/{repo}/issues?state=all&per_page=100",
                               dry, [])}
    created = []
    for spec in content.ISSUES:
        if spec["title"] in existing:
            skip(f"issue “{spec['title'][:52]}…”", "exists")
            continue
        if dry:
            skip(f"issue “{spec['title'][:52]}…”", spec["state"])
            continue
        payload = {"title": spec["title"], "body": spec["body"], "labels": spec["labels"]}
        if spec.get("milestone") in milestones:
            payload["milestone"] = milestones[spec["milestone"]]
        try:
            issue = request("POST", f"/repos/{owner}/{repo}/issues", payload)
            if spec["state"] == "closed":
                request("PATCH", f"/repos/{owner}/{repo}/issues/{issue['number']}",
                        {"state": "closed", "state_reason": "completed"})
            created.append((issue["number"], spec["title"], spec["state"]))
            ok(f"issue #{issue['number']}", f"{spec['state']:<6} {spec['title'][:56]}")
            time.sleep(0.6)                      # stay under the secondary rate limit
        except GitHubError as exc:
            fail(f"issue “{spec['title'][:40]}…”", exc.message[:90])
    return created


# ─────────────────────────────────────────────────────────────── discussions ──
REPO_Q = """
query($owner:String!,$name:String!){
  repository(owner:$owner,name:$name){
    id hasDiscussionsEnabled
    discussionCategories(first:50){ nodes { id name slug } }
    discussions(first:100){ nodes { title } }
  }
}"""

CREATE_DISCUSSION_M = """
mutation($repoId:ID!,$catId:ID!,$title:String!,$body:String!){
  createDiscussion(input:{repositoryId:$repoId,categoryId:$catId,title:$title,body:$body}){
    discussion { number url }
  }
}"""

ADD_COMMENT_M = """
mutation($discussionId:ID!,$body:String!){
  addDiscussionComment(input:{discussionId:$discussionId,body:$body}){
    comment { id }
  }
}"""

DISCUSSION_ID_Q = """
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){ discussion(number:$number){ id } }
}"""


def create_discussions(owner, repo, dry):
    data = graphql(REPO_Q, {"owner": owner, "name": repo})["repository"]
    if not data["hasDiscussionsEnabled"]:
        fail("discussions", "not enabled — run the `settings` step first")
        return []

    categories = {c["name"]: c["id"] for c in data["discussionCategories"]["nodes"]}
    existing = {d["title"] for d in data["discussions"]["nodes"]}

    missing = {name for name, *_ in content.CATEGORIES} - set(categories)
    if missing:
        warn("discussion categories",
             f"create manually in Settings → Discussions: {', '.join(sorted(missing))}")
        print("      (the GitHub API cannot create discussion categories; "
              "threads for missing categories fall back to General)")

    created = []
    for spec in content.DISCUSSIONS:
        title = spec["title"]
        if title in existing:
            skip(f"discussion “{title[:52]}…”", "exists")
            continue
        cat_id = categories.get(spec["category"]) or categories.get("General")
        if not cat_id:
            fail(f"discussion “{title[:40]}…”", "no usable category")
            continue
        if dry:
            skip(f"discussion “{title[:52]}…”", spec["category"])
            continue

        body = spec["body"]
        if "[worked example]" in title or spec["category"] in ("Q&A", "Design Reviews",
                                                              "Show and tell", "Reading Club",
                                                              "Interview Prep"):
            body += content.SEED_FOOTER
        try:
            out = graphql(CREATE_DISCUSSION_M, {
                "repoId": data["id"], "catId": cat_id, "title": title, "body": body})
            disc = out["createDiscussion"]["discussion"]
            created.append((disc["number"], title))
            ok(f"discussion #{disc['number']}", f"{spec['category']:<16} {title[:48]}")

            if spec.get("answer"):
                ids = graphql(DISCUSSION_ID_Q,
                              {"owner": owner, "name": repo, "number": disc["number"]})
                graphql(ADD_COMMENT_M, {
                    "discussionId": ids["repository"]["discussion"]["id"],
                    "body": spec["answer"] + content.SEED_FOOTER})
                ok("  ↳ answer posted")
            time.sleep(0.8)
        except GitHubError as exc:
            fail(f"discussion “{title[:40]}…”", exc.message[:90])
    return created


# ─────────────────────────────────────────────────────────────────── project ──
# repositoryOwner is the interface both User and Organization implement, so this resolves a
# personal account and an org through one field and cannot half-fail the way asking for both
# separately does. The typename is worth having: a board on a user account and a board on an
# org differ in who can see it and which token scope creates it.
OWNER_ID_Q = """
query($login:String!){ repositoryOwner(login:$login){ id __typename } }"""

CREATE_PROJECT_M = """
mutation($ownerId:ID!,$title:String!){
  createProjectV2(input:{ownerId:$ownerId,title:$title}){ projectV2 { id number url } }
}"""

CREATE_FIELD_M = """
mutation($projectId:ID!,$name:String!,$options:[ProjectV2SingleSelectFieldOptionInput!]!){
  createProjectV2Field(input:{projectId:$projectId,dataType:SINGLE_SELECT,
                              name:$name,singleSelectOptions:$options}){
    projectV2Field { ... on ProjectV2SingleSelectField { id name } }
  }
}"""

CREATE_TEXT_FIELD_M = """
mutation($projectId:ID!,$name:String!){
  createProjectV2Field(input:{projectId:$projectId,dataType:TEXT,name:$name}){
    projectV2Field { ... on ProjectV2Field { id name } }
  }
}"""

ADD_ITEM_M = """
mutation($projectId:ID!,$contentId:ID!){
  addProjectV2ItemById(input:{projectId:$projectId,contentId:$contentId}){ item { id } }
}"""

ISSUE_NODE_Q = """
query($owner:String!,$name:String!,$number:Int!){
  repository(owner:$owner,name:$name){ issue(number:$number){ id } }
}"""

FIELDS = [
    ("Phase", ["P0 Harness", "P1 Baseline", "P2 Retrieval", "P3 Context", "P4 Evaluation",
               "P5 Cost", "P6 Agentic", "P7 Hardening"]),
    ("Effort", ["S <1d", "M 2-3d", "L ~1w", "XL cohort"]),
    ("Cohort", ["C1", "C2", "faculty", "open"]),
    ("Risk", ["low", "medium", "high"]),
]


def create_project(owner, repo, issues, dry):
    if dry:
        skip("project board", "would create 'Advanced RAG — Delivery' with 5 custom fields")
        return
    try:
        ids = graphql(OWNER_ID_Q, {"login": owner}, partial_ok=True)
    except GitHubError as exc:
        warn("project board", f"cannot resolve owner — {exc.message[:80]}")
        return
    node = ids.get("repositoryOwner") or {}
    owner_id, kind = node.get("id"), node.get("__typename", "account")
    if not owner_id:
        warn("project board", f"no GitHub account named {owner!r}")
        return
    ok("  owner", f"{owner} · {kind}")

    try:
        out = graphql(CREATE_PROJECT_M,
                      {"ownerId": owner_id, "title": "Advanced RAG — Delivery"})
        project = out["createProjectV2"]["projectV2"]
        ok("project board", project["url"])
    except GitHubError as exc:
        warn("project board", f"skipped — {exc.message[:110]}")
        print("      A classic PAT with the `project` scope, or a fine-grained token with")
        print("      account permission Projects: read/write, is required to create boards.")
        print("      Everything else in this script has still run. Create the board manually")
        print("      following docs/08-project-management/board.md — it takes about five minutes.")
        return

    for name, options in FIELDS:
        try:
            graphql(CREATE_FIELD_M, {
                "projectId": project["id"], "name": name,
                "options": [{"name": o, "description": "", "color": "GRAY"} for o in options]})
            ok(f"  field {name}", f"{len(options)} options")
        except GitHubError as exc:
            warn(f"  field {name}", exc.message[:80])
    try:
        graphql(CREATE_TEXT_FIELD_M, {"projectId": project["id"], "name": "Metric moved"})
        ok("  field Metric moved", "text — the field that makes the board worth keeping")
    except GitHubError as exc:
        warn("  field Metric moved", exc.message[:80])

    added = 0
    for number, _title, _state in issues:
        try:
            node = graphql(ISSUE_NODE_Q, {"owner": owner, "name": repo, "number": number})
            graphql(ADD_ITEM_M, {"projectId": project["id"],
                                 "contentId": node["repository"]["issue"]["id"]})
            added += 1
            time.sleep(0.4)
        except GitHubError as exc:
            warn(f"  add #{number}", exc.message[:70])
    ok("  items", f"{added} issues added to the board")


# ────────────────────────────────────────────────────────────────────── main ──
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--private", action="store_true",
                    help="create the repository private (default public)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default="", help=f"comma separated: {','.join(STEPS)}")
    ap.add_argument("--skip", default="", help="comma separated")
    args = ap.parse_args()

    wanted = set(args.only.split(",")) if args.only else set(STEPS)
    wanted -= set(args.skip.split(",")) if args.skip else set()

    print(f"\n\033[1mProvisioning {args.owner}/{args.repo}\033[0m"
          + ("  \033[33m(dry run)\033[0m" if args.dry_run else ""))

    if not preflight(args.owner):
        return 1

    # Keep the tree's badges, clone URL, CODEOWNERS and packaging metadata in step with the
    # owner/repo actually being provisioned, so a fork does not ship badges pointing upstream.
    if not args.dry_run:
        import subprocess
        subprocess.run([sys.executable, str(Path(__file__).with_name("retarget.py")),
                        "--owner", args.owner, "--repo", args.repo], check=False)

    if "create" in wanted:
        print("\033[1mRepository\033[0m")
        run_step("create", create_repository,
                 args.owner, args.repo, args.private, args.dry_run)

    try:
        repo_info = request("GET", f"/repos/{args.owner}/{args.repo}")
        print(f"  {args.owner}/{args.repo} · {repo_info['visibility']} · "
              f"default branch {repo_info['default_branch']}\n")
    except GitHubError as exc:
        if not args.dry_run:
            print(f"\n\033[31mCannot reach {args.owner}/{args.repo}: {exc.message}\033[0m")
            print("\nCreate it by hand, then re-run this script:")
            print(f"  gh repo create {args.owner}/{args.repo} "
                  f"--{'private' if args.private else 'public'}")
            print("  …or at https://github.com/new")
            return 1

    milestones, issues = {}, []
    if "settings" in wanted:
        print("\033[1mRepository settings\033[0m")
        configure_repository(args.owner, args.repo, args.dry_run)
    if "labels" in wanted:
        print("\n\033[1mLabels\033[0m")
        create_labels(args.owner, args.repo, args.dry_run)
    if "milestones" in wanted:
        print("\n\033[1mMilestones\033[0m")
        milestones = create_milestones(args.owner, args.repo, args.dry_run)
    if "issues" in wanted:
        print("\n\033[1mIssues\033[0m")
        if not milestones:
            milestones = {m["title"]: m["number"] for m in existing_state(
                f"/repos/{args.owner}/{args.repo}/milestones?state=all&per_page=100",
                args.dry_run, [])}
        issues = create_issues(args.owner, args.repo, milestones, args.dry_run)
    if "discussions" in wanted:
        print("\n\033[1mDiscussions\033[0m")
        run_step("discussions", create_discussions,
                 args.owner, args.repo, args.dry_run)
    if "project" in wanted:
        print("\n\033[1mProject board\033[0m")
        if not issues and not args.dry_run:
            issues = [(i["number"], i["title"], i["state"]) for i in request(
                "GET", f"/repos/{args.owner}/{args.repo}/issues?state=all&per_page=100")
                if "pull_request" not in i]
        run_step("project board", create_project,
                 args.owner, args.repo, issues, args.dry_run)

    if "push" in wanted:
        print("\n\033[1mPush\033[0m")
        push_repository(args.owner, args.repo, args.dry_run)

    print(f"\n\033[1mDone.\033[0m  https://github.com/{args.owner}/{args.repo}")
    print("\nManual steps the API cannot do:")
    print("  1. Settings → Discussions → create the custom categories listed above")
    print("     (Design Reviews, Reading Club, Interview Prep) and set Q&A to answerable")
    print("  2. Settings → Pages → source: GitHub Actions   (enables the notebook site)")
    print("  3. Pin 2–3 discussions and 3–4 issues")
    print("  4. Add a repository social preview image (Settings → General)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
