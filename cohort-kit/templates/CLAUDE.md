# CLAUDE.md · cohort repository memory

This repository is one FDE Academy cohort, cloned from `fde-academy-lab/advanced-rag-lab` and
parametrised by `cohort.yaml`. Read `cohort.yaml` first; it names the owner, the repo, the
dates and the people.

## Standing rules

- Every GitHub mutation goes through `scripts/setup_github.py`, `scripts/merge_pr.py`,
  `cohort-kit/scripts/cohort_schedule.py` or a workflow. Dry-run first, read the plan, then run.
- A green workflow run is not proof. Read the surface back through the API and count.
- No number in prose without the command that regenerates it.
- Learners are tracked, never ranked. The Hands-on board is private or opt-in.
- Learner submissions run only in the grade job with no token. Never add a secret to it.
- Tokens never appear in chat or in a file. Repository secrets only.
- A permission refusal from the classifier is a stop. Say what was refused; do not route around.
- Titles are keys. Renaming a seeded thread means editing `RENAMED`, not the title in place.
- No em dashes in prose written for this repository's cohort pages.

## Where things are

| Need | Path |
|---|---|
| The order of operations, traps, verification | `cohort-kit/skills/cohort-repo-setup/` |
| Week-by-week operation | `cohort-kit/PLAYBOOK.md` |
| Discussions playbook | `docs/10-community/discussions-guide.md` |
| Simulator authoring | `lab-simulator/README.md`, `cohort-kit/skills/cohort-repo-setup/references/lab-simulator.md` |
| Boards | `docs/08-project-management/`, `references/boards.md` |
| Schedule, calendar, milestones | `cohort.yaml` via `cohort-kit/scripts/cohort_schedule.py` |
| Session resources | `resources/week-NN/` |

## Commands that must pass before a push

```bash
make lint && make test
python -m labsim validate && python -m labsim selftest     # from lab-simulator/
python cohort-kit/scripts/cohort_schedule.py --check
```

## Merging

`python scripts/merge_pr.py N --wait 900 --expect-head <sha>`. It refuses red, waits for
required contexts, and updates a branch that is behind. There is no override flag; a red
build is a human's decision.
