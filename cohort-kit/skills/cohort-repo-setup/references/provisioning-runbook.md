# Provisioning runbook

Every command below was run against the reference repository. Replace `OWNER` and `REPO`.
Preview with `--dry-run` first, every time. Read the output. Then run for real.

## 0. Preconditions

- A GitHub account that will own the repository. For four cohorts, an organisation is the
  better owner: teams (`@org/instructors`) can be mentioned and used in CODEOWNERS, and
  boards live at the org. A personal account works and is what the reference uses.
- A PAT for the human's terminal, if provisioning from a terminal: fine-grained, repository
  permissions Contents, Issues, Discussions, Pull requests, Administration read/write; account
  permission Projects read/write for boards. Or classic with `repo`, `project`, `workflow`.
- A Claude Code session may be behind a proxy that refuses GraphQL and workflow dispatch.
  Test with `GET /rate_limit` (always works) and one small GraphQL query. If GraphQL is
  refused, every GraphQL step goes through the Provision workflow in the browser.

## 1. Create the repository

Option A, from the reference as a template (browser):
`https://github.com/fde-academy-lab/advanced-rag-lab/generate`, name it
`fde-academy-cohort-N` (or per `cohort.yaml`), private for a paid cohort.

Option B, from a clone (terminal):

```bash
git clone https://github.com/fde-academy-lab/advanced-rag-lab cohort-N && cd cohort-N
python scripts/retarget.py --owner OWNER --repo REPO      # rewrites .identity.json and every handle
export GITHUB_TOKEN=github_pat_...                         # never paste it into chat
python scripts/setup_github.py --owner OWNER --repo REPO --only create,push --private --dry-run
python scripts/setup_github.py --owner OWNER --repo REPO --only create,push --private
```

Check: `https://github.com/OWNER/REPO` exists and `main` has the history.

## 2. Apply `cohort.yaml`

```bash
cp cohort-kit/cohort.example.yaml cohort.yaml           # then fill it in with the user
python cohort-kit/scripts/cohort_schedule.py --check     # validates dates and sessions
python cohort-kit/scripts/cohort_schedule.py             # writes docs/11-cohort/schedule.md and calendar/*.ics
python cohort-kit/scripts/cohort_schedule.py --milestones --dry-run
python cohort-kit/scripts/cohort_schedule.py --milestones   # one milestone per week, with due dates
```

Then copy the templates: `cohort-kit/templates/README.cohort.md` into the README's cohort
section, `templates/resources/` into `resources/`, `templates/CLAUDE.md` to the root. Commit
on a branch, open a PR, merge with `python scripts/merge_pr.py N --wait 900 --expect-head SHA`.

## 3. Discussion categories (browser, the human)

Hand over this list verbatim, with the URL first:

`https://github.com/OWNER/REPO/settings/discussions`

Create each row from `discussions-design.md` §Categories with the exact name, emoji and
format. Names without dots. The six GitHub defaults already exist. Wait for "done" before
step 4; the seeder skips threads whose category is missing and says so, but it will not
create the category.

## 4. Settings, labels, milestones, issues, discussions

Terminal:

```bash
python scripts/setup_github.py --owner OWNER --repo REPO --only settings,labels,milestones,issues,discussions --dry-run
python scripts/setup_github.py --owner OWNER --repo REPO --only settings,labels,milestones,issues,discussions
```

Browser, when the terminal cannot reach GraphQL:
`https://github.com/OWNER/REPO/actions/workflows/provision.yml` ▸ Run workflow ▸ steps
`settings,labels,milestones,issues,discussions,boards,project` with `dry_run` on, read the
summary, then again with `dry_run` off.

`settings` sets branch protection with the five required contexts. `REQUIRED_REVIEWERS=0`
unless two humans will review; the reason is in `setup_github.configure_repository`.

## 5. Boards

1. The human creates a PAT with `project` scope and adds it as a repository secret named
   `PROJECT_TOKEN` at `https://github.com/OWNER/REPO/settings/secrets/actions`.
2. Provision workflow ▸ steps `boards` (Lifecycle) and `project` (Delivery).
3. `https://github.com/OWNER/REPO/actions/workflows/labsim-progress.yml` ▸ Run workflow.
4. `https://github.com/OWNER/REPO/actions/workflows/discussions-pulse.yml` ▸ Run workflow.
5. Check `https://github.com/OWNER?tab=projects` (or `https://github.com/orgs/ORG/projects`).
   Four boards. If fewer, read the run's step output: rate limit says a time, scope says
   "createProjectV2" refused.
6. Set the Hands-on board to private, or get opt-in from learners. Decide now.
7. Update `project-automation.yml` with the Delivery board URL if the number differs from 1.
8. Link each board to the repository so it appears on the repository's own Projects tab:
   `https://github.com/OWNER/REPO/projects` ▸ "Link a project" ▸ pick each of the four. The
   scripts never call `linkProjectV2ToRepository`; without this the boards exist only on the
   account's projects page.

Run the two board syncs at least ten minutes apart. Both hit the same hourly quota.

## 6. People

From `cohort.yaml` `people:`; `triage` for learners on a private repo (label, close, mark
answers, no code push), `maintain` for instructors, `admin` for the programme owner.

```bash
python - <<'PY'
import sys, yaml; sys.path.insert(0, 'scripts')
from gh import request
c = yaml.safe_load(open('cohort.yaml'))
for p in c['people']:
    request('PUT', f"/repos/{c['github']['owner']}/{c['github']['repo']}/collaborators/{p['github']}",
            {'permission': p['role']})
    print('invited', p['github'], p['role'])
PY
```

Invitations expire in seven days; the acceptance list is at
`https://github.com/OWNER/REPO/settings/access`. Learners who fork a public repo need no
invitation; exercises are submitted in Discussions either way.

## 7. Verify

Follow `verification.md`. Do not skip it because the runs were green. Then write the handover.

## Re-running later

Everything is idempotent. Adding a thread to a seed module and merging to `main` seeds it
through `housekeeping.yml` on the next push. Renames and corrections need `PROJECT_TOKEN`
and therefore the Provision workflow. New labels: `--only labels` is a PATCH per label.
