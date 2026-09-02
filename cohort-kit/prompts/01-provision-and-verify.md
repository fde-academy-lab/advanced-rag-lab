# Prompt · provision or re-provision an existing cohort repository

For a repository that already exists and has the code, when something was added or something
failed. Paste into a session opened in the clone.

---

Use the `cohort-repo-setup` skill. This repository is OWNER/REPO, cohort N. `cohort.yaml` is
the source of truth.

What changed or failed: DESCRIBE (for example "added three drills", "the boards step went green
but no board exists", "renamed two threads").

1. Read `references/traps.md` rows 3, 4, 6, 7 and 8 before anything else; they cover the four ways a provisioning run lies.
2. Run `python scripts/setup_github.py --owner OWNER --repo REPO --only STEPS --dry-run` and show me the plan. Only then run it. If GraphQL is refused from this session, give me the Provision workflow URL and the exact `steps` value to pick, and wait.
3. If the change touches thread titles, confirm the rename is in `RENAMED` and that the create loop skips refused titles. Then count threads before and after with `all_discussions()`; the count must not grow by the renamed titles.
4. If a board is involved, tell me first whether the run needs `PROJECT_TOKEN`, and read the "Sync the board" step's output after the run, not the run status.
5. Verify per `references/verification.md`. Report expected versus found, with the command for each.
