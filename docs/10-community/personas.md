# Personas in seeded threads

Every seeded discussion is a **worked example**, authored by the maintainers and posted from
the seeding account. Each post carries a footer saying so. Nothing here impersonates a real
student, and no post is attributed to a real person.

They are written in-voice, under consistent names, for one reason: a thread where "a cohort
member asked" and "a reviewer replied" is unreadable past four turns. You cannot follow who
changed their mind, who was wrong first, or whose objection was the one that landed. Names
carry that structure. The disclosure footer carries the honesty.

## The cast

Each persona exists to make a specific kind of contribution legible — including the mistakes,
which are the point.

| Persona | Role in the cohort | What they reliably contribute | The failure mode they model |
|---|---|---|---|
| **Priya** | Backend engineer, 6 yrs, new to retrieval | Precise bug reports with reproductions | Optimises before measuring; ships a change and then looks for the metric that justifies it |
| **Marcus** | Data scientist, strong statistics | Catches the significance error nobody else sees | Rejects results for statistical reasons when the practical answer was obvious; perfectionism as delay |
| **Wei** | ML engineer, has shipped a production RAG | Corrects the theory with what actually happened at scale | Argues from one company's experience as though it generalises |
| **Sofia** | Platform engineer, security-minded | Asks the permissions and tenancy questions early | Treats every problem as an access-control problem |
| **Dan** | Career-switcher, 18 months in | Asks the question everyone else was too embarrassed to | Accepts the first confident answer without checking it |
| **Aarav** | Consultant, client-facing | Reframes debates around what the client will pay for | Under-engineers; declares things good enough too early |
| **Lena** | Research background, reads the papers | Brings the citation that settles it | Cites a paper whose setup does not match the corpus at hand |
| **Tomás** | SRE | Asks what breaks at 3am and who gets paged | Wants to freeze changes rather than make them safe |
| **@maintainer** | Faculty | Marks accepted answers, closes threads, states the standard | — |

## The shapes a seeded thread takes

Threads are not question-then-answer. They are modelled on the arcs that actually occur, and
each shape teaches something a single answer cannot.

| Shape | Arc | What it teaches |
|---|---|---|
| **Confidently wrong, then corrected** | Someone answers fast and plausibly; someone else produces the counter-example; the first person confirms and revises | How to be wrong in public without it being a disaster — and that the correction, not the answer, is the valuable artefact |
| **Two right answers, different assumptions** | Two people disagree, both correct under different constraints; a third surfaces the hidden assumption | That "it depends" is only a real answer when you can name what it depends on |
| **Question is wrong** | The asker's premise is faulty; answering as asked would waste a week | Reframing as a skill, and that the fastest answer is sometimes "you are measuring the wrong thing" |
| **Long-running investigation** | 10–15 replies over days: hypothesis, measurement, refutation, new hypothesis, resolution | What debugging actually looks like when nobody knows the answer at the start |
| **Negative result** | Someone tried an extension, it did not work, they post the measurement anyway | That a clean negative with a mechanism is a contribution, and is graded as one |
| **Escalation** | A design review that surfaces a decision needing an ADR; the thread ends with a link to the ADR it produced | How a discussion becomes a decision record rather than dissolving |

## Rules the seeded content follows

1. **Every number is real.** Any metric quoted in a seeded post is one this repository actually
   produces. No invented benchmark figures, ever — a plausible fabricated number is worse than
   no number, because it teaches people to trust the shape of a claim over its provenance.
2. **Wrong answers are wrong in instructive ways.** Not strawmen. Each incorrect reply is a
   mistake a competent engineer genuinely makes, and the correction names the reasoning error,
   not just the right answer.
3. **The accepted answer is marked.** In answerable categories the resolution is marked as the
   answer, so the thread has a readable conclusion rather than trailing off.
4. **Disclosure is per-post, not per-thread.** A reader landing mid-thread from a search result
   sees the footer without having to scroll to the top.
5. **No real person, company or client appears.** The corpus is synthetic and generated from a
   fact graph; the organisations in it are fictional by construction.

## When real cohort activity starts

Seeded threads are not archived or hidden. They stay, and they set the standard — a new cohort
member reads three of them before posting and learns the house style for a question, a
measurement and a disagreement without anyone having to write a style guide about it.

The one thing to watch: a seeded answer must never be treated as more authoritative than a
real one because it came from the maintainers. If a cohort member's answer is better, the
accepted mark moves.
