# How to read a measurement note without being fooled

**Takeaway:** the four questions below catch most wrong claims before you need to run anything.
The note format in this repository is built so that the answers are on the page.

1. **Which configuration?** k, fusion rule, encoder, question count. A number without them is
   not comparable with anything. The notes put them in the first table.
2. **Compared with what?** Against its own history (the eval gate) or against alternatives
   (`--compare`)? The gate is structurally unable to see that a different configuration would
   have been better; that is how "RRF loses to BM25" stood with a green gate the whole time.
3. **What is the interval?** A delta without a paired-bootstrap interval is a coin flip that
   landed. If the interval includes zero, the honest sentence is "not a difference". The fusion
   note's dense-versus-RRF delta is +0.0008 with an interval from −0.0101 to +0.0109.
4. **Do the legs fail on the same questions?** Fusion pays only when they do not. Overlap here
   is 0.9684, which is why fusion sits inside the noise band of the dense leg alone.

Then, if the note passes, run its command (see
[Reproduce any number](How-To-Reproduce-Any-Number.md)).

Worked example: [fusion-rules.md](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/09-research/measurements/fusion-rules.md),
including the correction banner at the top. The
[retraction ADR](https://github.com/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr/0015-correct-the-fusion-finding.md)
is the same story from the other side.
