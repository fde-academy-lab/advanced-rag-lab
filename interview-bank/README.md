# Interview bank

A drillable index over the question banks in [`docs/06-interview-prep/`](../docs/06-interview-prep/).

The prose banks hold the *answers*. This folder holds the **practice loop** — the machine-readable
index, the approach models, and a timer that makes you use them.

| File | What it is |
|---|---|
| [mental-models.md](mental-models.md) | Eight named procedures, each with its trigger, a worked case, and the failure it prevents |
| [questions.yaml](questions.yaml) | The machine-readable index: tier, topic, the model that fires, the trap, band signals, queued follow-ups, and a pointer to the full answer |
| [practice.py](practice.py) | Timed drill over the bank, with self-scoring and a weakest-first view |
| [by-tier/](by-tier/) | The same questions grouped by the level they are asked at |
| [drills/](drills/) | Short focused sets — one for each mental model |

## Start here

```bash
pip install pyyaml                          # or: pip install -e ".[dev]"

python interview-bank/practice.py --drill models
```

That is the drill worth doing. It shows a question, makes you **name which mental model fires
before you answer**, times you at ninety seconds, then shows the trap, the band signals and the
follow-ups the interviewer has queued.

```bash
python interview-bank/practice.py --loop 5                 # five in a row
python interview-bank/practice.py --topic evaluation       # one topic
python interview-bank/practice.py --tier staff             # the hard ones
python interview-bank/practice.py --weakest                # where to go next
```

Your scores go to `.progress.json`, which is gitignored. It is yours, not the repo's.

## Why a timer

The failure at senior level is almost never ignorance. It is a candidate who knows the answer,
takes ninety seconds to organise it out loud, and runs out of clock before the follow-up where
the marks are.

That is a timing skill, and it only improves under a timer. Reading the questions does not fix it
and neither does knowing more.

## Why this is an index rather than a second copy

Every entry points at the heading in the prose bank where the full answer lives. There is one
copy of each answer, and `tests/test_interview_bank.py` asserts that **every pointer resolves** —
file exists, and the heading anchor still matches GitHub's slug algorithm.

That test earned its place immediately: it caught an anchor drift and a heading whose anchor
contained a Greek letter, which is a link nobody can type.

## What is in the bank

21 questions across six topics and four tiers, with 43 queued follow-ups. It is deliberately not
a hundred questions — a bank you can work through in a week and revisit is worth more than one
you skim once.

| Topic | Where the answers live |
|---|---|
| retrieval | [retrieval.md](../docs/06-interview-prep/retrieval.md) |
| evaluation | [evaluation.md](../docs/06-interview-prep/evaluation.md) |
| mathematics | [mathematics.md](../docs/06-interview-prep/mathematics.md) |
| systems-design | [systems-design.md](../docs/06-interview-prep/systems-design.md) |
| coding | [coding.md](../docs/06-interview-prep/coding.md) |
| behavioural | [behavioural.md](../docs/06-interview-prep/behavioural.md) |

Full timed loops with an interviewer script are in
[mock-loops.md](../docs/06-interview-prep/mock-loops.md).

## Contributing a question

Open a thread in **Discussions → Interview Prep** with the question and what you were asked
next — the follow-up is the valuable half and it is the half that never gets written down.

A question earns a place in the bank when it has: a **trap** that catches a competent person, at
least two **band signals** that are genuinely distinguishable, and a **follow-up**. A question
with no follow-up under-trains you, because the follow-up is where the assessment happens.

Nothing here is under anyone's NDA, and nothing should be. If you cannot describe a question
without naming the company and the product, do not post it.
