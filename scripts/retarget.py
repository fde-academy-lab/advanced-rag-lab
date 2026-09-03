#!/usr/bin/env python3
"""Point this repository at a different owner, repository name, or Python package.

Nothing in the tree hardcodes an identity permanently. A handful of things genuinely cannot be
relative — CI badge URLs, the clone command, CODEOWNERS handles, CITATION.cff, the packaging
metadata — so they carry a placeholder that this script rewrites in one pass.

    python scripts/retarget.py --owner your-handle
    python scripts/retarget.py --owner your-org --repo my-rag-lab --package myrag

With no flags it reads `git remote get-url origin` and retargets to whatever that points at,
which is what `setup_github.py` calls before it pushes.

Idempotent. The current identity lives in `.identity.json`; every run rewrites the old values
to the new ones and updates that file, so running it twice is a no-op and running it a
fourth time to rename again works exactly like the first.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IDENTITY = ROOT / ".identity.json"
DEFAULT = {"owner": "OWNER", "repo": "advanced-rag-lab", "package": "raglab"}

SKIP_DIRS = {".git", "__pycache__", ".ruff_cache", ".ipynb_checkpoints", ".venv",
             "node_modules", ".pytest_cache", "dist", "build"}
# This script and the identity file both contain the names as data. Rewriting them from
# inside the sweep mangles this file's own examples and defaults; the identity file is
# rewritten deliberately at the end instead.
SKIP_FILES = {"scripts/retarget.py", ".identity.json"}
TEXT_SUFFIXES = {".py", ".ipynb", ".md", ".toml", ".yml", ".yaml", ".cff", ".txt", ".cfg",
                 ".json", ".html", ".sh", ".in", ""}


def load_identity() -> dict:
    if IDENTITY.exists():
        return {**DEFAULT, **json.loads(IDENTITY.read_text())}
    return dict(DEFAULT)


def detect_from_git() -> tuple[str | None, str | None]:
    """Read owner/repo off origin. Handles https, ssh and scp-style remotes."""
    try:
        url = subprocess.run(["git", "-C", str(ROOT), "remote", "get-url", "origin"],
                             capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None, None
    m = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    return (m.group(1), m.group(2)) if m else (None, None)


def text_files():
    for p in ROOT.rglob("*"):
        if not p.is_file() or any(d in p.parts for d in SKIP_DIRS):
            continue
        if p.relative_to(ROOT).as_posix() in SKIP_FILES:
            continue
        if p.suffix.lower() in TEXT_SUFFIXES or p.name in {"Makefile", "CODEOWNERS", "LICENSE"}:
            yield p


def rewrite(pairs, dry: bool) -> dict[str, int]:
    """Apply (old, new) string pairs across every text file. Longest-first so that
    'owner/repo' is consumed before the bare 'owner' that is a prefix of it."""
    pairs = [(a, b) for a, b in pairs if a and b and a != b]
    pairs.sort(key=lambda ab: -len(ab[0]))
    touched: dict[str, int] = {}
    for p in text_files():
        try:
            s = p.read_text()
        except (UnicodeDecodeError, ValueError):
            continue
        hits = sum(s.count(a) for a, _ in pairs)
        if not hits:
            continue
        if not dry:
            for a, b in pairs:
                s = s.replace(a, b)
            p.write_text(s)
        touched[str(p.relative_to(ROOT))] = hits
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--owner", help="GitHub user or org (default: read from origin)")
    ap.add_argument("--repo", help="repository name (default: read from origin)")
    ap.add_argument("--package", help="Python package name, if you want it renamed too")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    old = load_identity()
    git_owner, git_repo = detect_from_git()
    new = {
        "owner": args.owner or git_owner or old["owner"],
        "repo": args.repo or git_repo or old["repo"],
        "package": args.package or old["package"],
    }

    if new == old:
        print(f"Already targeting {new['owner']}/{new['repo']} "
              f"(package {new['package']}) — nothing to do.")
        return 0

    print(f"  owner    {old['owner']}  →  {new['owner']}")
    print(f"  repo     {old['repo']}  →  {new['repo']}")
    print(f"  package  {old['package']}  →  {new['package']}")
    if args.dry_run:
        print("  (dry run)")

    # Order matters, and rewrite() sorts longest-first to enforce it: the qualified
    # "owner/repo" pair must be rewritten before the bare owner handle that it contains.
    pairs = [
        (f"{old['owner']}/{old['repo']}", f"{new['owner']}/{new['repo']}"),
        (f"@{old['owner']}", f"@{new['owner']}"),
        (f"users/{old['owner']}/projects", f"users/{new['owner']}/projects"),
        (old["package"], new["package"]),
    ]
    # A bare repo name is too short to rewrite blindly (it may also appear as prose and,
    # by default, as the package name). Only touch it where it is unambiguous.
    if old["repo"] != new["repo"] and old["repo"] != old["package"]:
        pairs.append((old["repo"], new["repo"]))

    touched = rewrite(pairs, args.dry_run)
    for f, n in sorted(touched.items()):
        print(f"    {n:3d}  {f}")
    print(f"\n  {len(touched)} files, {sum(touched.values())} replacements")

    pkg_dir = ROOT / old["package"]
    if new["package"] != old["package"] and pkg_dir.is_dir():
        dest = ROOT / new["package"]
        print(f"  package directory  {old['package']}/  →  {new['package']}/")
        if not args.dry_run:
            res = subprocess.run(["git", "-C", str(ROOT), "mv", old["package"], new["package"]],
                                 capture_output=True, text=True)
            if res.returncode != 0:
                pkg_dir.rename(dest)

    if not args.dry_run:
        IDENTITY.write_text(json.dumps(new, indent=2) + "\n")
        print(f"\nDone. Re-run `make test` before pushing — the package import path "
              f"is now `import {new['package']}`."
              if new["package"] != old["package"] else "\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
