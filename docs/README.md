# Documentation

Ten numbered domains. The numbering is reading order for someone new and shelf order for
someone returning — `00` orients you, `01` explains how the thing is built, and the rest
follow the lifecycle of the work rather than the alphabet.

| | Domain | Start with | For |
|---|---|---|---|
| `00` | [Orientation](00-orientation/) | [start-here.md](00-orientation/start-here.md) | Day one. What this is, what to run, what to read |
| `01` | [Architecture](01-architecture/) | [overview.md](01-architecture/overview.md) | HLD, per-module LLDs, data model, the ten seams, 8 ADRs |
| `02` | [Curriculum](02-curriculum/) | [syllabus.md](02-curriculum/syllabus.md) | Session plans, prerequisites, delivery formats |
| `03` | [Exercises](03-exercises/) | [catalogue.md](03-exercises/catalogue.md) | 22 exercises + capstone, briefs, rubrics, submission flow |
| `04` | [Evaluation](04-evaluation/) | [metrics.md](04-evaluation/metrics.md) | What each metric means, the protocol, the release gate |
| `05` | [Operations](05-operations/) | [runbook.md](05-operations/runbook.md) | Runbook, incident playbooks, what to do when a number moves |
| `06` | [Interview prep](06-interview-prep/) | [README.md](06-interview-prep/) | Question bank by topic, with graded model answers |
| `07` | [Career](07-career/) | [portfolio.md](07-career/portfolio.md) | CV lines, LinkedIn, the 90-second walkthrough |
| `08` | [Project management](08-project-management/) | [board.md](08-project-management/board.md) | Board, phases, ceremonies, definition of done, GitHub setup |
| `09` | [Research](09-research/) | [reading-list.md](09-research/reading-list.md) | Papers with notes, 20 extension points |
| `10` | [Community](10-community/) | [discussions-guide.md](10-community/discussions-guide.md) | How Discussions work, and how exercises run through them |

## Conventions

Every folder has a `README.md` that says what is in it and what to read first — a directory
listing is not navigation.

Diagrams are Mermaid in fenced blocks, checked in CI by `scripts/lint/check_mermaid.mjs`
against **GitHub's** renderer settings rather than Mermaid's defaults. The two differ, and
the difference is why an earlier version of these docs rendered here and broke on github.com.

Relative links are checked by `scripts/lint/check_links.py`. Links to repository surfaces use
the `../../discussions/...` form, which GitHub resolves against the repository, so they keep
working through a fork or a rename.

Numbers in prose carry their interval. A delta without one is not a result, and a delta inside
the noise band is written as *inside the noise band* rather than rounded into a win.
