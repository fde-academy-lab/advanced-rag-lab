# Boards

Four Projects v2 boards. All four belong to the **account**, not the repository, so every
write needs `PROJECT_TOKEN`. The built-in token can read nothing and write nothing on them.

| Board | Title | Items | Fields | Created by | Kept current by |
|---|---|---|---|---|---|
| Delivery | Advanced RAG, Delivery | Issues and PRs | 5 custom fields | `setup_github.py --only project` | `project-automation.yml` on open or reopen |
| Hands-on | L.A.B. Simulator, Hands-on | One draft item per learner | attempts, clears, retries, hints, open units, stage | `labsim_progress.py --board` | `labsim-progress.yml`, Mondays 08:41 UTC |
| Pulse | Discussions, Pulse | One draft item per thread that moved, one per week of content change | heat, comments, people, needs an answer | `discussions_pulse.py --board` | `discussions-pulse.yml` |
| Lifecycle | Project Lifecycle, the shape this project follows | 19 practices across 7 phases | phase, artefact, file | `setup_github.py --only boards` | By hand: move to Done when the artefact exists |

## The two rules

**Tracking, not ranking.** The Hands-on board sorts by login and has no score. A leaderboard
on a public repository ranks who had a free weekend. Make the board private or opt-in before
the first learner posts; the setting is in the board's own Settings page and there is no API
for it.

**Heat is a policy, written down.** Pulse heat is `comments × 3 + people × 2 + reactions`.
The weights are in `discussions_pulse.py` and tested. Change them there, not in a doc.

## Why discussions are draft items

Projects v2 items are issues, pull requests or draft items. A discussion cannot be added, so
both discussion-driven boards mirror threads as drafts with the URL in the body and upsert by
title. Deleting the board and re-running recreates every item.

## Rate limits

Each upsert is at least one mutation. Sixty learners and forty active threads is a hundred
mutations, against a secondary limit of about eighty a minute and an hourly quota shared with
everything else the account does. `_run()` in both scripts recognises the refusal and prints
the reset time. Schedule the two syncs at least ten minutes apart and off the top of the hour.

## Views (browser)

The scripts create the project and its fields. Views are manual:

- Delivery: board grouped by Status; table sorted by milestone.
- Hands-on: table sorted by login; a second view filtered to `stage != done`.
- Pulse: board grouped by "Needs an answer"; the Yes column is the instructor's queue.
- Lifecycle: board grouped by phase.

## What to check after a sync

`https://github.com/OWNER?tab=projects`. Then open the run and read the "Sync the board"
step. A green run with the step skipped means no PAT was present; the "Say why the board was
skipped" step says so.
