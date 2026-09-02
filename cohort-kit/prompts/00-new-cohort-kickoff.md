# Prompt · kick off a new cohort repository

Paste into a fresh Claude Code session opened in an empty directory, or in a clone of the
reference repository. Fill the UPPERCASE fields first. Keep the token out of the prompt.

---

Use the `cohort-repo-setup` skill. Read its `references/traps.md` and `references/blueprint.md`
before any API call.

Set up the repository for **COHORT_NAME** (cohort number N) of FDE Academy, cloned from
`fde-academy-lab/advanced-rag-lab`.

Facts:
- GitHub owner: OWNER. Repository name: REPO. Visibility: private / public.
- First session: YYYY-MM-DD. Last session: YYYY-MM-DD. Weekly on WEEKDAY at HH:MM TIMEZONE, MINUTES minutes.
- Instructors (GitHub handles): HANDLE_1, HANDLE_2. Programme owner: HANDLE_0.
- Learners: I will add the roster to `cohort.yaml` myself; do not invent handles.
- The token is in my environment as `GITHUB_TOKEN`. Do not print it, echo it, or write it to a file.

Do this, in order, and stop at each human step with the exact URL and what to click:
1. Create `cohort.yaml` from `cohort-kit/cohort.example.yaml` with the facts above. Ask me for anything missing; do not guess dates or session titles.
2. Create the repository and push, then retarget the identity.
3. Run `cohort_schedule.py --check`, then generate the schedule, calendar and milestones. Copy the cohort templates into place. Open one PR for all of it and merge it with `merge_pr.py`.
4. Hand me the Discussion category list to create in the browser, with the URL. Wait for me.
5. Provision settings, labels, milestones, issues, discussions. Dry-run first, show me the plan, then run.
6. Tell me how to add `PROJECT_TOKEN`, then which workflows to dispatch for the boards, with URLs, spaced ten minutes apart.
7. Invite the people in `cohort.yaml` with their roles.
8. Verify every surface per `references/verification.md` by reading it back. Do not report from run status.
9. Write the handover in the format in `verification.md`, then the week-one checklist from `PLAYBOOK.md` with my dates filled in.

Rules: dry-run before every mutation; no number without the command that regenerates it; a permission refusal is a stop, tell me; the Hands-on board is private until I say otherwise; no em dashes in anything you write for the cohort pages.
