# Measurements

Comparisons between configurations. Each note carries the exact command that regenerates it, the
paired-bootstrap intervals, and the date it was measured.

| Note | Question | Command |
|---|---|---|
| [fusion-rules.md](fusion-rules.md) | Which fusion rule, and does fusion pay at all? | `python scripts/run_eval.py --compare` · `python scripts/failure_overlap.py` |
| [multi-hop-independence.md](multi-hop-independence.md) | Are multi-hop failures correlated, or just multiplied? | `python scripts/independence.py` |

The k grid lives in [metrics.md](../../04-evaluation/metrics.md) rather than here,
because it describes one configuration across a parameter rather than configurations
against each other: `python scripts/run_eval.py --ksweep`.

## What belongs here

A note belongs here when it compares **configurations against each other**, which the eval gate
structurally cannot do — it compares one configuration against its own history. A note that
tracks a single configuration over time is the gate's job and belongs in
`.github/eval-baseline.json`.

## The rules

1. **The command comes first.** If a reader cannot regenerate the table in one line, the note is
   an assertion rather than a measurement.
2. **Intervals, not means.** A table of means cannot distinguish a gap that would survive a
   corpus refresh from one that would not, and the difference between those two is the entire
   decision.
3. **Say what it does not say.** Every measurement here is conditional on this corpus, this
   encoder and this question mix. The note names the condition under which the answer flips.
4. **Date it, and re-run it when the corpus, the encoder or the question mix moves.** A finding
   is a measurement with an expiry date, not a fact.
