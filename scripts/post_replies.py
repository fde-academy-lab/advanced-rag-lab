#!/usr/bin/env python3
"""Post queued discussion replies with the Actions token, then delete the queue file.

    python scripts/post_replies.py .github/pending-replies/discussion-90.json

Why a queue file and a workflow: a Claude Code session's token reads Discussions but cannot
write them, and the repository's convention is that github-actions[bot] posts on the
maintainers' behalf. A reviewer writes the replies into JSON, merges it, and the Post replies
workflow does the posting with `replyToId` so each reply threads under the submission it is
about. The file is deleted by the workflow once every reply is posted, so nothing posts twice.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gh import graphql  # noqa: E402

REPLY_M = """
mutation($discussion: ID!, $reply: ID!, $body: String!) {
  addDiscussionComment(input: {discussionId: $discussion, replyToId: $reply, body: $body}) {
    comment { id url }
  }
}
"""

# Every reply the queue posts carries a hidden marker naming the queue entry, and existing
# replies under a parent are read before posting. Main is a protected branch, so the
# dequeue commit below can be refused; the marker is what makes a re-run harmless.
POSTED_Q = """
query($discussion: ID!) {
  node(id: $discussion) { ... on Discussion {
    comments(first: 100) { nodes { id replies(first: 100) { nodes { body } } } }
  } }
}
"""


def marker(queue: dict, r: dict) -> str:
    return f"<!-- post-replies:{queue['discussion']}:{r.get('parent_comment')} -->"


def already_posted(queue: dict) -> dict[str, set[str]]:
    """parent comment node id -> the markers found in its existing replies."""
    node = graphql(POSTED_Q, {"discussion": queue["discussion_id"]})["node"]
    out: dict[str, set[str]] = {}
    for c in node["comments"]["nodes"]:
        found = set()
        for reply in c["replies"]["nodes"]:
            for line in reply["body"].splitlines():
                if line.startswith("<!-- post-replies:") and line.endswith("-->"):
                    found.add(line.strip())
        out[c["id"]] = found
    return out


def post(path: Path) -> list[str]:
    queue = json.loads(path.read_text())
    done = already_posted(queue)
    urls = []
    for r in queue["replies"]:
        mark = marker(queue, r)
        if mark in done.get(r["reply_to"], set()):
            print(f"already posted under {r.get('parent_comment')}; skipped")
            continue
        out = graphql(REPLY_M, {"discussion": queue["discussion_id"], "reply": r["reply_to"],
                                "body": f"{r['body'].rstrip()}\n\n{mark}"})
        urls.append(out["addDiscussionComment"]["comment"]["url"])
        print(f"posted reply to {r.get('parent_comment')}: {urls[-1]}")
    return urls


def main() -> int:
    queue_dir = HERE.parent / ".github" / "pending-replies"
    paths = [Path(p) for p in sys.argv[1:]] or sorted(queue_dir.glob("*.json"))
    if not paths:
        print("nothing queued")
        return 0
    for p in paths:
        post(p)
        p.unlink()
        print(f"removed {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
