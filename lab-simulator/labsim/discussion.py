"""The Discussions bridge: submissions in, graded replies out.

Why a submission flow lives in Discussions at all, when `labsim check` exists locally: most
people who will ever open this repository will not clone it. They will read a thread. A thread
where somebody posted a wrong answer, a bot said which check caught it, a peer said why, and the
author came back with the fix is worth more to the next reader than a green tick on a fork they
cannot see — and it is the only artefact of a solve that survives the person who solved it.

Two shapes of input, both handled here so the workflow file stays free of parsing:

  a submission   a new discussion in the simulator category, usually from the category form
  a command      a comment on that thread: /check, /hint, /solution, /status

The parsing is deliberately forgiving. A form gives `### Field` sections; somebody who ignores
the form and pastes a code block under a title of "R1 attempt" gets graded anyway, because
refusing to read a submission on a formatting technicality is exactly the behaviour that makes
people stop submitting.
"""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from .brief import hints as brief_hints
from .grader import Result, attempt_dir
from .registry import all_units, by_id, unlocked

MARKER = "<!-- labsim-bot -->"
UID_IN_TITLE = re.compile(r"\b([A-Z]{1,2}\d{1,2})\b")
SECTION = re.compile(r"^###\s+(?P<label>.+?)\s*$", re.M)
FENCE = re.compile(r"```(?P<lang>[\w.]*)\s*\n(?P<code>.*?)```", re.S)
# Anywhere on a line, not only at the start: people write "any ideas? /hint" and refusing that
# on a technicality is the same mistake as refusing a submission for missing the form.
COMMAND = re.compile(r"(?:^|\s)/(check|hint|solution|status|help)\b[ \t]*(\d+)?", re.M | re.I)

# Which form field feeds which file in the attempt directory.
#
# Matched against the field's label in two passes, and the order is the point. A label that
# literally names the file wins; only then does the loose keyword pass run, and it skips labels
# that are asking for prose.
#
# The form's first textarea is "Your approach, before the code". Under a single loose pass that
# label contains "code" and captures any fenced block in it as the learner's solution — so
# somebody who sketches an approach in code, or pastes their answer one field too early, gets a
# grade for a file they did not submit.
FILENAMES = ("solution.py", "decision.yaml", "measurement.md")
FIELD_TO_FILE = {
    "solution": "solution.py",
    "code": "solution.py",
    "decision": "decision.yaml",
    "measurement": "measurement.md",
    "note": "measurement.md",
}
PROSE_FIELDS = ("approach", "surprised", "reflect", "before you post", "which unit")

# GitHub renders an untouched optional textarea as this literal string rather than omitting the
# section. Taken at face value it becomes a file: a P1 attempt that left the note blank was
# graded against a measurement.md whose entire contents were "_No response_".
NO_RESPONSE = re.compile(r"^\s*_?\s*no response\s*_?\s*$", re.I)


@dataclasses.dataclass
class Submission:
    unit_id: str | None
    files: dict[str, str]
    reflection: str = ""

    @property
    def usable(self) -> bool:
        return bool(self.unit_id) and bool(self.files)


def _sections(body: str) -> dict[str, str]:
    """`### Label` blocks from a discussion form, lowercased keys."""
    out, marks = {}, list(SECTION.finditer(body))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        out[m.group("label").strip().lower()] = body[m.end():end].strip()
    return out


def _target_file(label: str) -> str | None:
    """Which attempt file a form field feeds, or None when the field is prose."""
    low = label.lower()
    for filename in FILENAMES:
        if filename in low:
            return filename
    if any(word in low for word in PROSE_FIELDS):
        return None
    for key, filename in FIELD_TO_FILE.items():
        if key in low:
            return filename
    return None


def _first_fence(text: str, *langs: str) -> str | None:
    for m in FENCE.finditer(text):
        if not langs or (m.group("lang") or "").lower() in langs:
            return m.group("code").rstrip() + "\n"
    return None


