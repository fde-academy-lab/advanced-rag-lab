# What GitHub will not let you automate

Verified against `fde-academy-lab/advanced-rag-lab` up to 2026-09-02. Check the dated row in
`traps.md` before trusting any line here for a feature GitHub may have changed.

## No API at all (browser only)

| Surface | What is missing | Manual step, with the URL to hand over |
|---|---|---|
| Discussion categories | Create, rename, description, emoji, format (open, Q&A, announcement) | `https://github.com/OWNER/REPO/settings/discussions` then "New category" for each row in `discussions-design.md` |
| Polls | Creating a poll discussion | Open the Polls category in the browser and post it |
| Pinned discussions | Pinning is a GraphQL mutation (`pinDiscussion`) but the Actions token was not tested for it; treat as manual | Thread page ▸ "Pin discussion" |
| Projects v2 views | Board, table and roadmap layouts, column grouping, filters | Board page ▸ "New view". The seeder creates the project and its fields; the human arranges views |
| Project visibility | Public or private for a user-owned project | Project ▸ Settings ▸ Visibility |
| Linking a board to the repository | `linkProjectV2ToRepository` exists in GraphQL but the seeder does not call it; treat as manual | `https://github.com/OWNER/REPO/projects` ▸ "Link a project" |
| Wiki first page | The wiki git remote does not exist until a first page is created in the browser | `https://github.com/OWNER/REPO/wiki` ▸ "Create the first page". After that, `git clone https://github.com/OWNER/REPO.wiki.git` works and pages are markdown files |
| Codespaces prebuilds | Enabling prebuilds for a branch | `https://github.com/OWNER/REPO/settings/codespaces` |
| PAT scopes | Reading which scopes a token carries, through this proxy | The token's own settings page at `https://github.com/settings/tokens` |
| Discussion category for a form | A form file is keyed to a category by slug; the category must already exist | Create the category first, with the exact name the form expects |

## Has an API, but the built-in Actions token cannot do it

| Operation | Why | Token that can |
|---|---|---|
| `createProjectV2`, add or update project items | A project belongs to the account, the token to the repository | PAT with `project` scope (classic) or account Projects read/write (fine-grained), stored as `PROJECT_TOKEN` |
| `updateDiscussion` on a thread the bot did not open | Ownership | The same PAT, from the Provision workflow |
| `deleteDiscussion` | Ownership, and the auto-mode classifier refused to write the mutation from a session | A human in the browser |
| Creating a repository | Installation token is scoped to one repository | PAT with `repo`, or the browser |
| Branch protection | `Administration` permission | PAT with `repo` (classic) or Administration read/write (fine-grained) |
| Workflow dispatch from a Claude Code session | The egress proxy answered 403 | The browser: `https://github.com/OWNER/REPO/actions/workflows/NAME.yml` ▸ "Run workflow" |

## Works, and is the backbone

| Operation | Endpoint | Notes |
|---|---|---|
| List discussions | GraphQL `repository.discussions` with pagination | `setup_github.all_discussions()` |
| Create a discussion, comment, mark answer | GraphQL mutations | Built-in token with `discussions: write` |
| Labels on a discussion | REST `POST /repos/{o}/{r}/issues/{n}/labels` | Discussions share the issues label endpoint; needs `issues: write` |
| Labels, milestones, issues | REST | `setup_github.py` |
| Collaborators | REST `PUT /repos/{o}/{r}/collaborators/{login}` with `permission` | `pull`, `triage`, `push`, `maintain`, `admin` |
| Rate limit | REST `GET /rate_limit` | Free call; `gh.rate_limit_reset()` |
| Merge, update branch | REST `PUT /pulls/{n}/merge`, `PUT /pulls/{n}/update-branch` | `merge_pr.py` |
| Check runs for a commit | REST `GET /commits/{sha}/check-runs` | Empty list means pending |

## Limits worth knowing

- Label description: 100 characters.
- Secondary rate limit: about 80 mutations a minute on GraphQL. Back off, do not retry hot.
- Hourly quota observed on the reference account: 15000 core, 10000 GraphQL points. Board
  syncs burn points per item; keep sync windows small.
- Discussion body: large, but the bot sanitiser strips mentions and foreign HTML comments.
- `workflow_dispatch` `choice` inputs must list every allowed value; there is no free text
  for a choice.
