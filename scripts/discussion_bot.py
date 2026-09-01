#!/usr/bin/env python3
"""Post the L.A.B. Simulator's reply onto a discussion thread.

Split out of the workflow for two reasons. It is testable, and — more importantly — it is the
job that *holds a token*, so it should be a file somebody can read rather than forty lines of
YAML nobody re-reads after it works once.

Everything it posts was produced by a job that ran a stranger's Python. It therefore treats its
own input as untrusted and sanitises before posting: see `sanitise`.

  python scripts/discussion_bot.py --node-id D_xxx --body-file reply.md --mode grade
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import graphql  # noqa: E402

MARKER = "<!-- labsim-bot -->"
MAX_BODY = 60_000                      # GitHub's limit is 65,536; leave room for the wrapper

COMMENTS_Q = """
query($id:ID!){
  node(id:$id){ ... on Discussion {
    id number title
    comments(last:60){ nodes { id body author { login } } }
  } }
}"""

ADD_M = """
mutation($id:ID!,$body:String!){
  addDiscussionComment(input:{discussionId:$id,body:$body}){ comment { id url } }
}"""

UPDATE_M = """
mutation($id:ID!,$body:String!){
  updateDiscussionComment(input:{commentId:$id,body:$body}){ comment { id url } }
}"""

MENTION = re.compile(r"(?<![\w`])@([A-Za-z0-9][A-Za-z0-9-]{0,38})")
HTML_COMMENT = re.compile(r"<!--(.*?)-->", re.S)
ALLOWED_COMMENT = re.compile(r"^\s*labsim[-:]", re.S)


def sanitise(body: str) -> str:
    """Make a reply safe to post under the repository's own identity.

    The body is written by a job that executed somebody else's code. That job holds no token and
    no secrets, which is the actual defence; this is the second line, and it is about
    *impersonation* rather than access — a comment posted by `github-actions[bot]` carries the
    repository's authority, and arbitrary markdown under that identity is worth a few lines to
    prevent.

    Three things go:
      * `@mentions`, which would let a submission ping arbitrary people from the repo's account
      * HTML comments that are not ours, which is where a payload would hide from a reader
      * anything past the length cap, which is also how you avoid a 65k API error at 3am
    """
    body = MENTION.sub(lambda m: f"`@{m.group(1)}`", body)
    body = HTML_COMMENT.sub(
        lambda m: m.group(0) if ALLOWED_COMMENT.match(m.group(1)) or
        m.group(1).strip() == "labsim-bot" else "", body)
    if MARKER not in body:
        body = MARKER + "\n\n" + body
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY] + "\n\n…truncated. Run it locally for the full output: "\
                                 "`python -m labsim check <unit>`."
    return body


BOT_LOGINS = {"github-actions", "github-actions[bot]"}


def existing_bot_comment(node_id: str) -> str | None:
    data = graphql(COMMENTS_Q, {"id": node_id})
    for node in reversed(data["node"]["comments"]["nodes"]):
        author = (node.get("author") or {}).get("login", "")
        # GraphQL returns `github-actions`; REST returns `github-actions[bot]`. Testing only
        # the suffix meant the standing verdict was never found, so every re-grade appended a
        # new comment instead of updating the one already there.
        if MARKER in (node.get("body") or "") and author in BOT_LOGINS:
            return node["id"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node-id", required=True)
    ap.add_argument("--body-file", required=True)
    ap.add_argument("--mode", default="grade",
                    choices=["grade", "append"],
                    help="grade edits the standing verdict in place; append adds a new comment")
    args = ap.parse_args()

    raw = Path(args.body_file).read_text()
    if not raw.strip():
        print("nothing to post")
        return 0
    body = sanitise(raw)

    # A grade is a verdict and there should be exactly one of it on a thread — a fresh comment
    # for every edit turns a thread into a changelog nobody reads. A hint is a conversation and
    # accumulates, because the sequence of hints somebody needed is the interesting part.
    if args.mode == "grade":
        comment_id = existing_bot_comment(args.node_id)
        if comment_id:
            out = graphql(UPDATE_M, {"id": comment_id, "body": body})
            print("updated", out["updateDiscussionComment"]["comment"]["url"])
            return 0
    out = graphql(ADD_M, {"id": args.node_id, "body": body})
    print("posted", out["addDiscussionComment"]["comment"]["url"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
