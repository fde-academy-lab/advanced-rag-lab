#!/usr/bin/env python3
"""Resolve every relative link in every Markdown file and report the ones that miss.

Relative links are the ones that break silently. A moved file leaves the old link rendering
as ordinary blue text that 404s only when somebody clicks it, and GitHub will not tell you.
External URLs are checked by the link-check workflow instead; this is the offline half.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+?)(#[^)\s]*)?\)')

# GitHub resolves ../../<repo-surface> relative to the *repository*, not the file tree, so
# ../../discussions/categories/q-a is a working link that no filesystem check can confirm.
# Using it is the point: it survives a fork and a rename, unlike a hardcoded owner/repo URL.
GITHUB_SURFACES = ("discussions", "issues", "pulls", "projects", "wiki", "releases",
                   "actions", "milestones", "labels", "security", "settings", "compare",
                   "blob", "tree", "commits")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".ruff_cache", ".pytest_cache"}
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()


def markdown_files():
    for p in sorted(ROOT.rglob("*.md")):
        if not any(d in p.parts for d in SKIP_DIRS):
            yield p


def main() -> int:
    broken, checked = [], 0
    for p in markdown_files():
        for m in LINK.finditer(p.read_text()):
            target = m.group(1)
            if target.startswith(("http://", "https://", "mailto:", "tel:", "#")):
                continue
            bare = target.lstrip("./")
            if target.startswith("../../") and bare.split("/")[0] in GITHUB_SURFACES:
                continue
            checked += 1
            resolved = (p.parent / target).resolve()
            if not resolved.exists():
                broken.append((p.relative_to(ROOT), target))
    for src, target in broken:
        print(f"BROKEN  {src}  →  {target}")
    print(f"\n{checked} relative links checked, {len(broken)} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
