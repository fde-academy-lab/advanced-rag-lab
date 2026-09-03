#!/usr/bin/env python3
"""The Codespaces surface, checked for the drift it is prone to.

Three things rot here and none of them is caught by anything else:

  * `tasks.json` hard-codes the unit list in a pick-list. Add a unit and the menu is stale,
    silently, until somebody notices their unit is missing from the palette.
  * `devcontainer.json` and `.vscode/extensions.json` recommend extensions separately. They
    drift, and the Codespace ends up with a different editor from the local dev container.
  * `devcontainer.json` names shell scripts. Rename one and the Codespace fails on first boot
    with a message nobody sees until a learner reports it.

Both files are JSONC — comments are legal in devcontainer.json and .vscode/*.json, and the
comments in them are load-bearing explanations, so this strips rather than forbids them.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
def strip_comments(text: str) -> str:
    """Remove // and /* */ comments that are not inside a string.

    A regex is not enough here: the comments in these files contain quotes and colons
    (`// "don't look" is a weak defence`, `// see https://…`), and every cheap pattern either
    truncates on the quote or eats the URL. Nine lines of state machine, no dependency.
    """
    out, i, n = [], 0, len(text)
    in_string = escaped = False
    while i < n:
        ch = text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i)
            if i == -1:
                break
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def load_jsonc(path: Path) -> dict:
    text = strip_comments(path.read_text())
    text = re.sub(r",(\s*[}\]])", r"\1", text)      # trailing commas are legal in JSONC
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path.relative_to(ROOT)} does not parse after comment stripping: "
                         f"{exc}") from exc


def unit_ids() -> list[str]:
    sys.path.insert(0, str(ROOT / "lab-simulator"))
    from labsim.registry import all_units
    return [u.uid for u in all_units()]


def main() -> int:
    problems: list[str] = []
    dev = load_jsonc(ROOT / ".devcontainer" / "devcontainer.json")
    tasks = load_jsonc(ROOT / ".vscode" / "tasks.json")
    exts = load_jsonc(ROOT / ".vscode" / "extensions.json")

    for key in ("onCreateCommand", "postAttachCommand"):
        cmd = dev.get(key, "")
        for token in re.findall(r"\.devcontainer/\S+\.sh", cmd):
            script = ROOT / token
            if not script.exists():
                problems.append(f"devcontainer.json {key} runs {token}, which does not exist")
            elif not script.stat().st_mode & 0o111:
                problems.append(f"{token} is not executable — the Codespace will fail to boot")

    dev_exts = set(dev.get("customizations", {}).get("vscode", {}).get("extensions", []))
    rec_exts = set(exts.get("recommendations", []))
    if dev_exts != rec_exts:
        only_dev = ", ".join(sorted(dev_exts - rec_exts)) or "—"
        only_rec = ", ".join(sorted(rec_exts - dev_exts)) or "—"
        problems.append("extension lists have drifted: devcontainer-only "
                        f"[{only_dev}], extensions.json-only [{only_rec}]")

    known = set(unit_ids())
    listed = set()
    for inp in tasks.get("inputs", []):
        if inp.get("id") != "unit":
            continue
        for option in inp.get("options", []):
            value = option["value"] if isinstance(option, dict) else option
            listed.add(value)
    if listed != known:
        missing = ", ".join(sorted(known - listed)) or "—"
        stale = ", ".join(sorted(listed - known)) or "—"
        problems.append(f"tasks.json unit pick-list is stale: missing [{missing}], "
                        f"no longer exist [{stale}]")

    if problems:
        print("Codespaces surface has drifted:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"devcontainer + tasks OK · {len(known)} units in the pick-list · "
          f"{len(dev_exts)} extensions, consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
