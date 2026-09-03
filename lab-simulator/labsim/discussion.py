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
COMMAND = re.compile(r"(?:^|\s)/(check|hint|solution|status|help|why|progress)\b"
                     r"[ \t]*([^\n]*)", re.M | re.I)

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
FILENAMES = ("solution.py", "decision.yaml", "measurement.md", "answer.yaml")
FIELD_TO_FILE = {
    "solution": "solution.py",
    "code": "solution.py",
    "decision": "decision.yaml",
    "measurement": "measurement.md",
    "note": "measurement.md",
    "answer": "answer.yaml",
    "prediction": "answer.yaml",
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


def _is_form_label(label: str) -> bool:
    """Is this `###` heading one of the form's own fields, or part of somebody's answer?"""
    low = label.strip().lower()
    return (_target_file(low) is not None
            or any(word in low for word in PROSE_FIELDS))


def _sections(body: str) -> dict[str, str]:
    """`### Label` blocks from a discussion form, lowercased keys.

    Only a heading that names a *form field* starts a new section. Every `###` used to, which
    truncated any field whose content had sub-headings of its own — and a P1 measurement note
    is exactly that: the template it is graded against opens with `### The table`. The note was
    cut off at its first sub-heading and graded on the fragment.
    """
    out, marks = {}, [m for m in SECTION.finditer(body) if _is_form_label(m.group("label"))]
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
    """The first non-empty fenced block, optionally restricted by language.

    Non-empty matters: somebody who opens a fence and pastes nothing into it used to submit an
    empty solution.py, which is a *different* failure from submitting nothing — the unit grades
    it and reports a missing function rather than saying the form field was blank.
    """
    for m in FENCE.finditer(text):
        if langs and (m.group("lang") or "").lower() not in langs:
            continue
        code = m.group("code").rstrip()
        if code.strip():
            return code + "\n"
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
        unit = by_id(unit_id or "")
        yaml_target = "answer.yaml" if unit is not None and unit.needs_answer else "decision.yaml"
        for filename, langs in (("solution.py", ("python", "py")),
                                (yaml_target, ("yaml", "yml"))):
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


def parse_command(body: str) -> tuple[str, str] | None:
    """The first slash command in a comment, with whatever followed it on the line.

    Fences are stripped first so that quoting a file which happens to contain `/check` does
    not run the grader. The argument is returned as text: `/hint 3` gives ("hint", "3") and
    `/why every short span` gives ("why", "every short span"). Callers parse it.
    """
    text = FENCE.sub(" ", body or "")
    hit = COMMAND.search(text)
    if not hit:
        return None
    return hit.group(1).lower(), (hit.group(2) or "").strip()


def hint_index(arg: str) -> int | None:
    """`/hint 3` → 3; `/hint` → None; `/hint please` → None."""
    got = re.match(r"\s*(\d+)", arg or "")
    return int(got.group(1)) if got else None

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
    lines.append(f"{'drill' if unit.is_drill else 'unit'} · `{unit.mode}` · {unit.difficulty} · "
                 f"{unit.track} · ~{unit.minutes} min · graded in {result.duration:.1f}s on a "
                 "clean checkout")
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

    lines.extend(_coaching_block(unit, result, repo))
    lines.append("")
    lines.append(_footer(repo))
    return "\n".join(lines)


def _link(repo: str, path: str) -> str:
    return f"[`{path}`](https://github.com/{repo}/blob/main/{path})" if repo else f"`{path}`"


def _coaching_block(unit, result: Result, repo: str) -> list[str]:
    """The part of the reply that is about the learner rather than about the grader.

    Nothing here is generated. Every sentence comes from the unit's own metadata — `teaches`,
    `on_fail`, `reading`, and the prerequisite graph — written by whoever wrote the check, so
    it can be specific about *this* failure without inventing anything. A reply that names
    the skill behind the check it failed is worth more than one that praises the attempt.
    """
    out: list[str] = []
    if result.passed:
        out.append(f"**What `{unit.uid}` was for.** {_teaches(unit)}")
        out.append("")
        sol = f"lab-simulator/units/{unit.directory.name}/SOLUTION.md"
        out.append(f"Post `/solution` for the worked answer — including what we got wrong first. "
                   f"It lives at {_link(repo, sol)}.")
        nxt = _next_after(unit)
        if nxt:
            out.append("")
            out.append("**Next.** " + " · ".join(
                f"`{u.uid}` {u.title} — {u.mode}, {u.difficulty}, ~{u.minutes} min"
                for u in nxt))
            out.append("")
            out.append("Post a new thread for it in this category; the bot grades it the same way.")
        else:
            out.append("")
            out.append("`/status` shows the whole pathway.")
    else:
        coached = [(f, unit.coach(f)) for f in result.failures]
        named = [(f, c) for f, c in coached if c is not None]
        if named:
            out.append("**What to work on.** One line per check, written by whoever wrote it:")
            out.append("")
            for check, c in named:
                read = f" — read {_link(repo, c.read)}" if c.read else ""
                out.append(f"- `{check}` → {c.work_on}{read}")
            out.append("")
        unnamed = [f for f, c in coached if c is None]
        if unnamed and not named:
            out.append("The failing checks are named above; the brief's *trap table* says what "
                       "each one is guarding against.")
            out.append("")
        out.append("`/hint` gives you the next hint from the brief, one at a time. "
                   "`/why <check name>` explains a single check. Edit your post and the bot "
                   "re-grades, or comment `/check` to force a run.")
    if unit.reading:
        out.append("")
        out.append("**Read next.** " + " · ".join(_link(repo, r) for r in unit.reading))
    return out


def _teaches(unit) -> str:
    items = list(unit.teaches)
    if not items:
        return unit.summary.strip() or "See the brief."
    if len(items) == 1:
        return items[0].capitalize() + "."
    return ", ".join(items[:-1]) + f", and {items[-1]}."


def _next_after(unit) -> list:
    """Units this one unlocks, same track first, drills before units within a track.

    When it unlocks nothing — a drill with no dependants, say — fall back to the other
    starting points on the same track, so the reply never ends in "nothing".
    """
    nxt = [u for u in unlocked({unit.uid}) if unit.uid in u.prereqs]
    if not nxt:
        nxt = [u for u in unlocked({unit.uid})
               if u.uid != unit.uid and u.track == unit.track and not u.prereqs]
    nxt.sort(key=lambda u: (u.track != unit.track, not u.is_drill, u.minutes, u.uid))
    return nxt[:3]


def render_why(unit_id: str, check: str) -> str:
    """`/why <check name>` — one check, explained from the unit's own coaching notes."""
    unit = by_id(unit_id)
    if unit is None:
        return f"{MARKER}\n\nNo unit `{unit_id}`."
    if not check.strip():
        names = [c.matches for c in unit.coaching]
        return (f"{MARKER}\n\n`/why` takes a check name — any distinctive part of it. "
                + (f"`{unit.uid}` has notes for: " + ", ".join(f"`{n}`" for n in names)
                   if names else f"`{unit.uid}` carries no per-check notes yet; the brief's "
                                 "trap table is the place to look."))
    c = unit.coach(check)
    if c is None:
        return (f"{MARKER}\n\nNo note on `{unit.uid}` matches `{check}`. The check names are "
                "in the grader's reply above; `/why` with any distinctive word from one.")
    read = f"\n\nRead: `{c.read}`" if c.read else ""
    return (f"{MARKER}\n<!-- labsim:{unit.uid}:why -->\n\n**`{c.matches}`**\n\n{c.work_on}{read}")


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
        rows.append(f"| {mark} | `{u.uid}` | {u.title} | {'drill' if u.is_drill else 'unit'} | "
                    f"`{u.mode}` | {u.difficulty} | ~{u.minutes} | "
                    f"{', '.join(u.prereqs) or '—'} |")
    drills = sum(1 for u in all_units() if u.is_drill)
    return (f"{MARKER}\n\n### The pathway\n\n"
            "| | id | title | kind | mode | difficulty | min | needs |\n"
            "|---|---|---|---|---|---|---|---|\n"
            + "\n".join(rows)
            + f"\n\n{len(all_units()) - drills} units and {drills} drills. A drill is one idea "
              "in under fifteen minutes; a unit is a real corpus and three gates. Both sit in the "
              "same prerequisite graph, so clearing either unlocks what comes after it. "
              "Locally, `python -m labsim next` picks for you.")


def render_help(repo: str = "") -> str:
    return (f"{MARKER}\n\n### Commands on a simulator thread\n\n"
            "| | |\n|---|---|\n"
            "| `/check` | re-grade the submission in the first post |\n"
            "| `/hint` · `/hint 3` | the next hint from the brief, one at a time |\n"
            "| `/solution` | the worked answer — opens once the thread has cleared |\n"
            "| `/status` | the pathway and where this unit sits in it |\n"
            "| `/why <check name>` | what one failing check is guarding against, in a sentence |\n"
            "| `/progress` | what you have cleared and attempted across this category |\n\n"
            "Editing your first post re-grades it automatically. Nothing here needs a clone: "
            "paste the code in the form and the Action runs it.\n\n" + _footer(repo))


def _footer(repo: str) -> str:
    base = f"https://github.com/{repo}" if repo else ""
    codespace = (f"[Open in Codespaces]({base}/codespaces/new?hide_repo_select=true"
                 f"&ref=main&repo_name=advanced-rag-lab)" if base else "GitHub Codespaces")
    return ("<sub>Graded by `python -m labsim check` on a clean checkout — the same code path "
            f"you would run locally. Want the editor instead of the form? {codespace}, then "
            "`python -m labsim next`.</sub>")
