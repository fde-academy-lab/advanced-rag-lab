# Blueprint: what a finished cohort repository contains

The reference repository is `fde-academy-lab/advanced-rag-lab`. A cohort repository is that
repository plus a `cohort.yaml`, a resources tree, and the cohort-specific threads. Counts
below are read from the reference repository on 2026-09-02; regenerate with the command in
each row before quoting them.

## Top level

| Path | Purpose | Regenerate the count |
|---|---|---|
| `README.md` | Landing page: the brief, the LAB loop, quick start, the badges | |
| `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `LICENSE`, `CITATION.cff`, `CHANGELOG.md` | The professional floor. Learners cite the repository; recruiters open it | |
| `.identity.json` | `owner`, `repo`, `package`. Every script reads it; `scripts/retarget.py` rewrites every handle in the tree from it | |
| `Makefile` | `setup`, `test`, `lint`, `eval`, `strip`, `board` | |
| `pyproject.toml`, `requirements.txt` | The package and dev extras | |
| `.devcontainer/` | Codespaces: prebuild install, welcome script, hidden solutions | |
| `.vscode/tasks.json` | Unit pick-list; regenerated from the units, tested in CI | |
| `cohort.yaml` | **New for a cohort.** Dates, sessions, instructors, roster policy. Drives README schedule, milestones, calendar | |

## `docs/`

| Directory | Contents |
|---|---|
| `00-orientation` | start-here, the client brief, glossary, FAQ |
| `01-architecture` | ADRs, including the retraction ADR |
| `02-curriculum` | syllabus, per-session pages |
| `03-exercises` | catalogue, exercise workflow |
| `04-evaluation` | metrics, the k grid, the gate |
| `05-operations` | runbooks, cost |
| `06-interview-prep` | scenarios |
| `07-career` | portfolio |
| `08-project-management` | boards, lifecycle, ceremonies, definition of done, github-setup |
| `09-research` | reading list, measurement notes |
| `10-community` | discussions guide (14 categories, 24 plays), exercise workflow, hands-on roadmap, personas |
| `11-cohort` | **New for a cohort.** Schedule, roster policy, resources index, study guides, pre-reads. Generated from `cohort.yaml` and the templates in the kit |

## `lab-simulator/`

| Item | Count | Regenerate |
|---|---|---|
| Units (25 to 45 minutes, three gates) | 7 | `ls lab-simulator/units | grep -vE '^[A-Z]D[0-9]'` |
| Drills (5 to 15 minutes, one idea) | 9 | `ls lab-simulator/units | grep -E '^[A-Z]D[0-9]'` |
| Modes | `implement`, `diagnose`, `answer`, `decide`, `measure`, `ship` | `labsim/model.py` `MODES` |
| Kinds | `unit`, `drill` | `labsim/model.py` `KINDS` |
| Selftest | grades every reference pass and decoy | `python -m labsim selftest` |

See `lab-simulator.md` for authoring.

## `scripts/`

| Script | Job |
|---|---|
| `gh.py` | REST and GraphQL client, rate-limit recognition, no dependencies |
| `setup_github.py` | Steps: `create, settings, labels, milestones, issues, discussions, boards, project, push`. Idempotent. `--only`, `--dry-run` |
| `seed_content.py` and `seed/threads_*.py` | 8 custom categories, 40 labels, 8 milestones, 15 issues, 75 threads, corrections, cross-links, thread labels, renames, retirements, the Lifecycle board (19 practices) |
| `discussion_bot.py` | Sanitise and post the grader's reply, apply labels from unit metadata |
| `labsim_progress.py` | Per-learner attempts, clears, retries, hints; the Hands-on board |
| `discussions_pulse.py` | Heat per thread, needs-an-answer, content changes; the Pulse board |
| `labsim_digest.py` | Weekly digest of which checks catch people; not a leaderboard |
| `merge_pr.py` | Merge with the guards that make an unattended merge defensible |
| `retarget.py` | Rewrite owner and repo everywhere from `.identity.json` |
| `sweep_branches.py` | Delete branches whose PRs are all merged |
| `run_eval.py`, `failure_overlap.py`, `independence.py` | The measurements; every published number comes from one of these |
| `lint/check_links.py`, `lint/check_devcontainer.py` | The doc checks CI runs |
| `cohort_schedule.py` | **New, in the kit.** `cohort.yaml` to schedule table, `.ics`, milestones |

Regenerate the seed counts with:

```bash
python - <<'PY'
import sys; sys.path[:0] = ['scripts', 'lab-simulator']
import seed_content as s
print(len(s.CATEGORIES), len(s.LABELS) + len(s.DISCUSSION_LABELS), len(s.MILESTONES),
      len(s.ISSUES), len(s.DISCUSSIONS), len(s.LIFECYCLE))
PY
```

## `.github/`

| Item | Count | Notes |
|---|---|---|
| Workflows | 16 | Listed with their triggers in `automations.md` |
| Discussion forms | 9 | One per custom category plus Q&A; `labels:` must name existing labels |
| Issue forms | 5 plus `config.yml` | `config.yml` routes questions to Discussions with contact links |
| `PULL_REQUEST_TEMPLATE.md` | | Asks for the measurement table |
| `CODEOWNERS` | | Every PR gets a reviewer; retargeted with the handle |
| `dependabot.yml`, `labeler.yml` | | |
| `eval-baseline.json` | | The release gate's frozen baseline |

## Discussions (live surface)

| Item | Count |
|---|---|
| Categories | 14: six GitHub defaults plus eight custom |
| Seeded threads | 75 defined, 77 live on the reference (two human threads) |
| Labels applied to threads | area, drill or unit, difficulty, cleared, worked example, retracted, mechanism, first-week |

## Boards (Projects v2, account level)

| Board | Source | Sync |
|---|---|---|
| Advanced RAG, Delivery | Issues and PRs | `project-automation.yml` on open |
| L.A.B. Simulator, Hands-on | Grader replies, one draft item per learner | `labsim-progress.yml`, Mondays |
| Discussions, Pulse | Threads that moved this week, content changes | `discussions-pulse.yml` |
| Project Lifecycle | 7 phases, 19 practices, each with its artefact | `setup_github.py --only boards`, once |

## What a cohort adds on top

| Addition | Where | Mechanism |
|---|---|---|
| Schedule and calendar | `docs/11-cohort/schedule.md`, `calendar/cohort-N.ics` | `cohort_schedule.py` from `cohort.yaml` |
| Milestones per week with due dates | GitHub milestones | `cohort_schedule.py --milestones` |
| Resources per session | `resources/week-NN/` with pre-read, slides link, recording link, in-session notes | Templates in the kit; instructors push via PR or direct on a `resources/` path |
| Study guides and pre-reads | `docs/11-cohort/study-guides/week-NN.md` | Template in the kit |
| Announcements | Announcements category, one thread per week, instructors only can post | Seeded from `cohort.yaml` sessions by `seed/threads_cohort.py` |
| Doubt and query mechanism | Q&A category with the form, `status: triage`, unanswered-questions alert | `templates/workflows/unanswered-questions.yml` |
| Instructor alerts | A tracking issue assigned to instructors, updated daily; GitHub notifies on assignment | Same workflow |
| Roster and roles | Collaborators with `triage` for learners, `maintain` for instructors | REST, from `cohort.yaml` |
| Wiki | Optional; enabled only if the cohort wants a free-form space. Docs in-repo are preferred because they are reviewed and link-checked | Browser first page, then git |
