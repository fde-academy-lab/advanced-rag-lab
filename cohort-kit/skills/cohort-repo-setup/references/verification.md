# Verification: proving a step worked

A green run is a fact about the runner, not about the repository. Every step below reads the
surface back. Run them all before the handover; paste the counts into it.

```bash
export GITHUB_TOKEN=...   # in the human's terminal, or the session's env
O=OWNER; R=REPO
```

| Surface | Read it back | Expect |
|---|---|---|
| Repository | `GET /repos/$O/$R` | `has_discussions: true`, `has_projects: true`, `delete_branch_on_merge: true`, `visibility` as intended |
| Branch protection | `GET /repos/$O/$R/branches/main/protection` | `required_status_checks.contexts` equals `setup_github.REQUIRED_CHECKS`, `strict: true` |
| Labels | `GET /repos/$O/$R/labels?per_page=100` | Every name in `LABELS + DISCUSSION_LABELS`; no description over 100 characters |
| Milestones | `GET /repos/$O/$R/milestones?state=all` | The eight phases plus one per cohort week with a `due_on` |
| Issues | `GET /repos/$O/$R/issues?state=all&per_page=100` | 15 seeded; the tracking issue "Unanswered questions" once the alert has run |
| Discussion categories | `all_discussions()` and group by category, or the browser | 14 names, exact spelling |
| Threads | `python -c "from setup_github import all_discussions; ..."` | Every seed title present exactly once. Zero duplicates. Every thread carries the labels in `THREAD_LABELS` |
| Forms | Open a new discussion in each category in the browser | The form appears; the dropdown in LAB Simulator lists every unit |
| Bot | Post a drill from the form, wait two minutes | A reply with named checks; `/help` answers; the thread gets `drill` and `difficulty:` labels |
| Boards | `https://github.com/$O?tab=projects` and each workflow's "Sync the board" step | Four boards; item counts match the printed table |
| Boards linked to the repository | `https://github.com/$O/$R/projects` | All four listed; otherwise they exist only on the account page |
| Hands-on board visibility | The board's Settings page | Private, or the opt-in thread exists |
| Housekeeping | The run on the last push to main | Branches job green; seed log artifact present; "would create 0" or a list you expected |
| Pages | `https://$O.github.io/$R/` | The site renders |
| Calendar | Subscribe to the raw `.ics` URL in a calendar app | Sessions appear on the right days in the right timezone |
| Collaborators | `GET /repos/$O/$R/collaborators` and `/invitations` | Every person in `cohort.yaml` with the right role, or a pending invitation |

## From a restricted session

When GraphQL is refused, the discussion checks go through the REST listing
`GET /repos/$O/$R/discussions` (works, paginated) and the counts still come from code, not
from a screenshot. When the browser is the only tool, the human reads the URLs above and
reports the numbers; write them into the handover as "reported by the user".

## The handover format

```
Verified on YYYY-MM-DD HH:MM UTC against https://github.com/OWNER/REPO

| Surface | Expected | Found | Status |
|---|---|---|---|
| ... | ... | ... | ok / short / not checked (why) |

Left for a human, with the URL:
1. ...

Week-one checklist: (from PLAYBOOK.md, dated)
```

The first line of the message says whether anything is unverified.
