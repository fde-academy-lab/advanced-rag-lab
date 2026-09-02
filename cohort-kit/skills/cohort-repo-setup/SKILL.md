---
name: cohort-repo-setup
description: Set up, provision and operate a complete FDE Academy cohort repository on GitHub, end to end, from a fresh Claude Code session. Use this whenever the user mentions a new cohort, a cohort repo, cohort 1 to 4, provisioning Discussions, labels, boards, the L.A.B. Simulator, seeding threads, pre-reads, study guides, resource sharing for a session, instructor alerts, or "set up the repo like advanced-rag-lab". Trigger it even when the user only says "start cohort 3" or "get the repo ready for Monday". It carries the verified traps from building fde-academy-lab/advanced-rag-lab, so read it before touching the GitHub API.
---

# Cohort repo setup

One cohort, one repository, cloned from the reference repository
`fde-academy-lab/advanced-rag-lab` and parametrised by a single `cohort.yaml`. The reference
repository is the source of truth for the code, the units, the workflows and the seeder. This
skill is the source of truth for the **order of operations, what cannot be automated, and the
traps that cost a day each the first time**.

Everything in `references/` was learned by doing it, not by reading docs. When this skill and
GitHub's current behaviour disagree, GitHub wins, and the disagreement goes into
`references/traps.md` as a new row with the date.

## Before you do anything

1. Read `references/traps.md` in full. It is short and every row was paid for.
2. Read `references/blueprint.md` so you know what a finished cohort repo contains.
3. Ask for, or find, the `cohort.yaml`. If there is none, copy `cohort.example.yaml` from the
   kit and fill it in with the user. Do not invent dates, names, or session titles. The
   `decision-questionnaire` skill exists for exactly the unsettled fields.
4. Confirm the two things a runner cannot bootstrap: the user can create a repository and can
   create Discussion categories in a browser. Nothing else needs a browser.

## The order of operations

The order matters because later steps read what earlier steps created, and because two of
them cannot be done by any API.

| # | Step | Who | Tool | Reference |
|---|---|---|---|---|
| 1 | Create the repository from the reference (template or clone), retarget the identity | Claude | `scripts/retarget.py`, `setup_github.py --only create,push` | `references/provisioning-runbook.md` §1 |
| 2 | Apply `cohort.yaml`: README, schedule, milestones, calendar file, resources tree | Claude | `cohort-kit/scripts/cohort_schedule.py` | §2 |
| 3 | **Create the Discussion categories in the browser** | Human | Settings ▸ Discussions | §3, `references/discussions-design.md` |
| 4 | Settings, labels, milestones, issues, discussions | Claude or Actions | `setup_github.py` or Provision workflow | §4 |
| 5 | Add `PROJECT_TOKEN` secret, then boards | Human, then Actions | Provision `boards`, the two board workflows | §5, `references/boards.md` |
| 6 | Invite learners and instructors, set roles | Claude via REST | `PUT /repos/{o}/{r}/collaborators/{login}` | §6 |
| 7 | Verify every surface by reading it back, not by trusting green | Claude | `references/verification.md` | §7 |
| 8 | Hand the user the week-one checklist and the operating rhythm | Claude | `PLAYBOOK.md` in the kit | |

Run steps 1, 2, 4, 6 and 7 yourself. Hand the user steps 3 and 5 as a numbered list with the
exact URL for each click, in the form `https://github.com/OWNER/REPO/settings/discussions`,
and wait. Never describe a click without its URL.

## Rules that are not optional

- **Do not hallucinate a GitHub feature.** If you are not sure an API exists, say so and put
  the manual step in the runbook. `references/github-api-limits.md` lists what has no API.
- **Every number needs a command that regenerates it.** A metric, a count, a date in a doc
  must trace to a script or a file. This is the rule that caught a retraction propagated to
  eleven files in the reference repository.
- **Green is not done.** A workflow run can succeed while a step swallows a refusal. Read the
  seed log artifact or the step output. Then read the surface back through the API.
- **Idempotent or nothing.** Every seeding operation keys on a title or a marker comment. A
  rename needs a refused-set guard or you get duplicates. Nine duplicates, once.
- **A classifier block is a stop.** If the permission system refuses an action, do not route
  around it with a different tool. Tell the user what was refused and why you wanted it.
- **Secrets never appear in chat.** Tokens go into repository secrets or `export` in the
  user's own terminal. If a token has been pasted into a chat, say once that it should be
  rotated, then stop raising it.
- **Learners are not ranked in public.** Track attempts and clears; never sort by score on a
  public board. The Hands-on board is private or opt-in. Decide before the first learner posts.
- **Untrusted code runs with no token.** Any workflow that executes learner submissions uses
  the three-job split in `references/automations.md`. No exceptions for convenience.

## What "done" looks like

A cohort repository is done when `references/verification.md` passes end to end and the
user has been handed:

1. The repository URL, the Discussions URL, and each board URL.
2. The list of what was created, with counts, read back from the API.
3. The list of what was skipped and why, with the URL where a human finishes it.
4. The week-one checklist from `PLAYBOOK.md`, filled in with this cohort's dates.

Write that handover as the final message. If anything in it was not verified, say so in the
first line.

## Where to go next

| Need | Read |
|---|---|
| What a finished repo contains, directory by directory | `references/blueprint.md` |
| The exact commands and URLs, in order | `references/provisioning-runbook.md` |
| Which category, form, label and thread goes where | `references/discussions-design.md` |
| Authoring a unit or a drill, and how the grader is graded | `references/lab-simulator.md` |
| The four boards and the PAT they need | `references/boards.md` |
| Every workflow and the patterns that keep them safe | `references/automations.md` |
| Proving a step worked | `references/verification.md` |
| What GitHub will not let you automate | `references/github-api-limits.md` |
| The traps, dated | `references/traps.md` |
| Weekly operation once learners arrive | `PLAYBOOK.md` and `prompts/03-weekly-ops.md` in the kit |
