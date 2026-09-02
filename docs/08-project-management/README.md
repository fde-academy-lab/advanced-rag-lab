# 08 · Project management

The repository is run the way a delivery team runs one, and this folder is the operating
manual for that. It is here to be copied, not admired.

| File | What it covers |
|---|---|
| [board.md](board.md) | The board: fields, views, what each column means, what moves a card |
| [phases.md](phases.md) | P0–P7, with entry and exit criteria per phase |
| [ceremonies.md](ceremonies.md) | Standup, review, retro, and what each produces as an artefact |
| [definition-of-done.md](definition-of-done.md) | The checklist a card passes before it can leave In Review |
| [lifecycle.md](lifecycle.md) | The seven-phase lifecycle this project actually ran, as a board, with the artefact that proves each practice and where the named AI-delivery frameworks fit |
| [github-setup.md](github-setup.md) | Provisioning the repository surface, by script or from the Actions tab |

A card does not move because someone felt it had progressed. It moves because a stated exit
criterion is met, and the criterion is written on the card before the work starts.

## The four boards

| Board | Items | Kept current by |
|---|---|---|
| **Advanced RAG — Delivery** | Issues and pull requests, the work | `project-automation.yml` on open / close / label |
| **L.A.B. Simulator — Hands-on** | One draft item per learner: attempts, clears, retries, hints, open units, stage. Sorted by login; no score | `labsim-progress.yml`, Mondays. Reads the grading bot's own replies |
| **Discussions — Pulse** | One draft item per thread that moved this week: heat, comments, people, needs-an-answer. One item per week of content changes | `discussions-pulse.yml`, daily |
| **Project Lifecycle** | Nineteen practices in seven phases, each with the artefact that proves it | Seeded once by `setup_github.py --only boards`; content, not activity |

A discussion cannot be a Projects v2 item — only issues, pull requests and draft items can — so
the two activity boards mirror threads and learners as draft items keyed by title. All three
new boards need `PROJECT_TOKEN`: a board belongs to the account, and the built-in token cannot
write to one.

**Before the first cohort, decide whether the Hands-on board is public.** It counts attempts and
retries by name. That is tracking, not ranking, but on a public repository it is still a
person's record. Make the project private, or make joining it opt-in.
