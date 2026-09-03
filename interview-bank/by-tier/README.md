# By tier

The same questions, grouped by the level they are asked at. Use this to calibrate: if you are
interviewing for senior and the `mid` questions are taking you ninety seconds, that is the gap.

| Tier | What is being tested | Questions |
|---|---|---|
| **screen** | Can you talk about a system in order, and write readable code under mild pressure | R1, C1 |
| **mid** | Do you know the mechanisms, and do you measure | R2, R4, C4 |
| **senior** | Do you notice the second-order failure, and do you cost your own proposals | R3, R5, E1–E4, M1, M5, S1–S3, S5, B1, B3 |
| **staff** | Do you see the failure that is invisible in aggregate, and can you say when a rule stops applying | R7, E3, M4 |

## The band boundaries, said plainly

**screen → mid.** Stops naming technologies, starts naming mechanisms. "We use Pinecone" becomes
"we retrieve candidates, then rerank, and here is what each stage costs".

**mid → senior.** Starts volunteering the failure mode of their own proposal, unprompted, and
proposes the cheap diagnostic before the expensive one. This is the largest single jump and it is
mostly a habit rather than knowledge.

**senior → staff.** Notices what a metric *cannot* see. The canonical example in this repository:
a filtered graph search can disconnect the ANN graph for restricted users, so recall collapses
for exactly the users with the tightest permissions — and nothing in an aggregate metric shows
it. Almost nobody says this, and it is the correct answer.

## Practising to a tier

```bash
python ../practice.py --tier mid --loop 5
python ../practice.py --tier senior --drill models
```

Do the tier below yours until every answer lands inside ninety seconds without effort. Time at
your own tier is wasted while the tier below is still slow, because in a real loop the easy
questions come first and eat the clock you needed later.
