#!/usr/bin/env python3
"""Copy wiki/ into a checkout of the wiki repository, rewriting links for the wiki's URL rules.

    python scripts/wiki_sync.py /path/to/wiki-checkout [--dry-run]

Pages are written in the repository as ordinary markdown so the link checker and the tests can
hold them to the same rules as every other document: a link to another wiki page is
`[text](Page-Name.md)`. GitHub's wiki serves pages at `/wiki/Page-Name`, so the `.md` is
stripped on the way out. Links to repository files are absolute URLs already, because the wiki
is a separate site and a relative path would break there.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "wiki"
LINK = re.compile(r"\]\(([A-Za-z0-9][A-Za-z0-9_-]*)\.md(#[^)]*)?\)")


def rewrite(text: str) -> str:
    """`[x](Page.md)` and `[x](Page.md#anchor)` become `[x](Page)` and `[x](Page#anchor)`."""
    return LINK.sub(lambda m: f"]({m.group(1)}{m.group(2) or ''})", text)


def sync(dest: Path, dry: bool = False) -> list[str]:
    written = []
    for page in sorted(SRC.glob("*.md")):
        out = dest / page.name
        text = rewrite(page.read_text())
        if out.exists() and out.read_text() == text:
            continue
        written.append(page.name)
        if not dry:
            out.write_text(text)
    for extra in sorted(SRC.glob("*")):
        if extra.is_dir() and not dry:
            shutil.copytree(extra, dest / extra.name, dirs_exist_ok=True)
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dest")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    changed = sync(Path(args.dest), args.dry_run)
    print(f"{'would write' if args.dry_run else 'wrote'} {len(changed)} page(s): "
          + ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
