# Your attempts live here

`labsim start R1` scaffolds `attempts/R1/`. Work there, run `labsim check R1`, and commit when
you want it graded on a pull request.

Nothing in this directory is gitignored, and that is on purpose. On this pathway a completed
unit is a commit: the diff is the record of what you tried, the pull-request comment is the
grade, and a reviewer can see the reasoning in `decision.yaml` next to the code it produced.

`progress.json` accumulates here as you go — attempts per unit, seconds per attempt, and the
date each one first cleared. It is the honest version of a streak counter: it also records the
units you have opened four times and not finished.

## Working through this in a fork

Fork, work on a branch, open the pull request against **your** fork. The grading Action runs
there exactly as it does here — it needs no secrets and no token beyond the one GitHub hands
every workflow.

Open a pull request against this repository only if you are contributing a *unit*, not an
attempt.
