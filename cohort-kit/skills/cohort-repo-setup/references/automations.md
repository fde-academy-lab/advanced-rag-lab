# Automations

Sixteen workflows in the reference repository, plus one the kit adds. Triggers and
permissions are what matter; the rest is in each file's header comment, which is written to be
read.

| Workflow | Trigger | Permissions | Does |
|---|---|---|---|
| `ci.yml` | push to main, PR | contents read | Lint, tests on 3.11, one-click promise, notebook outputs stripped, devcontainer pick-list |
| `eval-regression.yml` | PR | contents read | Runs the eval and posts a scorecard; fails when a metric drops below the frozen baseline |
| `lab-simulator.yml` | push, PR touching units | contents read | `labsim validate` and `selftest`; every reference pass must pass and every decoy must fail |
| `lab-simulator-discussions.yml` | discussion created or edited, comment created | route none, grade none, respond discussions write and issues write | Grades a thread in the LAB Simulator category; commands `/check /hint /why /solution /status /progress /help` |
| `lab-simulator-digest.yml` | Mondays 08:17 UTC, dispatch | discussions write | Which checks caught people this week; not a leaderboard |
| `labsim-progress.yml` | Mondays 08:41 UTC, dispatch | contents read, discussions read, PAT for the board | Per-learner table and the Hands-on board |
| `discussions-pulse.yml` | schedule, dispatch | same shape | Heat, needs-an-answer, content changes; the Pulse board |
| `housekeeping.yml` | push to main, dispatch | contents write for branches, discussions and issues write for seeding | Sweeps merged branches; seeds any missing thread, unconditionally |
| `provision.yml` | dispatch with a `steps` choice | contents read, issues write, discussions write, PAT when present | The terminal-free path for every seeder step |
| `project-automation.yml` | issue or PR opened, reopened, closed | repository-projects write, issues write | Adds new items to the Delivery board; explains the board on a new issue |
| `labeler.yml` | PR opened, synchronised | pull-requests write | Path-based labels |
| `link-check.yml` | push to md, PR, Sundays | contents read | Relative links resolve; Mermaid renders |
| `notebooks.yml` | schedule, dispatch | contents read | Executes every notebook headlessly |
| `pages.yml` | push to notebooks, raglab, docs | pages write | Builds the site |
| `stale.yml` | Mondays 06:00 UTC | issues and PRs write | 45 days stale, 14 to close; exempts `type: exercise`, `cohort`, `pinned` |
| `welcome.yml` | first issue or PR | issues and PRs write | A human-shaped first reply that routes questions to Discussions |
| `unanswered-questions.yml` (kit) | daily, dispatch | discussions read, issues write | Updates a tracking issue assigned to instructors with every Q&A thread unanswered for 24 hours |

## Patterns that keep them safe

**The three-job split for untrusted code.** `route` reads the event and decides, running no
code. `grade` runs the learner's Python with `permissions: {}`, no secrets,
`persist-credentials: false`, `ref: main` and a hard timeout; it cannot write, cannot read a
secret, holds no token. `respond` has write scope and runs no untrusted code; it posts a
sanitised artifact. Untrusted content is never interpolated into a shell: the payload is on
disk at `$GITHUB_EVENT_PATH` and is passed by path. `${{ github.event.discussion.body }}`
appears nowhere and must not be added.

**Secrets through an output, never in an `if`.** A step reads the secret into
`have_pat=true|false`; later steps branch on `steps.tok.outputs.have_pat`. GitHub rejects
the whole file otherwise, silently from the schedule's point of view.

**The bot never reacts to itself.** `route` sets `proceed=false` when the actor is the bot.
Without it, a reply that contains `/check` triggers a run that posts a reply, forever.

**Unconditional idempotent steps.** Seeding runs on every push to main. A guard that made a
failure unrecoverable cost weeks of unseeded content.

**Keep the log as an artifact.** Step summaries and job logs are not readable through the API
from a restricted network; an uploaded `seed.log` is.

**Required checks run on every PR.** A `paths`-filtered workflow that produces a required
context deadlocks every PR outside those paths. `tests/test_workflows.py` enforces it.

**Nothing schedules on the hour.** `:17`, `:41`, off-peak. Two board syncs in the same
minute hit the secondary rate limit.

**Tokens by preference.** `${{ secrets.PROJECT_TOKEN || secrets.GITHUB_TOKEN }}` gives the
PAT when present and the built-in token otherwise, for every step that can use either.

## Adding a workflow

1. Write the header comment first: what it does, what it must not do, what it needs.
2. Least permissions at the top (`permissions: {}`), then per job.
3. Any `if:` that mentions a secret is a bug. Any interpolation of user content into `run:`
   is a bug.
4. Add the local mirror to pytest, so the CI step is not the only place it runs.
5. Dispatch once by hand from the browser and read the step output, not the run status.
