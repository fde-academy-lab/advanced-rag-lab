#!/usr/bin/env python3
"""Resolve every relative link in every Markdown file and report the ones that miss.

Relative links are the ones that break silently. A moved file leaves the old link rendering
as ordinary blue text that 404s only when somebody clicks it, and GitHub will not tell you.
External URLs are checked by the link-check workflow instead; this is the offline half.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^)\s]+?)(#[^)\s]*)?\)')

# GitHub resolves ../../<repo-surface> relative to the *repository*, not the file tree, so
# ../../discussions/categories/q-a is a working link that no filesystem check can confirm.
# Using it is the point: it survives a fork and a rename, unlike a hardcoded owner/repo URL.
GITHUB_SURFACES = ("discussions", "issues", "pulls", "projects", "wiki", "releases",
                   "actions", "milestones", "labels", "security", "settings", "compare",
                   "blob", "tree", "commits")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".ruff_cache", ".pytest_cache"}
# Templates are copied into a cohort repository and filled in there; their links point at
# files that do not exist until then (`docs/11-cohort/schedule.md`, `../../../PATH`). Checking
# them here would only ever report the placeholders. tests/test_cohort_kit.py checks the kit.
SKIP_PREFIXES = (("cohort-kit", "templates"),)
ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()


def markdown_files():
    for p in sorted(ROOT.rglob("*.md")):
        rel = p.relative_to(ROOT).parts
        if any(d in p.parts for d in SKIP_DIRS) or any(rel[:len(x)] == x for x in SKIP_PREFIXES):
            continue
        yield p


def tracked_paths() -> set[str] | None:
    """Everything git tracks, as repo-relative posix paths.

    A link is checked against git rather than the filesystem because an **empty directory is
    not tracked**. It exists on the machine that made it and does not exist in a fresh clone,
    so a link to it passes locally and 404s on GitHub — which is exactly how this check passed
    here and failed in CI.
    """
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                             capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None  # not a git repo; fall back to the filesystem
    return {p for p in out.split("\0") if p}


def main() -> int:
    tracked = tracked_paths()
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
                continue
            if tracked is None:
                continue
            rel = resolved.relative_to(ROOT).as_posix()
            if rel == ".":
                continue  # the repository root, which always exists
            if resolved.is_dir():
                # A directory with nothing tracked under it does not exist in a clone.
                if not any(t == rel or t.startswith(rel + "/") for t in tracked):
                    broken.append((p.relative_to(ROOT), target + "  (empty — git tracks no file "
                                                               "here, so it 404s in a clone)"))
            elif rel not in tracked:
                broken.append((p.relative_to(ROOT), target + "  (untracked)"))
    for src, target in broken:
        print(f"BROKEN  {src}  →  {target}")
    print(f"\n{checked} relative links checked, {len(broken)} broken")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