def parse_submission(title: str, body: str) -> Submission:
    unit_id = None
    for token in UID_IN_TITLE.findall(title or ""):
        if by_id(token):
            unit_id = by_id(token).uid
            break

    sections = _sections(body or "")
    files: dict[str, str] = {}
    reflection = ""

    for label, text in sections.items():
        if NO_RESPONSE.match(text or ""):
            continue                    # an untouched optional field, not an empty submission
        if unit_id is None and ("unit" in label or "which" in label):
            for token in UID_IN_TITLE.findall(text.upper()):
                if by_id(token):
                    unit_id = by_id(token).uid
                    break
        filename = _target_file(label)
        if filename:
            code = _first_fence(text)
            # A measurement note is prose, so it may arrive without a fence at all.
            if code is None and filename.endswith(".md") and text.strip():
                code = text.strip() + "\n"
            if code:
                files[filename] = code
        if "surprised" in label or "reflect" in label:
            reflection = text.strip()

    # Not a form: fall back to scanning the whole body, so somebody who ignores the template
    # and pastes a code block under a title of "R1 attempt" is still graded.
    #
    # Only when the post is not form-shaped, though. A form that names its file fields has
    # already said which block is which, and re-scanning would defeat that — the approach field
    # comes first, so a learner sketching in code would be graded on the sketch.
    form_like = any(_target_file(label) for label in sections)
    if not files and not form_like:
        for filename, langs in (("solution.py", ("python", "py")),
                                ("decision.yaml", ("yaml", "yml"))):
            code = _first_fence(body or "", *langs)
            if code:
                files[filename] = code

    return Submission(unit_id, files, reflection)


def materialise(sub: Submission) -> Path:
    """Write the submitted files into the attempt directory the grader reads."""
    unit = by_id(sub.unit_id or "")
    if unit is None:
        raise ValueError(f"no unit {sub.unit_id!r}")
    dest = attempt_dir(unit)
    dest.mkdir(parents=True, exist_ok=True)
    for name, text in sub.files.items():
        (dest / name).write_text(text)
    return dest


def parse_command(body: str) -> tuple[str, int | None] | None:
    # Strip fenced code first. A pasted diff containing `/check` in a path is not a command,
    # and a bot that thinks it is will grade somebody's thread every time they quote a file.
    text = FENCE.sub("", body or "")
    m = COMMAND.search(text)
    if not m:
        return None
    return m.group(1).lower(), int(m.group(2)) if m.group(2) else None


# ------------------------------------------------------------------ rendering


def _machine_tag(unit_id: str, result: Result | None) -> str:
    """A line the weekly digest tallies. Comment syntax, so a reader never sees it.

    The digest asks which *check* fails most often across everybody's attempts, and that answer
    is feedback on the unit rather than on the learner: a check that nearly everyone trips is
    either the lesson or a badly written brief, and the histogram is how you tell.
    """
    if result is None:
        return f"<!-- labsim:{unit_id}:no-result -->"
    state = "pass" if result.passed else "fail"
    names = ";".join(sorted(result.failures)[:6]).replace("-->", "")
    return f"<!-- labsim:{unit_id}:{state}:{names} -->"


def render_grade(unit_id: str, result: Result, *, repo: str = "") -> str:
    unit = by_id(unit_id)
    lines = [MARKER, _machine_tag(unit_id, result), ""]
    head = "cleared" if result.passed else "not yet"
    lines.append(f"## {'✅' if result.passed else '🔴'} `{unit.uid}` · {unit.title} — **{head}**")
    lines.append("")
    lines.append(f"`{unit.mode}` · {unit.difficulty} · {unit.track} · graded in "
                 f"{result.duration:.1f}s on a clean checkout")
    lines.append("")

    if result.decision_ok is not None:
        lines.append(f"- {'✅' if result.decision_ok else '❌'} **decision** — filled, and the "
                     "falsifier names an observation rather than the conclusion")
    if result.checks_ok is not None:
        lines.append(f"- {'✅' if result.checks_ok else '❌'} **checks**")
    for desc, ok, value in result.bars:
        shown = f"{value:.4f}" if value is not None else "not reported"
        lines.append(f"- {'✅' if ok else '❌'} **bar** `{desc}` — got `{shown}`")
    lines.append("")

    if result.failures:
        lines.append("**Checks that failed**")
        lines.append("")
        lines.extend(f"- `{f}`" for f in result.failures)
        lines.append("")
    if result.messages:
        lines.append("<details><summary>What the grader said</summary>")
        lines.append("")
        lines.append("```")
        lines.extend(m for m in result.messages if m.strip())
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    if result.passed:
        sol = f"lab-simulator/units/{unit.directory.name}/SOLUTION.md"
        lines.append(f"Post `/solution` on this thread for the worked answer — including the two "
                     f"things we got wrong first. It lives at `{sol}`.")
        nxt = [u.uid for u in unlocked({unit.uid}) if unit.uid in u.prereqs]
        if nxt:
            lines.append("")
            lines.append(f"Unlocked: {', '.join(f'`{x}`' for x in nxt)}")
    else:
        lines.append("Stuck? `/hint` gives you the next hint from the brief, one at a time. "
                     "Edit your post and the bot re-grades, or comment `/check` to force a run.")
    lines.append("")
    lines.append(_footer(repo))
    return "\n".join(lines)


