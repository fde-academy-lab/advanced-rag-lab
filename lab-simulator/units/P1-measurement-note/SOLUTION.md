# P1 · How we did it

The worked note is [`reference/pass/measurement.md`](reference/pass/measurement.md). Read it
against your own before reading this. What follows is why each part of it is shaped the way it
is, and what the three graded decoys are.

## The check no other unit has

The grader re-runs the measurement and compares your numbers to it.

That is unusual for a writing exercise and it is the whole unit. Format can be satisfied by a
careful writer who never ran anything, and the failure this unit exists to prevent was not a
format failure. It was a **correct-looking note whose numbers had drifted from the code**, and it
survived for months because the structure was impeccable.

`reference/fail-numbers-do-not-match-the-run/` is that failure, reproduced honestly: every
section present, the reasoning sound, the conclusion right, and `0.7745` where the run says
`0.7709`. It was written a day later from memory. That is how it happens — not through
dishonesty, through a gap between the terminal and the document.

## The four things the note has to do, and why each one

**Carry a command.** One line, paste-able, naming something in this repository. This is the
sentence the whole unit turns on:

> A claim you cannot re-run in one command is a claim nobody will re-run.

`reference/fail-no-command/` has correct numbers, correct reasoning and a correct condition, and
describes its provenance in prose: *"ran the R3 grader locally and read the metrics off the JSON
output"*. Everything a careful reader needs, except the thing that makes them a *re-runner*
rather than a reader. In four months that note is folklore.

**Carry a date.** A measurement without one cannot be known to be stale, and staleness is the
only way measurements go wrong quietly. Nobody ever notices a number is old; they notice a number
is *wrong*, which is months later and after it has been quoted.

**Quote intervals, or say you did not compute one.** `reference/fail-means-without-intervals/`
has every number right and writes *"a small lead but it is consistent"* about a difference of
`+0.0036` on 207 questions. That sentence is what a difference inside the noise band sounds like
when nobody computed the band. It is not a lie and it is not sloppy — it is the ordinary way
complexity gets shipped.

Notice what the worked note does instead. It says plainly that it did not compute a bootstrap
inside that run, cites the repository's own interval for the same comparison, and then declines
to claim anything:

> "The difference I measured is the same size as the difference already known to be inside the
> noise band. I am not claiming a gain and I am not claiming a loss."

Saying "I did not measure that" is available, costs nothing, and almost nobody does it.

**Name the condition.** Two specific ones, both falsifiable: a dense encoder whose failures stop
being nested inside BM25's, and an identifier slice past roughly a fifth of traffic. "This may
not generalise" is a hedge; "here are the two changes that would flip it" is a handover.

## The sentence to steal

> "The more useful list here is the one that did **not** clear."

Every result table has two lists in it — the comparisons that beat the noise band and the ones
that did not — and almost every write-up prints only the first. The second is where the decisions
are: it is the list of things you are *not* going to build, each one with a number attached, and
it is the only defence a team has against re-litigating the same idea every quarter.

## Where this sits in the delivery lifecycle

You have now produced three artefacts without anyone naming them as a process:

- **R2** — a decision record. Written *before* the code, so it is a decision and not a
  rationalisation.
- **R3** — a measurement. A number from a run, not an impression from a demo.
- **P1** — a note that outlives you. The measurement, made contestable.

That sequence is most of what an engagement leaves behind. Not a plan and a status report — a
decision somebody can disagree with, a number somebody can reproduce, and a document that tells
a stranger how to do both.

The PDLC vocabulary for these — decision record, measurement, acceptance criterion — is worth
knowing and is not worth leading with. What makes an FDE useful is that these exist, in that
order, because each one prevents a specific failure. Naming the process does not prevent
anything.

## What we got wrong first

**We wrote the note before deciding who it was for.** The first version explained what RRF is.
The reader of a measurement note is not learning retrieval — they are deciding whether to trust a
conclusion, or trying to work out whether it still holds. Everything that is not the numbers, the
mechanism or the condition is in their way.

**We buried the condition at the bottom in a paragraph titled "Caveats".** Nobody read it. Under
"What this does not say", with two specific falsifiable changes and no hedging language, people
read it and — twice — came back with "the second one is about to happen, should we re-run?"

That is the note working.

## Where this lives in the real system

`docs/09-research/measurements/` is this artefact at repository scale, with the rules stated in
its [README](../../../docs/09-research/measurements/README.md). Its existence is a direct
consequence of [ADR-0015](../../../docs/01-architecture/adr/0015-correct-the-fusion-finding.md):
the eval gate compares a configuration against its own history and never against alternatives, so
every claim of the form *"X beats Y"* sat outside what CI could check, and had nowhere to live
that carried its own reproduction command.

## What this unlocks

**P2** points the same discipline forwards: the acceptance criterion — a number, a slice and a
noise band — written before the work starts, so "done" is decidable by someone other than the
person who did it.
