# Prompt · the Monday operations pass

Ten minutes, every Monday morning, before the boards' scheduled syncs have run. Paste into a
session in the clone.

---

Use the `cohort-repo-setup` skill. Cohort N, OWNER/REPO. Give me the Monday picture.

1. Unanswered questions: run `cohort-kit/scripts/unanswered_questions.py --dry-run` (or read the tracking issue if GraphQL is refused here). List each with how long it has waited and who asked.
2. Hands-on: run `scripts/labsim_progress.py` for the table. Tell me who has not posted anything in two weeks, without ranking anyone. Tell me which check failed most often this week and whether people cleared it on the second attempt (that distinguishes "the lesson landing" from "the brief is doing too little").
3. Pulse: run `scripts/discussions_pulse.py` for the table. The three hottest threads and any thread in "needs an answer".
4. Content: what changed in `docs/`, `resources/` and `lab-simulator/units/` since last Monday, from git log.
5. Housekeeping: did the last run on `main` seed anything, and is the seed log artifact present?
6. Rate limit: `GET /rate_limit`; if the GraphQL quota is under 2000 points, say so before I dispatch any board sync.

Then three lines: what to say in today's Announcements thread, which two threads to answer first, and what to fix in the repo this week. Nothing generic; every line names a thread, a unit, or a file.
