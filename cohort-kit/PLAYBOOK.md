# Cohort playbook · what the human does, in order

For the programme owner. Every step names who does it, what to click or paste, and how to
know it worked. Claude Code does the typing; you do the six things only a browser can do.
Budget for a first cohort: one working day, half of it waiting for rate limits and
invitations. Second cohort: two hours.

## Before day zero

| # | You do | Where | Done when |
|---|---|---|---|
| 1 | Decide the owner. Four cohorts under one personal account works; an organisation gives you `@org/instructors`, team mentions, and boards that outlive any one person's account. Moving later means transferring four repositories, so decide now | `https://github.com/organizations/new` if org | The owner exists |
| 2 | Create one PAT for provisioning. Classic, scopes `repo`, `project`, `workflow`; or fine-grained with repository Contents, Issues, Discussions, Pull requests, Administration, and account Projects, all read/write. Set an expiry at the cohort's end date | `https://github.com/settings/tokens` | Copied once, into your terminal as `export GITHUB_TOKEN=...`. Never into a chat |
| 3 | Fill `cohort.yaml` from `cohort-kit/cohort.example.yaml`: dates, weekday, time, timezone, sessions, instructors. Learners come later | Your editor | `python cohort-kit/scripts/cohort_schedule.py --check` prints ok |
| 4 | Install the skill so a new session knows the traps | `cp -r cohort-kit/skills/cohort-repo-setup ~/.claude/skills/` (or upload the zip to claude.ai skills) | It appears in the session's skill list |

## Day zero · provisioning (Claude does most of it)

Open a fresh Claude Code session in an empty directory and paste
`cohort-kit/prompts/00-new-cohort-kickoff.md` with the fields filled in. Then respond to the
six stops below as they come.

| Stop | You do | Where | Done when |
|---|---|---|---|
| A | Create the Discussion categories from the list Claude hands you: eight custom, exact names, exact format (Open, Q&A, Announcement) | `https://github.com/OWNER/REPO/settings/discussions` | Fourteen categories exist; tell Claude "done" |
| B | Add the PAT as a repository secret named `PROJECT_TOKEN` | `https://github.com/OWNER/REPO/settings/secrets/actions` | The secret is listed |
| C | Run the Provision workflow with steps `boards` then `project`, dry run first | `https://github.com/OWNER/REPO/actions/workflows/provision.yml` ▸ Run workflow | The run's Provision step output names a board URL for each |
| D | Ten minutes later, run the Hands-on board workflow; ten minutes after that, the Pulse workflow | `.../actions/workflows/labsim-progress.yml` and `.../actions/workflows/discussions-pulse.yml` | Four boards at `https://github.com/OWNER?tab=projects` |
| E | Set the Hands-on board to private, or decide on opt-in and say so in the welcome thread | The board ▸ Settings ▸ Visibility | You can say, in one sentence, who can see it |
| F | Arrange the views on each board (board, table, roadmap); nothing can do this for you | Each board ▸ New view | The Pulse board has a "Needs an answer" column you would read first |
| G | Link the four boards to the repository so they show on its Projects tab | `https://github.com/OWNER/REPO/projects` ▸ Link a project | Four boards listed on the repository, not only on your account page |

When Claude's handover arrives, read the first line. If it says anything is unverified, do
that check yourself before anyone is invited.

## Week minus one · people and content

| # | You do | Where | Done when |
|---|---|---|---|
| 1 | Append the roster to `cohort.yaml` `people:` with role `triage`, and let Claude send invitations. Invitations expire in seven days; send them the week before, not the day before | The clone, then `prompts/01-provision-and-verify.md` | `https://github.com/OWNER/REPO/settings/access` shows everyone as pending or accepted |
| 2 | Seed week one with `prompts/02-seed-week.md`. Fill every `TODO(instructor)` it lists | The clone | The week-one Announcements thread exists and links the pre-read |
| 3 | Post the welcome thread in General yourself, from your own account, in your own words. The seeded one is a template; the cohort should hear a person first | `https://github.com/OWNER/REPO/discussions/new?category=general` | Pinned |
| 4 | Send the calendar link: the raw URL of `calendar/cohort-N.ics`. Learners subscribe once; every session appears in their local time | Your usual channel | Two learners confirm it renders |
| 5 | Post one drill yourself from the form, on a throwaway account if you have one, and read the bot's reply. This is the only way to know the grader works on this repository | `https://github.com/OWNER/REPO/discussions/new?category=lab-simulator` | A reply with named checks within two minutes; the thread gets `drill` and a difficulty label |

## Every week

| When | Who | What | Prompt |
|---|---|---|---|
| Friday | Instructor of record | Seed next week: resources, study guide, the Announcements and Standup threads; update the README "This week" block | `prompts/02-seed-week.md` |
| Friday | Instructor of record | Open the Standup thread with Moved, Blocked, Wrong about, Numbers. The third heading is the one that teaches | by hand |
| Monday, before 08:00 UTC | Programme owner | The ten-minute operations pass: unanswered questions, hands-on picture, hottest threads, content changes, rate limit | `prompts/03-weekly-ops.md` |
| Monday, 08:17 and 08:41 UTC | Nobody | Digest and Hands-on board sync run themselves. Read the step output if the board looks stale | |
| Daily, 04:23 UTC | Nobody | Unanswered-questions issue updates; instructors are assigned and notified | |
| Within 24h of a question | Any instructor | Answer in the thread and **mark the answer**. Marking is what clears the alert and what makes the thread findable | |
| Within a day of a session | TA | Commit `session-notes.md` and `recording.md` for the week | |
| Any time | Anyone with `maintain` | Merge a PR with `python scripts/merge_pr.py N --wait 900`. It refuses red and has no override | |

## Signs something is wrong, and where to look

| Sign | Look at | Usually |
|---|---|---|
| A learner posts a drill and nothing replies | `.../actions/workflows/lab-simulator-discussions.yml` runs | Category name is not one the router recognises; or the post is in the wrong category |
| A board is stale on Tuesday | The Monday run's "Sync the board" step | No `PROJECT_TOKEN`, or a rate limit with a printed reset time |
| A thread you renamed appears twice | The Provision run's log | The rename was refused (built-in token) and the create loop ran. Delete the copy by hand; the guard in `rename_threads` should have prevented it, so also file it |
| A green Provision run and no board | The step output, not the run status | Scope on the PAT. The token's settings page is the only place that settles it |
| A PR is green and will not merge | `merge_pr.py` output | The branch is behind, or a required context has not registered; the script handles both if you give it `--wait` |
| A workflow never runs on schedule | The Actions list for a run named after the file path with zero jobs | `secrets` inside an `if:`; the file was rejected |

## Closing

The week after the last session, `prompts/04-close-cohort.md`. Its last section is the
input to the next cohort's `cohort.yaml`. That loop is the reason the kit exists.
