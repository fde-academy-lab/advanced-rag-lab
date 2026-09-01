"""The cast that appears in seeded discussion threads.

Every seeded post is written by the maintainers and posted from the seeding account. The
names exist so a fifteen-reply thread is readable — you cannot follow who changed their mind
or whose objection landed when every participant is "a cohort member". The disclosure is
carried per-post rather than per-thread, because a reader arriving from a search result lands
mid-thread and never sees the top.

Each persona owns a failure mode as well as a strength. A cast where everyone is competent
teaches nothing about how engineering conversations actually go wrong.
"""
from __future__ import annotations

PERSONAS: dict[str, dict[str, str]] = {
    "priya": {
        "name": "Priya",
        "tag": "backend engineer · 6 yrs · new to retrieval",
        "strength": "precise bug reports with a reproduction",
        "flaw": "optimises before measuring",
    },
    "marcus": {
        "name": "Marcus",
        "tag": "data scientist · strong statistics",
        "strength": "catches the significance error nobody else sees",
        "flaw": "perfectionism as delay",
    },
    "wei": {
        "name": "Wei",
        "tag": "ML engineer · shipped a production RAG",
        "strength": "corrects theory with what actually happened at scale",
        "flaw": "generalises from one company's experience",
    },
    "sofia": {
        "name": "Sofia",
        "tag": "platform engineer · security-minded",
        "strength": "asks the tenancy and permissions question early",
        "flaw": "treats everything as an access-control problem",
    },
    "dan": {
        "name": "Dan",
        "tag": "career-switcher · 18 months in",
        "strength": "asks what everyone else was embarrassed to ask",
        "flaw": "accepts the first confident answer",
    },
    "aarav": {
        "name": "Aarav",
        "tag": "consultant · client-facing",
        "strength": "reframes around what the client will pay for",
        "flaw": "declares things good enough too early",
    },
    "lena": {
        "name": "Lena",
        "tag": "research background · reads the papers",
        "strength": "brings the citation that settles it",
        "flaw": "cites a paper whose setup does not match this corpus",
    },
    "tomas": {
        "name": "Tomás",
        "tag": "SRE",
        "strength": "asks what breaks at 3am and who gets paged",
        "flaw": "wants to freeze changes rather than make them safe",
    },
    "maintainer": {
        "name": "Maintainer",
        "tag": "faculty",
        "strength": "states the standard and marks the answer",
        "flaw": "",
    },
}

FOOTER = (
    "\n\n---\n<sub>📎 **Worked example.** Written by the maintainers to model what a good "
    "question, a good wrong turn and a good correction look like. Not a real cohort member — "
    "see [docs/10-community/personas.md](../blob/main/docs/10-community/personas.md). "
    "Start your own thread rather than replying here unless you have something to add.</sub>"
)


def header(key: str) -> str:
    """The attribution line that opens every seeded post."""
    p = PERSONAS[key]
    if key == "maintainer":
        return "> 🛠 **Maintainer**\n\n"
    return f"> 💬 **{p['name']}** · <sub>{p['tag']}</sub>\n\n"


def render(key: str, body: str) -> str:
    """One post: attribution, body, disclosure."""
    return header(key) + body.strip() + FOOTER
