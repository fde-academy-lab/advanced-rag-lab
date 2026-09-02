# The L.A.B. Simulator, for someone provisioning or extending it

Full docs in the reference repository: `lab-simulator/README.md`, `lab-simulator/DISCUSSIONS.md`,
`docs/10-community/hands-on-roadmap.md`. This is the contract.

## The shape

- A **unit** is 25 to 45 minutes, a real corpus, three gates. Seven ship.
- A **drill** is 5 to 15 minutes, one idea, one check that carries it. Nine ship. Ids are two
  letters plus a digit (`RD2`); units are one letter plus a digit (`R3`).
- **Modes**: `implement` (fill the blanks), `diagnose` (fix the planted bug), `answer`
  (commit to a number or a choice before you look), `decide`, `measure`, `ship`.
- **Prerequisites** form a DAG; `/status` and `/progress` show what is unlocked.
- Three surfaces, one grader: CLI, Codespaces, a discussion thread. All run
  `python -m labsim check` on the same units.

## A unit directory

```
lab-simulator/units/<ID>-<slug>/
  unit.yaml            id, slug, title, kind, track, difficulty, minutes, mode, teaches,
                       prereqs, bars, reading, on_fail (check, work_on, read), summary
  BRIEF.md             the task, with at least two ### Hint sections
  starter.py           or answer.template.yaml for answer mode
  check.py             built on labsim.checkkit; prints pass/FAIL lines and LABSIM_RESULT
  SOLUTION.md          the worked answer, unlocked by /solution after a clear
  reference/pass/      a solution the grader must accept
  reference/fail-*/    decoys, each with expect.yaml naming the check that must catch it
```

## The grader contract

- `check.py` loads the attempt with `checkkit.load_solution` or `load_answer`, runs named
  checks through a `Checker`, and ends with `return emit(metrics, checker)`.
- `emit()` exits non-zero when any check failed **or when no check ran**. A missing or
  unparsable file is a fail, not a pass. This was a real hole: an empty attempt graded as a
  pass on four units.
- The grader requires the `LABSIM_RESULT` block. A check that exits 0 without printing it is
  a failure.
- `python -m labsim validate` checks every unit's metadata: kind, minutes cap for drills,
  answer template exists, `on_fail` read paths exist, id and title present.
- `python -m labsim selftest` grades every `reference/pass` and every decoy. A decoy that
  passes fails the build. This is how the graders are graded.

## Answer keys

Compute the key when you can: `FD1` runs the three candidate chunkers rather than trusting a
number, and that caught a wrong key in the drill's own first draft. When a key must be pinned
(`RD2`, `XD1`, `ED2`), add a test in `tests/test_measurements.py` tying it to the measurement
note that regenerates it.

## The reply

Assembled from unit metadata only: check names, `teaches`, per-check `on_fail` notes,
`reading`, what is unlocked next. Nothing generated. Each `on_fail` sentence was written by
whoever wrote the check. Keep it that way; a fluent generated paragraph is less true.

## Adding a drill for a cohort

1. Copy the closest existing drill. Fifteen minutes of authoring is the budget.
2. Write the decoy first. If you cannot name the wrong answer the check must catch, the
   check is not carrying an idea.
3. `validate`, `selftest`, then add the id to `.github/DISCUSSION_TEMPLATE/lab-simulator.yml`
   and regenerate `.vscode/tasks.json`; both have tests that fail until you do.
4. Label metadata (`kind`, `difficulty`, `track`) is what the bot applies to the thread.

## What not to build

- A leaderboard. `labsim badge` gives a paste-able line from what was actually cleared.
- LLM-written feedback. See "The reply".
- Hints before a first attempt. Proposed, and the mechanism is in the roadmap; not built.
