# Session 01 · The recall budget, and what a baseline is for

**Length** 3 hours · **Notebooks** `00`, `01` · **Phase** P0–P1

## Prerequisites

`make setup` run and verified **before** the session. Post in the thread that it worked. Setup on
conference wifi is the largest schedule risk in the whole curriculum.

## Timings

| Time | What | Mode |
|---|---|---|
| 0:00–0:15 | The Client Zero brief. Read it out loud, exactly as a client would say it | Talk |
| 0:15–0:35 | Notebook `00`, Run All. Four seconds. Discuss what just happened | Live |
| 0:35–1:05 | The recall budget: where evidence is lost between corpus and answer | Talk + notebook `01` |
| 1:05–1:20 | Break | |
| 1:20–2:00 | Declaring a baseline. Everyone picks one **before** running anything | Exercise |
| 2:00–2:40 | Run it. Compare against what you predicted | Live |
| 2:40–3:00 | Why per-piece and per-question recall are different questions | Talk |

## The live demo

Run notebook `00` end to end in front of them. Four seconds, no API key, no download. The point
lands physically in a way a slide cannot: *the whole system is here and it runs.*

Then break it. Change `k` from 8 to 2, re-run, watch recall fall. Change it to 20, watch recall
rise **and** context precision fall. That five-minute demonstration is the entire recall/precision
tradeoff and it does not need a diagram.

## The exercise: declare a baseline

Everyone writes down, before running anything:

1. Which configuration they are calling the baseline.
2. Why that one.
3. What they predict evidence recall will be, to one decimal place.

Then they run it. The prediction is the point — a cohort that predicts 0.9 and measures 0.76 has
learned something about the difficulty of the corpus that no explanation transmits.

**Facilitator note:** at least one person will pick the best-scoring configuration as the
"baseline" after seeing the numbers. Name it, without embarrassing them. A baseline chosen after
the fact is just the second-best result, and this is the most common self-deception in applied
retrieval work.

## Discussion prompt (post 24 h ahead)

> Before the session: what would you need to see to believe a retrieval system is working? Write
> your answer before reading anyone else's.

## Exit check

Each participant can state: **their baseline configuration, its evidence recall to four decimals,
and one reason that number is not comparable to anyone else's on a different corpus.**

That third clause is the one that matters. It is the difference between a number and a benchmark.

## Common failure in the room

Somebody asks why answer correctness is only 0.41 and concludes the system is broken. It is not —
the eval set contains multi-hop chains and 36 deliberately unanswerable questions. Have the answer
ready, because if it goes unaddressed the room spends the rest of the day distrusting every number
you show them.
