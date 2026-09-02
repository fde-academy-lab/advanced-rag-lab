# Discussions design

The full playbook lives in the reference repository at
`docs/10-community/discussions-guide.md` (14 categories, 9 forms, 24 plays, lifecycle,
moderation, bots, search recipes). This page is the part a provisioning session needs.

## Categories

Create these in the browser; there is no API. Six defaults exist already.

| Category | Emoji | Format | Who posts | What lives there |
|---|---|---|---|---|
| Announcements | 📣 | Announcement | Instructors | One thread per week: what to read, what is due, where the session is. Learners cannot open threads here, which is the point |
| General | 💬 | Open | Anyone | Everything that is not a question or a submission |
| Ideas | 💡 | Open | Anyone | Proposals for the programme or the repo |
| Q&A | ❓ | Q&A | Anyone | Doubts. The form asks what was tried. Marking the answer closes the loop and feeds the alert workflow |
| Show and tell | 🎤 | Open | Anyone | Capstones, results that surprised, decision records |
| Polls | 📊 | Poll | Instructors | Session timing, topic votes. Browser only |
| Design Reviews | 🏗 | Open | Anyone | A design before it is built, with its constraints and cost |
| Reading Club | 📚 | Open | Anyone | The argument about an assigned paper. The assignment is an issue |
| Interview Prep | 🎯 | Q&A | Anyone | An answer practised and critiqued. Nothing under NDA |
| Exercises & Submissions | 🧪 | Q&A | Learners | Every exercise: approach, then submission with an interval, one peer review owed |
| Math & Theory | 🧮 | Q&A | Anyone | Derivations and the question behind the formula |
| Debugging Clinic | 🐞 | Q&A | Anyone | A failure nobody can explain, symptom first |
| LAB Simulator | 🧪 | Q&A | Learners | Post a unit or drill; the bot grades it. Name without dots so the slug is `lab-simulator` |
| Weekly Standup & Retro | 🗓 | Announcement | Instructors | Moved, blocked, wrong about, numbers |

The exact names and descriptions are in `scripts/seed_content.py` `CATEGORIES`; hand the
human that list, not a paraphrase.

## Forms

`.github/DISCUSSION_TEMPLATE/<slug>.yml`, one per custom category and one for Q&A. Each
`labels:` entry must exist in `LABELS`. The simulator form's dropdown lists every unit and
drill; `tests/test_workflows.py` fails when a unit is missing from it.

## Labels on threads

Threads carry the same `area:` labels as issues, so one search spans both surfaces.
The bot applies `drill` or `unit`, `difficulty:`, `area:` and `cleared` from unit metadata,
never from what a learner typed. Faculty threads carry `worked example`. Threads with a
withdrawn claim carry `retracted` and a banner at the top.

Search recipes that the labels make possible:

- `label:drill label:"difficulty: easy" -label:cleared` is a learner's to-do list.
- `category:Q&A is:unanswered` is the instructor's queue.
- `label:first-week` is what to read in week one.

## Seeded threads

The reference ships 75 threads written by faculty as worked examples: a good question, a wrong
turn, a correction. They are keyed by exact title. A cohort adds, in `seed/threads_cohort.py`:

- One Announcements thread per session, from `cohort.yaml`, posted the week before.
- One "Welcome, cohort N" thread in General with the schedule and the three first plays.
- One Weekly Standup thread per week, opened by the instructor of record, with the four
  headings: Moved, Blocked, Wrong about, Numbers.

Do not seed learner-voiced threads for a cohort. The reference's personas are labelled
`worked example` for a reason; a cohort's own threads should be the cohort's.

## The doubt and query mechanism

1. A learner opens a Q&A thread through the form. The form applies `status: triage`.
2. The Pulse board's "Needs an answer" column lists it within the sync window.
3. `unanswered-questions.yml` runs daily, finds Q&A threads with no answer marked and no
   instructor comment in the last 24 hours, and updates one tracking issue titled
   "Unanswered questions" assigned to the instructors. Assignment and edits notify them
   through GitHub's own notifications; no webhook, no third party.
4. An instructor answers and marks the answer, or a learner marks a peer's answer.
5. A thread with an answer for 30 days and no new comment is a candidate for the docs FAQ.
   That is a human decision, made in the weekly retro.

## Etiquette the forms enforce

- Approach before code, in the submission form.
- What you tried, in the question form.
- The number, not the adjective, in every form with a metric field.
