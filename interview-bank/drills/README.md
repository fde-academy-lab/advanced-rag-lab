# Drills

One short set per mental model. Each drill runs only the questions where that model fires, so you
practise the *trigger* rather than the content.

| Drill | Model | Questions | What you are training |
|---|---|---|---|
| `two-timelines` | 1 | R1, S1 | Splitting index-time from query-time before saying anything else |
| `name-the-denominator` | 2 | E1, E4, M5, C4, B1 | Asking n, unit of analysis and slice on reflex |
| `cheapest-diagnostic-first` | 3 | R3, E2, S2, S5 | Ordering hypotheses by cost × likelihood, out loud |
| `the-third-case` | 4 | R5 | Finding what a binary framing hides |
| `condition-not-law` | 5 | R2, M1, M4 | Converting "X always beats Y" into a conditional |
| `whose-budget` | 6 | R4, R7 | Naming what your proposal spends, unprompted |
| `what-would-make-this-false` | 7 | E3, S3, B3 | Stating the falsifier before running anything |
| `say-the-shape-first` | 8 | C1 | Opening with the count and the axis |

## Running one

```bash
python ../practice.py --drill models --loop 5
```

The `--drill models` flag makes you name the model before you answer, which is the whole point.
Getting it "wrong" against the bank is not necessarily wrong — several questions admit two models
— but you should be able to defend the one you picked, and if you cannot, that is the finding.

## The sequence that works

1. **Week one:** `--drill models` on everything, ignoring answer quality entirely. You are
   training recognition, not content.
2. **Week two:** answer for real, timed at ninety seconds, self-scored.
3. **Week three:** `--weakest`, and go read the source file for the three worst.
4. **Then:** full timed loops from [mock-loops.md](../../docs/06-interview-prep/mock-loops.md)
   with a partner.

Most people report the models stop feeling like a checklist after roughly forty questions and
start firing on their own. That is when you stop drilling models and start drilling content.
