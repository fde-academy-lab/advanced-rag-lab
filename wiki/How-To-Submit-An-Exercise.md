# How to submit an exercise and get a review

**Takeaway:** a submission is a number with an interval and the command that produced it. Words
about the number are optional; the number is not.

1. Pick the exercise in the
   [catalogue](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/03-exercises/catalogue.md).
   Each brief names the metric it moves.
2. Post your **approach** in
   [Exercises & Submissions](https://github.com/fde-academy-lab/advanced-rag-lab/discussions/categories/exercises-submissions)
   before writing code. The form has a field for it. A peer or a maintainer will usually poke at
   the approach within a day, which is cheaper than poking at the code.
3. Do the work in a Codespace or locally. Run `python scripts/run_eval.py` before and after.
4. Reply on your own thread with the table: before, after, delta, and the 95% interval that
   `run_eval.py --compare` prints. Paste the command. If the interval crosses zero, say so;
   that is a result, and it earns full credit under the `negative-result` label.
5. **Owe one review before you ask for one.** Find another open submission and leave a comment
   that names one thing that is strong and one thing to fix. That is the house rule.

**Done when:** a maintainer marks the answer on your thread, or your table is quoted in the
Friday standup.

Full workflow: [docs/10-community/exercise-workflow.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/10-community/exercise-workflow.md).
