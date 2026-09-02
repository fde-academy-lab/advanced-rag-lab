# Traps, dated

Every row here cost real time in `fde-academy-lab/advanced-rag-lab` between 2026-08-29 and
2026-09-02. Read the whole table before the first API call. Add a row when you pay for a
new one; never delete a row, mark it `retired` with the reason.

| # | Trap | What it looks like | What to do instead |
|---|---|---|---|
| 1 | **Label description over 100 characters** | `POST /labels` answers 422 on every run, with every token. The warning sits in a log nobody downloads. In the reference repo the `worked example` label was missing from fifteen threads for days. | Keep descriptions at or under 100 characters. `tests/test_seed_content.py` holds every label to the cap. |
| 2 | **`secrets` inside an `if:`** | GitHub rejects the whole workflow file. The run appears named after the file path, with zero jobs, on every push. From the schedule's point of view it silently never runs. | Read the secret in a step into an output (`have_pat=true`) and branch on `steps.tok.outputs.have_pat`. `tests/test_workflows.py` lints for `secrets` in any `if`. |
| 3 | **Actions `GITHUB_TOKEN` cannot edit another person's discussion** | `updateDiscussion` is refused for threads the bot did not author. Renaming seeded threads from housekeeping fails. | Renames run from the Provision workflow with `PROJECT_TOKEN`. Labels are fine: they go through the issues REST API with `issues: write`. |
| 4 | **Refused renames create duplicates** | The seeder renames title A to title B, the rename is refused (trap 3), the create loop then sees no thread titled B and creates one. Nine duplicates in one run. | `rename_threads` returns the refused set and the create loop skips those titles. The user deleted the nine by hand: there is no delete without a PAT and the classifier blocks the mutation anyway. |
| 5 | **No API for Discussion categories** | Nothing creates, renames, describes or gives an emoji to a category. Polls too. The seeder skips a thread whose category is missing rather than misfiling it. | Categories are the one browser step. Give the user the URL `https://github.com/OWNER/REPO/settings/discussions` and the exact list. Name categories without dots so the slug is predictable (`LAB Simulator` becomes `lab-simulator`). |
| 6 | **Projects v2 boards belong to the account** | The built-in token cannot create one. `createProjectV2` is refused; `create_boards` warns and the run still goes green. | A PAT with the classic `project` scope, or fine-grained account permission Projects read/write, stored as the `PROJECT_TOKEN` secret. Discussions cannot be board items; mirror them as draft items. |
| 7 | **Green run, nothing created** | Provision `boards` completed with success and no board existed. The step swallowed the refusal into a warning. | Never report a step done from the run status. Read the surface back (`references/verification.md`). Keep the seed log as an artifact so it can be read on a restricted network. |
| 8 | **GraphQL rate limit during a board sync** | `RATE_LIMIT` at the sync step. Secondary limit is roughly 80 mutations a minute; the hourly quota resets at the top of the hour. | `gh.py` recognises it and prints the reset time. Do not click again before the printed time. Schedule board syncs off the hour and never run two in the same minute. |
| 9 | **"N of N required status checks are expected"** | Reads as "checks are running". It also means the branch is behind the base with strict protection on. | `merge_pr.py` updates the branch through the API and waits on the new head. An empty check list means pending, not passing. A required context that is absent counts as pending. |
| 10 | **A required check whose workflow is `paths`-filtered** | The check never reports on a PR outside those paths, shows "Expected" forever, and only an admin bypass merges. Invisible for a day because every merge was a bypass. | Every required context must come from a job that runs on every pull request. `tests/test_workflows.py` enforces it. |
| 11 | **Actions token answers 403 on `GET /user`** | Preflight treated it as a bad token, so provisioning only ever worked with a PAT. | An installation token has no user identity. Fall back to `GET /repos/{o}/{r}`; if that answers, the token is fine. |
| 12 | **The proxy strips `X-OAuth-Scopes`** | An empty scopes header from a Claude Code session is not evidence the PAT lacks a scope. | The one place that settles scope is the PAT's own settings page. Say so instead of guessing. |
| 13 | **A guard that makes a failure unrecoverable** | Seeding ran only when `scripts/seed*` changed. The one run with a change failed; every later push correctly reported "nothing changed" and skipped. Content stayed unseeded for weeks. | Run the idempotent step every time. The steady-state cost is one listing query. |
| 14 | **Heredoc inside a heredoc** | A `<<'PY'` block inside a `<<'MSG'` commit message put Python source into three commit messages and skipped a PR creation. | Write the message to a file first, then `git commit -F file`. Write PR bodies to a file too. |
| 15 | **`| tail` hides the exit code** | A CI step that failed locally looked green because the pipe's status was `tail`'s. | Run each CI job's steps locally as CI runs them, and check `${PIPESTATUS[0]}` or drop the pipe. |
| 16 | **Running most CI steps locally, not all** | The devcontainer pick-list check ran only in CI. The PR went red after everything else passed. | Every CI step has a local mirror in pytest. Add one when you add a step. |
| 17 | **A derived number with no command** | A retracted finding survived in five files, then six more were found by a repo-wide guard. | A number in prose is pinned by a test that regenerates it, or it does not ship. A claim repeated across files gets a repo-wide test. |
| 18 | **The grader can be told what to say** | An empty attempt, a syntax error and `os._exit(0)` all graded as passes on four units. | `emit()` exits non-zero when no check ran; the grader requires the `LABSIM_RESULT` block; every unit ships decoys that must fail; `selftest` grades the graders. |
| 19 | **Pinned answer keys drift** | A drill's key was wrong in its own first draft. | Compute the key where possible (run the candidates). Where it must be pinned, a test ties it to the note that regenerates it. |
| 20 | **A classifier block treated as a detour** | The permission classifier refused writing a `deleteDiscussion` mutation. The temptation is to do it another way. | Stop. Tell the user what was refused. It is the user's call, and routing around it is the one thing that makes the grant indefensible. |
| 21 | **Token pasted into chat** | A PAT in a transcript is stored outside GitHub. | Say once that it should be rotated. Record the recommendation and stop raising it. |
| 22 | **`pull_request_target` style triggers with untrusted code** | Grading a stranger's Python with a token in scope is a credential theft primitive. | Three jobs: route (no code), grade (`permissions: {}`, no secrets, `persist-credentials: false`, hard timeout), respond (write scope, no untrusted code, sanitised artifact). Never interpolate event payload into a shell; pass `$GITHUB_EVENT_PATH` by path. |
| 23 | **Discussion form `labels:` naming a label that does not exist** | The form applies nothing, silently. `question` is a GitHub default that the seeder deletes. | Forms name only labels in `seed_content.LABELS`. A test checks each form's labels exist. |
| 24 | **Re-reading a PR head once, before the loop** | A merge attempted straight after a push judged the previous commit's red check. | Re-read the PR every iteration. Pass `--expect-head` with the pushed sha. |
| 25 | **Notebook outputs committed** | Unreadable diffs; CI refuses. | `make strip` before commit. CI checks it. |
| 26 | **The missing-PAT warning keyed on the wrong word** | Provision's "Choose a token" step warned only when the steps string contained `project`. A `boards` run without `PROJECT_TOKEN` produced no annotation at all, and the run was green (found 2026-09-02 by an eval of this skill). | The case pattern is `*project*|*boards*`. Any step that needs the PAT must be in that pattern; `tests/test_workflows.py` checks it. |

## Habits that prevent the next row

- Dry-run everything that mutates: `--dry-run` exists on every seeding entry point and on
  both board syncs. Use it first, read the plan, then run for real.
- Use a scratch copy (`git archive HEAD | tar -x -C scratch`) to rehearse a patch script
  before running it on the working tree.
- After any seeding run, call `all_discussions()` and diff titles against the seed. Count,
  do not assume.
- Write the verification step before the provisioning step. If you cannot say how you will
  prove it worked, you are not ready to run it.
