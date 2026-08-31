# GitHub setup

Everything this repository needs on GitHub — the repository itself, settings, labels,
milestones, seeded issues, Discussions, the project board, and the push of the phased
history — is provisioned by one script, from your machine.

```bash
export GITHUB_TOKEN=github_pat_...
python scripts/setup_github.py --owner OWNER --repo nanorag
```

Preview it first with `--dry-run`; it prints the full plan and changes nothing. The script is
**idempotent** — anything that already exists is skipped rather than duplicated — and every
step fails independently, so a token without Projects access still gets you the other six.

| Step | What it does | Needs |
|---|---|---|
| `create` | Creates the repository, public by default (`--private` to change) | REST |
| `settings` | Description, homepage, 16 topics, squash-only merges, branch protection | REST |
| `labels` | 26 labels across type / area / phase / difficulty | REST |
| `milestones` | P0–P7, the eight delivery phases | REST |
| `issues` | 15 issues — 8 closed real defects with their fixes, 7 open | REST |
| `discussions` | 17 seeded threads across 7 categories | **GraphQL** |
| `project` | Projects v2 board, 5 custom fields, every issue placed | **GraphQL** |
| `push` | Adds `origin`, pushes `main` with its 20 phased commits | git |

### If you cannot run this from a terminal

An account you can only reach in a browser can still provision itself, because an Actions
runner has the network access and the credentials that your laptop is missing.

1. Create the repository and push (or have someone push) — this is the only part a runner
   cannot bootstrap, since the workflow has to already be in the repository to run.
2. Create the three Discussion categories in Settings ▸ Discussions.
3. **Actions ▸ Provision GitHub surface ▸ Run workflow**, pick the steps, run it.

The `discussions` step works on the built-in `GITHUB_TOKEN`; the workflow requests
`discussions: write` and needs nothing else configured.

The `project` step does not, and the reason is worth knowing: a Projects v2 board belongs to
the **account**, not to the repository, and the built-in token is scoped to the repository —
no permissions block can widen it. Add a PAT with account-level Projects: read/write as a
repository secret named `PROJECT_TOKEN` (Settings ▸ Secrets and variables ▸ Actions), then run
the workflow with `project`. Without the secret the run warns and stops rather than failing
obscurely.

### Renaming or forking

Nothing in the tree is hard-bound to an account. A handful of things genuinely cannot be
relative — CI badge URLs, the clone command, CODEOWNERS handles, `CITATION.cff`, packaging
metadata — and `scripts/retarget.py` rewrites all of them in one pass:

```bash
python scripts/retarget.py --owner your-handle                    # fork it
python scripts/retarget.py --owner your-org --repo my-rag-lab     # rename the repo
python scripts/retarget.py --owner your-org --repo my-rag-lab --package myrag   # and the package
```

With no flags it reads `git remote get-url origin` and follows that. The current identity
lives in `.identity.json`, so the script is idempotent and reversible — a round trip is
byte-identical. `setup_github.py` runs it for you before pushing, so provisioning under a
different owner never ships badges pointing at someone else's CI.

### Recommended order

The three custom Discussion categories cannot be created by any API, and a seeded thread whose
category is missing is skipped. So run it in two passes with a thirty-second detour through the
UI in between:

```bash
# pass 1 — creates the repo, pushes, does everything REST can do
python scripts/setup_github.py --owner OWNER --repo REPO --skip discussions,project

#  → Settings ▸ Discussions ▸ New category:  Design Reviews · Reading Club · Interview Prep
#  → set the Q&A category's format to "Question / Answer"

# pass 2 — the two GraphQL steps
python scripts/setup_github.py --owner OWNER --repo REPO --only discussions,project
```

Running it in one pass also works; you just re-run `--only discussions` afterwards to backfill
the threads that had nowhere to go.

---

## Why this has to run from your machine

A Claude Code cloud session is pinned by its egress proxy to the repositories configured on
that session. Two consequences, both hard limits rather than missing permissions:

- **Repository creation is not a repository-scoped call.** `POST /user/repos` and
  `POST /orgs/{org}/repos` return `sessions are bound to their configured repositories`.
  No token changes this — the block is on the URL path, before the request reaches GitHub.
- **GraphQL is limited to a pinned set of PR-review operations.** Repository Discussions and
  Projects v2 are GraphQL-only APIs with no REST equivalent, so those two steps cannot run
  from a cloud session even after the repository is attached.

Your GitHub account connection is fine and irrelevant to this. Run the script locally with an
ordinary PAT and all eight steps work.

---

## 1 · Create the repository

The `create` step does this for you. To do it by hand instead:

```bash
gh repo create fde-academy-lab/advanced-rag-lab \
  --public \
  --description "Runnable retrieval/RAG/evaluation curriculum — 10 notebooks and a toolkit that run entirely in memory, with an eval gate in CI"
```

