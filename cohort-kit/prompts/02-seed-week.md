# Prompt · seed one week's content

Every Friday, for the coming week. Paste into a session in the clone.

---

Use the `cohort-repo-setup` skill. Cohort N, OWNER/REPO, `cohort.yaml` is the source of truth.
Seed week W.

1. Read `cohort.yaml` for week W: title, date, pre-reads, drills, units, exercises. Do not add readings that are not listed; ask me instead.
2. Create `resources/week-0W/` from `cohort-kit/templates/resources/week-NN/`, filled in with the week's facts. Leave every LINK placeholder I have not given you as `TODO(instructor)` and list them at the end.
3. Write `docs/11-cohort/study-guides/week-0W.md` from `cohort-kit/templates/study-guide.md`. The questions come from the pre-reads and the drills' `teaches` lists; cite the section for each.
4. Add the week's Announcements thread and the Standup thread to `scripts/seed/threads_cohort.py`, keyed by exact title, in the shape the existing standup threads use (Moved, Blocked, Wrong about, Numbers, with the Numbers table empty for the instructor to fill).
5. Update the "This week" block in the README.
6. `make lint && make test`, `cohort_schedule.py --check`, then a PR. Merge it with `merge_pr.py`; housekeeping seeds the threads on the push. Read back the two new threads by title and give me their URLs.
7. List every TODO(instructor) left, with the file and line.
