"""Reading a brief in a terminal, and pulling its hints out one at a time.

Two jobs that turn out to be the same job.

A brief is markdown with `<details><summary>Hint N — …</summary>` blocks. Cat it and you get
raw markup and every hint spoiled at once; the `<details>` collapse that makes hints progressive
on GitHub does nothing in a terminal. So the renderer strips the hints out and leaves a pointer,
and `hints()` hands them back one at a time — which is also exactly what the Discussions bot
needs for `/hint`, so both surfaces spend the same code and cannot drift.

Deliberately not a general markdown renderer. It handles what the briefs actually contain and
leaves the rest alone, because a half-correct renderer that mangles a table is worse than one
that prints it.
"""
from __future__ import annotations

import dataclasses
import re
import shutil
import textwrap

BOLD, DIM, RESET = "\033[1m", "\033[90m", "\033[0m"
CYAN, YELLOW, GREEN, UNDER = "\033[36m", "\033[33m", "\033[32m", "\033[4m"

DETAILS = re.compile(
    r"<details>\s*<summary>(?P<summary>.*?)</summary>(?P<body>.*?)</details>",
    re.S | re.I)
FENCE = re.compile(r"^```(\w*)\s*$")


@dataclasses.dataclass(frozen=True)
class Hint:
    number: int
    summary: str
    body: str

    def render(self) -> str:
        return f"{BOLD}{self.summary}{RESET}\n\n{textwrap.dedent(self.body).strip()}"


def hints(markdown: str) -> list[Hint]:
    """Every `<details>` block in order. The summary is the teaser, the body is the spend."""
    out = []
    for i, m in enumerate(DETAILS.finditer(markdown), start=1):
        summary = re.sub(r"\s+", " ", m.group("summary")).strip()
        out.append(Hint(i, summary, m.group("body")))
    return out


def strip_hints(markdown: str) -> str:
    """The brief with its hint bodies removed and the summaries left as a menu."""
    def swap(m: re.Match) -> str:
        summary = re.sub(r"\s+", " ", m.group("summary")).strip()
        return f"@@HINT@@{summary}"
    return DETAILS.sub(swap, markdown)


def _inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", lambda m: f"{BOLD}{m.group(1)}{RESET}", text)
    text = re.sub(r"(?<!\w)`([^`]+)`", lambda m: f"{CYAN}{m.group(1)}{RESET}", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  lambda m: f"{UNDER}{m.group(1)}{RESET} {DIM}{m.group(2)}{RESET}", text)
    return text


def render(markdown: str, width: int | None = None, *, colour: bool = True) -> str:
    """The brief, wrapped and coloured, with hints replaced by how to ask for them."""
    width = width or min(shutil.get_terminal_size((92, 24)).columns - 4, 94)
    lines: list[str] = []
    in_fence = False
    hint_n = 0
    para: list[str] = []

    def flush() -> None:
        # Briefs are hard-wrapped in the source at about 98 columns. Wrapping each source line
        # separately reflows every paragraph into ragged half-lines, so join first.
        if para:
            joined = " ".join(x.strip() for x in para)
            lines.extend(textwrap.wrap(_inline(joined), width, initial_indent="  ",
                                       subsequent_indent="  ") or [""])
            para.clear()

    for raw in strip_hints(markdown).splitlines():
        fence = FENCE.match(raw)
        if fence:
            flush()
            in_fence = not in_fence
            lines.append(f"  {DIM}{'─' * (width - 2)}{RESET}" if in_fence else
                         f"  {DIM}{'─' * (width - 2)}{RESET}")
            continue
        if in_fence:
            lines.append(f"  {DIM}│{RESET} {raw}")
            continue
        if raw.startswith("@@HINT@@"):
            flush()
            hint_n += 1
            summary = raw[len("@@HINT@@"):]
            lines.append(f"  {YELLOW}◆{RESET} {summary}")
            continue
        if raw.startswith("#"):
            flush()
            level = len(raw) - len(raw.lstrip("#"))
            text = raw.lstrip("# ").strip()
            lines.append("")
            lines.append(f"{BOLD}{text}{RESET}" if level <= 2 else f"{BOLD}{DIM}{text}{RESET}")
            if level <= 2:
                lines.append(f"{DIM}{'─' * min(len(text), width)}{RESET}")
            continue
        if raw.startswith("|") or raw.startswith(">"):
            flush()
            lines.append("  " + _inline(raw))
            continue
        if not raw.strip():
            flush()
            lines.append("")
            continue
        bullet = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", raw)
        if bullet:
            flush()
            indent, mark, rest = bullet.groups()
            wrapped = textwrap.wrap(_inline(rest), width - len(indent) - 4) or [""]
            lines.append(f"{indent}  {mark} {wrapped[0]}")
            lines.extend(f"{indent}    {w}" for w in wrapped[1:])
            continue
        para.append(raw)

    flush()
    text = "\n".join(lines)
    if hint_n:
        text += (f"\n\n  {YELLOW}{hint_n} hint(s) available.{RESET} "
                 f"{DIM}They are collapsed on purpose — spend one when you are stuck, not "
                 f"before.{RESET}")
    if not colour:
        text = re.sub(r"\033\[[0-9;]*m", "", text)
    return text
