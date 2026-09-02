# ED3 · solution

**Claims 2, 3 and 4 are smells. Claims 1 and 5 are sound.**

| claim | shape | why |
|---|---|---|
| 2 | `no-interval` | Both numbers are real. The delta is +0.0082, and the fusion note's paired bootstrap says every pairwise comparison on `answer_correct` is **inside the noise band**. "Reaching users" is a claim the data cannot support |
| 3 | `denominator` | Context precision divides by k. Going 5 → 10 doubles the slots and the gold set does not grow, so the fall is arithmetic. Recall rose from 0.6329 to 0.7279 on the same move. The window is retrieving *more*, not worse |
| 4 | `tuned-on-frozen` (and `no-command`) | An α chosen on the frozen slice and then reported on it is a number that has already seen its test set. And 0.35 / 0.7801 appear in no measurement note — there is no command behind them |
| 1 | sound | A command, an interval that excludes zero, the question count, the configuration |
| 5 | sound | A committed file anybody can open |

The three smells are not hypothetical. Claim 4's shape is how the original fusion finding
was reached; claim 2's is how it was defended; claim 3's is the most common misreading of the
scorecard in this repository's Q&A. ADR-0015 is the record of what each one cost.
