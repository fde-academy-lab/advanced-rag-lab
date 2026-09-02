"""Cohort-specific threads: one Announcements thread per session, one Standup per week.

Empty in the reference repository on purpose. A cohort repository fills this from its
`cohort.yaml` (see cohort-kit/prompts/02-seed-week.md), keyed by exact title like every other
seed module, and housekeeping seeds whatever is missing on the next push to main.

The shape of an entry is the one in threads_standup.py: category, author, title, body, and an
optional replies list. Announcements use category "Announcements"; standups use
"Weekly Standup & Retro" with the four headings Moved, Blocked, Wrong about, Numbers.
"""
from __future__ import annotations

THREADS: list[dict] = []
