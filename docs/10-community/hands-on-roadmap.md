# Hands-on: what is built, what is next, and why

This page is the answer to *"how do we make the hands-on experience more useful with less
friction"* — written as a peer would write it, with the ideas ranked by what they cost and what
they change, and the built ones marked as built. Nothing here is a wishlist; every proposed item
names the mechanism and the reason it is not built yet.

## The design that everything below sits on

Three surfaces, one grader. Codespaces for people who want an editor, a discussion thread for
people who will never clone, and the CLI for everyone else — all running `python -m labsim
check` on the same units. A unit is trustworthy because it ships a worked answer the grader
must accept and decoys it must reject, and `labsim selftest` grades the graders.

That last sentence is the load-bearing one. Everything in this page that grades a learner is
only as honest as the reference cases behind it, which is why the drills below each carry at
least one decoy and why the audit that found the grader could be told what to say is written
up in the [ADR](../01-architecture/adr/) index rather than fixed quietly.

## Built

| | What | Why it earns its place |
|---|---|---|
| ✅ | **Drills** — 9 of them, 5–15 minutes, tagged `easy / medium / hard`, in the same prerequisite graph as the units | A first evening can be four short clears. The pathway now starts in six places, not two |
| ✅ | **`answer` mode** — commit to a number, a ranking or a choice *before* opening the note; the grader tells you how far off you were | Calibration. The distance between the prediction and the measurement names the model of the system you were carrying. `RD2` is the retracted fusion finding turned into eight minutes of practice |
| ✅ | **Computed keys** where possible | `FD1` runs the three candidate chunkers rather than trusting a key — and that caught a wrong key in the drill's own first draft. Where a key must be pinned (`RD2`, `XD1`, `ED2`), `tests/test_measurements.py` holds it to the note that regenerates it |
| ✅ | **A reply that says what to work on** — `teaches`, per-check `on_fail` notes, `reading`, and what is unlocked, every sentence from the unit's metadata | Specific without being generated. Each `on_fail` line was written by whoever wrote the check |
| ✅ | **`/why <check>`** and **`/progress`** | One check explained in a sentence; one person's own picture and what is unlocked, with nobody else's row |
| ✅ | **Auto-labels on the thread** — `drill`/`unit`, `difficulty:`, `area:`, `cleared` | `label:drill label:"difficulty: easy" -label:cleared` is a to-do list |
| ✅ | **The Hands-on board** — one draft item per learner: attempts, clears, retries, hints, open units, stage | Tracking, not ranking. Sorted by login; no score column |
| ✅ | **The Pulse board** — one item per thread that moved this week: heat, comments, people, needs-an-answer; one item per week of content changes | A facilitator's queue. "Needs an answer" is the column to read first |
| ✅ | **The Lifecycle board** — seven phases, nineteen practices, each with the artefact that proves it and the file here that embodies it | The shape this project actually ran, laid out so the next one can be run against it |
| ✅ | **The grader cannot be told what to say** | An empty attempt, a syntax error and `os._exit(0)` used to grade as passes on four units. Fixed, with tests that fail without the fix |

## Proposed, ranked

Each has the mechanism, the cost, and the reason it is not built yet. **Friction** is the
learner's; **cost** is ours.

### Low friction, low cost — do these next

| | Idea | Mechanism | Not yet because |
|---|---|---|---|
| 1 | **Hints unlock after the first grade** | `/hint` before any grade on the thread replies "post an attempt first" | Needs the grade job to know thread history, and it holds no token by design. The respond job can do it; small change |
| 2 | **"Someone else is stuck where you just passed"** | When a thread clears, the reply names one open thread on the same unit whose last failure is a check you passed | The respond job can query threads. This is the single highest-leverage community mechanic here: it turns a clear into a review owed |
| 3 | **Drill of the week** in the digest | The digest already knows the unit with the lowest clear rate; pin it as the week's drill with the check that catches people | Five lines in `labsim_digest.py`. Wants a facilitator to agree it goes in Announcements |
| 4 | **`/next`** | `/progress` already computes what is unlocked; `/next` returns the single best one, same-track first, drill before unit | Trivial once `/progress` has run once in production |
| 5 | **Difficulty-adaptive next** | Cleared first try → suggest the next difficulty up; cleared on retry → same difficulty, different track | Heuristic in `render_for`; wants a week of real data to check the rule is not annoying |

### Low friction, medium cost

| | Idea | Mechanism | Not yet because |
|---|---|---|---|
| 6 | **`spot` drills from real threads** | Take a real Show-and-tell write-up (with consent), number its claims, grade "which are unsupported" | Consent and curation. The first three should be faculty-written, like `ED3` |
| 7 | **Pair mode** | Two learners on one thread; the bot grades whichever post is latest and credits both | `parse_submission` reads the first post only. Reading the latest post by either author is a small change; the `/progress` attribution is the harder half |
| 8 | **Retry ladders** | After two fails on the same check, the reply offers a smaller drill that isolates that check | Needs a `remediates:` field on drills mapping check names → drill ids. The data model is ready for it |
| 9 | **Weekly personal digest** | A Monday comment on each learner's most recent open thread: what moved, what is unlocked | One more mode on `labsim_progress.py`. Wants an opt-in, because unsolicited bot comments are noise |

### The ones to argue about

| | Idea | Why it might be wrong |
|---|---|---|
| 10 | **Badges / streaks** | Every practice site has them and this repository has deliberately declined a leaderboard. A badge is a leaderboard of one. The `labsim badge` CLI already gives a paste-able line generated from what you actually cleared, which is the honest version |
| 11 | **LLM-written feedback** | The reply is specific *because* it is assembled from metadata a human wrote. A generated paragraph would be more fluent and less true, and the whole repository is about the second property |
| 12 | **Public per-learner board** | Built, and visible. Counting attempts and retries by name on a public repository is tracking a person. It should be a **private** project, or the learner should opt in. Decide before the first cohort |

## How to add a drill

Fifteen minutes. `lab-simulator/units/<ID>-<slug>/` with `unit.yaml` (`kind: drill`, `minutes`
≤ 15, `on_fail` notes, `reading`), a `BRIEF.md` with two hints, a `starter.py` or
`answer.template.yaml`, a `check.py` built on `labsim.checkkit`, and `reference/pass/` plus
at least one `reference/fail-*/` with an `expect.yaml` naming the check that must catch it.
Then `python -m labsim validate` and `python -m labsim selftest`. Then add it to the form
dropdown — `tests/test_workflows.py` fails until you do.

An `answer` drill whose key is a measured number must pin it in `check.py` **and** add a test in
`tests/test_measurements.py` tying it to the note that regenerates it. That is not bureaucracy;
it is the reason `RD2` will still be right after the corpus changes.