def render_hint(unit_id: str, n: int | None) -> str:
    unit = by_id(unit_id)
    if unit is None:
        return f"{MARKER}\n\nNo unit `{unit_id}` — say which one you are on."
    items = brief_hints((unit.directory / "BRIEF.md").read_text())
    if not items:
        return (f"{MARKER}\n\n`{unit.uid}` ships no hints. That is deliberate for a unit this "
                "size — the brief is the hint. Post what you tried and somebody will read it.")
    index = (n or 1)
    if index > len(items):
        return (f"{MARKER}\n\n`{unit.uid}` has {len(items)} hints and you asked for {index}. "
                f"The last one is spent, so the next move is to post your attempt and let the "
                f"checks tell you which promise it breaks.")
    hint = items[index - 1]
    tail = (f"\n\n`/hint {index + 1}` for the next one." if index < len(items)
            else "\n\nThat was the last hint.")
    return (f"{MARKER}\n<!-- labsim:{unit.uid}:hint:{index} -->\n\n"
            f"### {unit.uid} · hint {index} of {len(items)}\n\n"
            f"**{hint.summary}**\n\n{hint.body.strip()}{tail}")


def render_solution(unit_id: str, *, passed: bool) -> str:
    unit = by_id(unit_id)
    if unit is None:
        return f"{MARKER}\n\nNo unit `{unit_id}`."
    path = f"lab-simulator/units/{unit.directory.name}/SOLUTION.md"
    if not passed:
        items = brief_hints((unit.directory / "BRIEF.md").read_text())
        return (f"{MARKER}\n\n`{unit.uid}` has not cleared on this thread yet, so the worked "
                f"answer stays closed.\n\nThat is not gatekeeping — reading a solution before "
                f"you have a failing attempt in front of you teaches the answer and not the "
                f"reasoning, and the difference shows up in an interview two months later. "
                + (f"There are {len(items)} hints; `/hint` spends one." if items else
                   "Post what you have and the checks will name the promise it breaks.")
                + f"\n\nIf you want it anyway it has always been in the repository: `{path}`.")
    return (f"{MARKER}\n\n`{unit.uid}` is cleared on this thread. The worked answer, including "
            f"what we got wrong first, is [`{path}`]({path}).\n\n"
            "Worth reading even though you passed: it is written to disagree with plausible "
            "correct answers, not to confirm yours.")


def render_status(unit_id: str | None) -> str:
    rows = []
    for u in all_units():
        mark = "→" if u.uid == unit_id else " "
        rows.append(f"| {mark} | `{u.uid}` | {u.title} | `{u.mode}` | {u.difficulty} | "
                    f"{', '.join(u.prereqs) or '—'} |")
    return (f"{MARKER}\n\n### The pathway\n\n"
            "| | id | unit | mode | difficulty | needs |\n|---|---|---|---|---|---|\n"
            + "\n".join(rows)
            + "\n\nPrerequisites are not bureaucracy: a later unit reuses what an earlier one "
              "built. Locally, `python -m labsim next` picks for you.")


def render_help(repo: str = "") -> str:
    return (f"{MARKER}\n\n### Commands on a simulator thread\n\n"
            "| | |\n|---|---|\n"
            "| `/check` | re-grade the submission in the first post |\n"
            "| `/hint` · `/hint 3` | the next hint from the brief, one at a time |\n"
            "| `/solution` | the worked answer — opens once the thread has cleared |\n"
            "| `/status` | the pathway and where this unit sits in it |\n\n"
            "Editing your first post re-grades it automatically. Nothing here needs a clone: "
            "paste the code in the form and the Action runs it.\n\n" + _footer(repo))


def _footer(repo: str) -> str:
    base = f"https://github.com/{repo}" if repo else ""
    codespace = (f"[Open in Codespaces]({base}/codespaces/new?hide_repo_select=true"
                 f"&ref=main&repo_name=advanced-rag-lab)" if base else "GitHub Codespaces")
    return ("<sub>Graded by `python -m labsim check` on a clean checkout — the same code path "
            f"you would run locally. Want the editor instead of the form? {codespace}, then "
            "`python -m labsim next`.</sub>")
