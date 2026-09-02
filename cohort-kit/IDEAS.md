# Ideas, ranked, from the peer at the next desk

Each idea names the mechanism, the cost, and the reason it is not already built. Built
things are in `docs/10-community/hands-on-roadmap.md`; this page is what a cohort adds.
Friction is the learner's; cost is ours.

## Do these before cohort 1 starts

| # | Idea | Mechanism | Cost | Why not yet |
|---|---|---|---|---|
| 1 | **One organisation, four repositories, one instructors team** | `@fde-academy/instructors` in CODEOWNERS and in the unanswered-questions issue; boards at the org; a `cohort-template` repository marked as a template so "Use this template" replaces the clone-and-retarget dance | An afternoon and a repository transfer | Decided by the programme owner, not by a script. Transferring later costs more than deciding now |
| 2 | **Answer SLA visible to learners** | The Q&A form's markdown block says "answered within 24 hours on weekdays"; the unanswered-questions workflow is what makes the promise true | Ten minutes | Only worth writing down once the workflow has run for a week without lying |
| 3 | **The welcome thread from a person** | The programme owner posts it, pinned, in their own voice, before any bot posts anything | Twenty minutes | A habit, not a feature |
| 4 | **Codespaces prebuilds on `main`** | Settings ▸ Codespaces ▸ prebuild; the devcontainer already does the install in `onCreateCommand` | Five minutes, some Actions minutes per push | Browser only |

## Do these in week one, from real data

| # | Idea | Mechanism | Cost | Why not yet |
|---|---|---|---|---|
| 5 | **"Someone else is stuck where you just passed"** | When a thread clears, the reply names one open thread on the same unit whose last failure is a check the clearer passed. A clear becomes a review owed | A day in `discussion_bot.py`; the respond job can query threads | The single highest-leverage community mechanic here. Needs one week of real threads to test against |
| 6 | **Drill of the week in Announcements** | The digest already knows the unit with the lowest clear rate; pin it with the check that catches people | Five lines in `labsim_digest.py` | Wants an instructor to agree it goes in Announcements |
| 7 | **`/next`** | `/progress` already computes what is unlocked; `/next` returns the single best one, same track first, drill before unit | An hour | Trivial once `/progress` has run in production |
| 8 | **Office-hours queue from the Pulse board** | The "Needs an answer" column, sorted by waiting time, is the office-hours agenda. Post it as the session's first comment | A view and a habit | Views are manual |

## Resource sharing, in and around sessions

| # | Idea | Mechanism | Cost | Why not yet |
|---|---|---|---|---|
| 9 | **In-session shared notes as a file, not a doc** | `resources/week-NN/session-notes.md` edited in a Codespace by the TA, committed within the day; learners comment on the announcement thread | Zero code | A habit. The template exists |
| 10 | **A `resources` path that instructors can push to directly** | CODEOWNERS grants `@instructors` on `resources/**`; branch protection still requires CI, so a broken link is caught before it lands | Two lines | Needs the org and the team (idea 1) |
| 11 | **Pre-read as questions, not titles** | The template's table has a "question it answers" column. Enforce it with a test that every pre-read row has one | An hour | Write the first three by hand first |
| 12 | **Recording timestamps as the index** | `recording.md` holds the timestamps that matter; the wrong turn and the fix, not the agenda | Zero code | Habit |
| 13 | **A wiki for the things nobody owns** | Enable the wiki for glossary drift and links people find; keep the reviewed material in `docs/` | Browser first page, then git | The reference repository turned the wiki off deliberately; docs are link-checked and reviewed, a wiki is neither. Enable only if a cohort asks |

## Alerts and notifications, honestly

| # | Idea | Mechanism | Cost | Why not yet |
|---|---|---|---|---|
| 14 | **Assignment as the alert** | The tracking issue assigned to instructors; GitHub notifies on assignment and on edits. No webhook | Built in the kit | Untested against live GraphQL from this session; verify on the first cohort |
| 15 | **Slack or email fan-out** | A repository secret with a webhook URL and one `curl` in the workflow, guarded by the `have_pat` pattern | An hour | Adds a secret and a third party. Do it only when GitHub notifications are demonstrably being missed |
| 16 | **Weekly personal digest** | A Monday comment on each learner's most recent open thread: what moved, what is unlocked | One more mode on `labsim_progress.py` | Wants an opt-in; unsolicited bot comments are noise |

## Pathway and progression

| # | Idea | Mechanism | Cost | Why not yet |
|---|---|---|---|---|
| 17 | **Week-gated pathway** | `cohort.yaml` names the drills per week; `/status` shows "this week" first | An hour in `render_status` | Wants the schedule in the repo first, which the kit now does |
| 18 | **Retry ladders** | After two fails on one check, offer a smaller drill that isolates it; needs a `remediates:` field | A day plus drills to point at | The data model is ready; the drills are not written |
| 19 | **`spot` drills from real threads** | A real Show-and-tell write-up, with consent, claims numbered, grade "which are unsupported" | Curation | The first three should be faculty-written, like `ED3` |
| 20 | **Cohort-level lifecycle board** | The Lifecycle board copied per cohort; the retro asks which practice was marked Done without its artefact | `--only boards` per repo | Built; needs the PAT per repo |

## The ones to argue about

| # | Idea | Why it might be wrong |
|---|---|---|
| 21 | **Badges and streaks** | A badge is a leaderboard of one. `labsim badge` gives a paste-able line from what was actually cleared, which is the honest version |
| 22 | **LLM-written feedback** | The reply is specific because it is assembled from metadata a human wrote. A generated paragraph is more fluent and less true |
| 23 | **A public per-learner board** | Counting attempts by name in public is tracking a person. Private or opt-in, decided before the first post |
| 24 | **Auto-closing stale questions** | A question nobody answered is our failure, not the asker's. The stale workflow exempts `cohort`; keep it that way |
| 25 | **One repository for all cohorts** | Cheaper to run, but every cohort would read every other cohort's threads, boards would mix, and closing a cohort would mean archiving nothing. One repository per cohort, one template for all of them |