Or at [github.com/new](https://github.com/new). **Public** is recommended — the portfolio value
in `docs/07-career/portfolio.md` depends on a recruiter being able to open it, and Discussions on a
private repo are invisible to anyone outside the org.

Do not initialise it with a README, licence or `.gitignore` — this repository already has all
three, and an initial commit on the remote means a merge before you can push.

## 2 · Push

The `push` step does this too. By hand:

```bash
cd nanorag
git remote add origin https://github.com/fde-academy-lab/advanced-rag-lab.git
git push -u origin main
```

## 3 · Get a token

A **fine-grained personal access token**
([github.com/settings/tokens?type=beta](https://github.com/settings/tokens?type=beta)) scoped
to this one repository:

| Permission | Level | Needed for |
|---|---|---|
| Repository → **Administration** | Read and write | Settings, enabling Discussions, branch protection |
| Repository → **Contents** | Read and write | — |
| Repository → **Issues** | Read and write | Labels, milestones, seeded issues |
| Repository → **Discussions** | Read and write | Seeded threads and answers |
| Repository → **Pull requests** | Read and write | — |
| Account → **Projects** | Read and write | The board (optional — everything else runs without it) |

A classic PAT with `repo` + `project` scopes also works and is simpler if you are in a hurry.

Export the **actual token string**, not the placeholder:

```bash
export GITHUB_TOKEN=github_pat_11ABC...      # the full value GitHub showed you, once
curl -sS -H "Authorization: Bearer $GITHUB_TOKEN" https://api.github.com/user | head -3
```

That curl prints your account JSON when the token is good and
`{"message":"Bad credentials"}` when it is not. `setup_github.py` runs the same check itself
before it creates anything, so a bad token costs you a message rather than a half-provisioned
repository.

## 4 · Run it

```bash
python scripts/setup_github.py --owner OWNER --repo REPO --dry-run   # see the plan first
python scripts/setup_github.py --owner OWNER --repo REPO
```

Run one step at a time if you prefer:

```bash
python scripts/setup_github.py --owner OWNER --repo REPO --only settings,labels
python scripts/setup_github.py --owner OWNER --repo REPO --only discussions
python scripts/setup_github.py --owner OWNER --repo REPO --skip project
```

Steps: `create` · `settings` · `labels` · `milestones` · `issues` · `discussions` · `project` · `push`

### What it creates

| Step | What |
|---|---|
| `settings` | Description, homepage, 16 topics, Discussions + Projects on, wiki off, squash-merge only, delete branch on merge, branch protection on `main` |
| `labels` | 26 labels across three orthogonal axes; deletes GitHub's unused defaults |
| `milestones` | 8 delivery phases, P0–P7, with P0–P6 closed |
| `issues` | 15 seeded issues — 8 **closed** real defects from the build with their fixes, 7 open extensions, reading assignments and docs gaps |
| `discussions` | 17 seeded threads across 7 categories, several with answers |
| `project` | "Advanced RAG — Delivery" board with 5 custom fields, all issues added |

## 5 · Four things the API cannot do

The script prints these at the end. Budget ten minutes.

**1 · Create Discussion categories.** GitHub has no API for this. In
**Settings → Discussions → Categories**, add:

| Name | Emoji | Format | Description |
|---|---|---|---|
| Design Reviews | 🏗 | Open-ended | Post a design *before* you build it. Include your constraints and what your own design costs. |
| Reading Club | 📚 | Open-ended | Discussion of assigned papers. The assignment is an issue; the argument lives here. |
| Interview Prep | 🎯 | Question / Answer | Practise an answer and get it critiqued. Nothing under NDA. |

Also set **Q&A** to the *Question / Answer* format so answers can be marked.

Create these **before** running the `discussions` step — threads for missing categories fall
back to General, and moving them afterwards is manual.

**2 · Enable Pages.** Settings → Pages → Source: **GitHub Actions**. This publishes executed
notebooks as a browsable site, which is what you link from a CV.

**3 · Pin things.** Pin the two Announcements discussions, and 3–4 issues — the abstention
extension, HyDE, and one closed bug so a visitor immediately sees what a well-run issue looks
like.

**4 · Add a social preview image.** Settings → General → Social preview. This is what renders
when the repo is shared on LinkedIn, and it is the difference between a link people click and
one they scroll past.

## 6 · Optional — a project token for board automation

`.github/workflows/project-automation.yml` adds new issues and PRs to the board. The default
`GITHUB_TOKEN` cannot write to a user-owned Projects v2 board, so add a repository secret:

- **Settings → Secrets and variables → Actions → New repository secret**
- Name: `PROJECT_TOKEN`
- Value: a classic PAT with the `project` scope

Without it the workflow degrades gracefully — the board simply is not auto-populated, and the
`continue-on-error: true` means nothing fails.

Then edit the `project-url` in that workflow to your board's actual URL.

---

## Verifying it worked

```bash
# Labels, milestones, issues
gh label list --repo OWNER/REPO
gh issue list --repo OWNER/REPO --state all --limit 20

# Discussions
gh api graphql -f query='
  query { repository(owner:"OWNER", name:"REPO") {
    hasDiscussionsEnabled
    discussions(first:30) { nodes { number title category { name } } } } }'
```

Then open the repository and check the **Insights → Community Standards** page. It should be
fully green: description, README, code of conduct, contributing guide, licence, security
policy, issue templates and pull request template.

## Re-running after adding seed content

Add to `scripts/seed_content.py` and re-run. Existing items are matched **by title** and
skipped, so only the new ones are created.

If you change the *body* of something already created, the script will not update it — that is
deliberate, because overwriting a thread someone has replied to would be destructive. Edit it
on GitHub, or delete it and re-run.
