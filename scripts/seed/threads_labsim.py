"""L.A.B. Simulator threads: the index, and two solves worked in public.

The index thread is documentation, so it is short and it is a reference. The two worked threads
are not documentation — they are the argument that this loop is worth using, and the argument
only lands if the first submission in each one is *wrong in a way a competent person would be
wrong*. A demo thread where somebody posts the right answer and a bot says "correct" teaches
nothing and reads as advertising.

Every number quoted is one the repository actually produces.
"""
from __future__ import annotations

CAT = "LAB Simulator"
REPO = "https://github.com/fde-academy-lab/advanced-rag-lab"

THREADS = [
{
 "category": CAT, "author": "maintainer",
 "title": "Start here — the simulator, and how to use it without cloning anything",
 "body": f"""Seven units. Five modes. Every one graded against a live retrieval corpus rather
than against a fixture.

You can work them three ways, and they are the same grader.

### 1 · In this category, with no clone

Open a new discussion here using the form, paste your file, post. A GitHub Action runs
`python -m labsim check` on a clean checkout and replies with the **named checks** that failed —
not a red cross, the specific promise your code broke.

Then, as comments on your own thread:

| | |
|---|---|
| `/check` | re-grade (editing your post also re-grades automatically) |
| `/hint` · `/hint 3` | the next hint from the brief, one at a time |
| `/solution` | the worked answer — opens once the thread has cleared |
| `/status` | the pathway and where this unit sits in it |

### 2 · In Codespaces, with an editor

**Code ▸ Codespaces ▸ Create codespace on main.** Everything installs during the prebuild, and
you land in a terminal that already tells you what to do next.

```
python -m labsim next             what to do now
python -m labsim brief F1         read it, rendered, hints collapsed
python -m labsim start F1 --open  scaffold an attempt beside the brief
python -m labsim check F1         grade it
```

`F1` → *Run Task* in the command palette has the same commands if you prefer a menu.

### 3 · Locally

`pip install -e ".[dev]"`, then `cd lab-simulator` and the same commands. `python -m labsim
doctor` answers "is this machine able to run this" before you spend an hour deciding it is your
code.

---

## The pathway

Prerequisites are not bureaucracy here: a later unit reuses what an earlier one built. The
pathway is *derived* from them rather than declared, so it cannot drift from what the units
actually say.

```
wave 1   F1  R1                what a chunk is, what a citation is
wave 2   E1  R2  C1            how to measure, how to decide, how to diagnose
wave 3   R3                    implement the thing you decided, against a bar
wave 4   P1                    hand it over so somebody else can re-run it
```

| | Unit | Mode | Difficulty | Really about |
|---|---|---|---|---|
| **F1** | Chunk so the answer survives the cut | `implement` | easy | Overlap is a length budget, not a tuning knob |
| **R1** | Make a citation resolve | `implement` | easy | A citation a human cannot follow is decoration |
| **E1** | The two recalls that disagree by thirty points | `implement` | medium | A metric normalised against its own output cannot go down |
| **R2** | Decide whether to fuse at all | `decide` | medium | No code. The deck says fuse; the measurement says otherwise |
| **C1** | The five characters that cost two thirds of the bill | `diagnose` | hard | A correct feature, a passing test, a bill three times the estimate |
| **R3** | Build the rule you rejected | `measure` | hard | The real corpus, and the diagnostic nobody ran |
| **P1** | The measurement note that survives you leaving | `ship` | medium | The grader re-runs your measurement and checks your numbers match |

## What makes a unit different from a practice problem

Three gates instead of one.

**A decision, before any code.** If a unit ships a decision template, the grader reads it first
and rejects a falsifier that names the conclusion rather than an observation. *"I would change
this if it turned out to be wrong"* is true of every decision ever made, and it is the shape
most first attempts take.

**The checks**, which are named, so a failure tells you which promise you broke.

**A metric bar**, measured on the real corpus. Passing tests is not passing: a reranker that
returns its input unchanged passes every structural test ever written for a reranker.

## Two things about the grading

**The graders are themselves graded.** Every unit ships a worked answer the grader must accept
and decoys it must reject, with `expect.yaml` naming which check has to catch each one. A check
that has never rejected anything is a function that returns `True` and you cannot tell those
apart by reading it. CI runs both directions on every change to the lab.

**Your code runs in a job with no token and no secrets.** The workflow is split in three — route,
grade, respond — and only the last one can write anything. The
[workflow file]({REPO}/blob/main/.github/workflows/lab-simulator-discussions.yml) opens with the
reasoning, including what it does *not* protect against.

## House rules

Post your **approach before your code** — the form asks for it first on purpose. Writing the
reasoning afterwards turns it into rationalisation and nobody can tell afterwards, including
you.

Spend hints deliberately. They are collapsed rather than absent because a hint read before you
are stuck costs you the thing you were about to work out.

And if you get a red result, leave the thread up. A thread where somebody posted a wrong answer,
a named check caught it, a peer explained why and the author came back with the fix is the most
useful object in this whole repository. A green tick on a fork nobody can see is not.""",
 "replies": [
  {"by": "priya", "body": """One thing that is not obvious from the brief and cost me twenty
minutes: the grader reads `decision.yaml` **before** it runs a single test. On R2 I had a
half-written decision and a finished implementation and got rejected without any of my code
being executed.

That is the mode working as designed, and I would still put it in bold somewhere. It reads like
a bug the first time."""},
  {"by": "maintainer", "body": """It is in the brief and clearly not prominently enough — added
to the form's description too.

Worth saying why it is that order rather than parallel. If the decision is graded *after* the
code, a decision can always be written to match what was built, and the grader cannot tell.
Order is the only thing that makes the artefact mean anything.""",
   "accepted": True},
  {"by": "dan", "body": """Codespaces question — does the prebuild include the corpus, or does
the first `check` build it?"""},
  {"by": "maintainer", "body": """It builds in about 0.7 seconds, so there is nothing to cache
on disk; there is no dataset to download at all. What the prebuild does pay for you is the pip
install and the interpreter's import cost, which is the part that would otherwise make somebody's
first `labsim check R3` feel slow and give them the wrong impression of the whole thing.

`.devcontainer/setup.sh` builds it once anyway, so the bytecode is warm."""},
 ],
},
{
 "category": CAT, "author": "dan",
 "title": "R1 · my attempt — every shape check passes and the last one does not",
 "body": """**Approach.** Number the hits from 1, put a provenance line above each passage, join
with a blank line. Keep `markers` as the mapping so a citation can be traced back.

**Your solution.py**

```python
def pack_context(hits) -> PackedContext:
    blocks, markers = [], {}
    for i, hit in enumerate(hits, start=1):
        markers[i] = hit.doc_id
        provenance = f"[{i}] {hit.doc_id} · chunk {hit.ordinal} · score {hit.score:.2f}"
        blocks.append(f"{provenance}\\n{hit.text}")
    return PackedContext(text="\\n\\n".join(blocks), markers=markers)
```

**What surprised me.** Ten checks pass and two fail, and the output looks completely correct to
me. I have read it four times.""",
 "replies": [
  {"by": "labsim-bot", "body": """🔴 `R1` · Make a citation resolve — **not yet**

`implement` · easy · retrieval · graded in 0.1s on a clean checkout

**Checks that failed**

- `markers map to the input chunk_ids`
- `every marker resolves to a real chunk_id, over random inputs`

```
FAIL  every marker resolves to a real chunk_id, over random inputs — with 4 hits, marker(s)
      ['1','2','3','4'] in the text resolve to ['doc-loymnp','doc-nquchc','doc-sbzzrq',
      'doc-anbega'], which was not in the input
```"""},
  {"by": "wei", "body": """Your output *is* correct. That is the problem — the failure is not in
what the reader sees, it is in what the mapping points at.

`markers[i] = hit.doc_id`. A document, not the passage. Every citation in your bundle resolves
to a 34-page runbook."""},
  {"by": "dan", "body": """Oh. And it would have shipped, because the block renders identically
either way — the doc_id is in the provenance line in both versions, so a screenshot of the
output cannot tell them apart.

Fixed to `hit.chunk_id`, green.

Filing this one: **the check that caught it is the only one stated over randomised inputs.** The
ten shape checks are all about formatting, and my formatting was fine."""},
  {"by": "maintainer", "body": """That last sentence is the unit, and you got there without the
hints, so I will add the part that comes after it.

A test comparing your output to an expected string tests your formatting choices. It cannot
express the promise a citation makes, which is not *"the marker is rendered"* but *"the marker
resolves"*. Those look identical in a demo and diverge the first time somebody at 3am clicks
through to check a claim.

When you write a checker for your own system, the question to ask is: **which of these
assertions would still hold if the feature were quietly broken?** Ten of yours would.""",
   "accepted": True},
  {"by": "priya", "body": """Adding the version of this I shipped once, which is worse and
passes even more checks: `markers[i] = hit.chunk_id` but built *before* a dedup step that
renumbered the blocks. Correct mapping, correct ids, and the numbers in the text pointed one
row off after any duplicate was removed.

Nobody noticed for six weeks. The citations were plausible — adjacent chunk, same document,
roughly the right topic."""},
 ],
},
{
 "category": CAT, "author": "marcus",
 "title": "R2 · rejected before it ran a single test, and I think the gate is wrong",
 "body": """**Approach.** Read the evidence table, worked out the mechanism, wrote the decision,
posted it.

**Your decision.yaml**

```yaml
decision: >-
  Ship weighted score fusion with alpha near 0.2 on the dense leg, min-max normalised per query.

why: >-
  Equal weight treats both retrievers as equally credible voters and here they are not. The
  scale-invariance that lets RRF skip normalisation is the same property that discards the
  evidence that one leg is weaker, so the weak leg keeps a full vote.

rejected: >-
  RRF, which would have been right if the two legs were of comparable strength or if per-query
  score distributions were too unstable to normalise.

would_change_if: >-
  I would revisit this if the weighted approach turned out to be the wrong choice.
```

**What surprised me.** It did not run anything. Three fields are, I think, genuinely good, and
it rejected the whole submission on the fourth. That feels disproportionate.""",
 "replies": [
  {"by": "labsim-bot", "body": """🔴 `R2` · Decide whether to fuse at all — **not yet**

`decide` · medium · retrieval · graded in 0.0s on a clean checkout

- ❌ **decision** — filled, and the falsifier names an observation rather than the conclusion

```
decision.yaml: `would_change_if` names the conclusion rather than an observation.
"If it turns out to be wrong" is true of every decision ever made. What would you *see*?
```"""},
  {"by": "wei", "body": """It is disproportionate and I think that is deliberate. Three good
fields and a tautological falsifier is exactly the artefact that reads as rigorous in a design
review and cannot be acted on afterwards.

Your first three fields are reasoning. The fourth is the only one that does any work after the
meeting ends."""},
  {"by": "dan", "body": """I would push back on Wei slightly. The gate is a regex. Mine got
rejected for a falsifier I still think was fine — I wrote "if the measurement no longer holds",
which is vague, sure, but it is not the same failure as "if it turns out to be wrong".

A checker that cannot tell vague from tautological is going to reject correct work."""},
  {"by": "maintainer", "body": """Dan is right that it is a regex and right that regexes are
blunt. It is worth being precise about what it is blunt *about*, because the answer changes what
you do with the rejection.

"If the measurement no longer holds" is rejected for a different reason than Marcus's, and both
rejections are correct. Marcus's names the **conclusion**: it is true of every decision ever
made, so it carries no information. Yours names the **evidence you already have**: it says you
would change your mind if the thing you just measured stopped being true, which is a restatement
of the decision with a negation on it.

A falsifier is a standing instruction to your future self, and the test is whether somebody who
was not in the room can execute it. Neither of yours passes that.

Marcus, the version that clears is in your own `why` already — you wrote that the legs are not
equally credible. So: *what would you see if they became equally credible?*

> The per-query win rate between the legs moves toward even — each best on 40 to 60 percent of
> queries instead of the current lopsided split.

Somebody can plot that on a Tuesday without asking what you meant. That is the whole bar.""",
   "accepted": True},
  {"by": "marcus", "body": """That lands, and the annoying part is that the sentence was
already in my `why`. I had the observation and wrote a conditional about the conclusion instead,
which I have now watched myself do twice in this thread.

Green. And R3 immediately told me my decision was defensible and my *premise* was not — the
per-query failure overlap between the legs is 0.9684, so 92 of the 95 questions the dense leg
misses are also missed by BM25. There was almost nothing for any fusion rule to add, at any
weight.

Both of us were arguing about how to weight a vote that was never going to change the
outcome."""},
  {"by": "priya", "body": """That is the best advert for the ordering I have seen. R2 makes you
commit, R3 shows you the number, and the gap between them is the lesson — which you only get if
the commit came first."""},
 ],
},
]
