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


def post(path: Path) -> list[str]:
    queue = json.loads(path.read_text())
    urls = []
    for r in queue["replies"]:
        out = graphql(REPLY_M, {"discussion": queue["discussion_id"], "reply": r["reply_to"],
                                "body": r["body"]})
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
