# Start here

## The fifteen-minute version

```bash
git clone https://github.com/fde-academy-lab/advanced-rag-lab.git
cd advanced-rag-lab
make setup
make lab
```

Open `notebooks/00_start_here.ipynb`, press **Run All**. It finishes in about four seconds.

There is no dataset to download, no API key to set and no service to start. The entire
retrieval stack lives inside `sqlite3.connect(":memory:")` and disappears when you stop the
kernel.

## What this is

A retrieval, RAG and evaluation system small enough to read in full and complete enough to be
wrong in interesting ways. Ten notebooks build it; a ~6,800-line toolkit implements it; an
evaluation harness judges it and gates changes to it in CI.

The point is not the retrieval. Thousands of repositories implement retrieval. The point is
that **every claim here has a number attached, and three of those numbers came out against the
received wisdom** — which is the part that turns out to be worth teaching.

## What to read, by why you are here

| You are | Path |
|---|---|
| Learning retrieval properly | Notebooks `00` → `09` in order. Do not skip `01`; everything later assumes the recall budget |
| Preparing for interviews | [06-interview-prep](../06-interview-prep/) — start with `mock-loops.md` and run one |
| Assessing whether to use this for a cohort | [02-curriculum/syllabus.md](../02-curriculum/syllabus.md), then [03-exercises](../03-exercises/) |
| Extending it | [01-architecture/overview.md](../01-architecture/overview.md), then [09-research/extension-points.md](../09-research/extension-points.md) |
| Reviewing the engineering | [01-architecture/adr](../01-architecture/adr/) — eight decisions with their consequences |
| Here from a CV or LinkedIn post | Keep reading this page, then the three findings below |

## The three findings that make this worth your time

Each is measured, reproducible from a notebook cell, and contradicts what most material on the
subject says. Each also names the condition under which the expected result returns — a
negative finding without that is just an anecdote.

**1 · Equal-weight RRF loses to BM25 alone on this corpus.**
Weighted fusion at α = 0.2 wins instead. Fusing a strong retrieval leg with a weak one at equal
weight moves the result toward the weak one; RRF's scale-invariance is a virtue when the legs
are comparable and a liability when they are not, because it discards the score distribution
that would have told you to down-weight the weak leg. Returns to the expected result when both
legs are comparably strong. *Notebook `04`.*

**2 · Comparison starvation does not reproduce here.**
The corpus is generated from a fact graph that emits organisations on a balanced schedule, so
entity prevalence ratio ≈ 1 and the precondition for starvation is absent by construction.
Which is itself the finding: **a balanced generator cannot measure imbalance failures**, most
eval sets are built by balanced generators because those are easier to write, and so a whole
class of real failures is invisible to them. *Notebook `02`.*

**3 · No retrieval-score threshold separates answerable from unanswerable questions.**
Best F1 **0.38** across four signals tried. The null questions name real entities in the
corpus's own vocabulary while genuine questions paraphrase — so the *unanswerable* questions are
lexically **closer** to the corpus. Any threshold on retrieval score reads a feature with the
wrong sign, and no amount of tuning repairs that. *Notebook `05`.*

## The numbers, so you know what "working" looks like

| Metric | Value | What it means |
|---|---|---|
| Evidence Recall@8 | 0.7645 | Of all gold evidence pieces, the fraction that reached the context window |
| Full-chain recall | 0.4686 | Of all questions, the fraction where *every* required piece arrived |
| Answer correct | 0.4115 | Judged against gold, including abstentions |
| Cost per eval run | $0.0039 | The whole 243-question set |

The gap between 0.7645 and 0.4686 is not a defect. It is the multi-hop problem stated
numerically, and it is the single most useful number on the page.

## The house rules

1. **Any change that could move a number ships with the number** — before, after, delta, and a
   95% interval from `metrics.paired_bootstrap`.
2. **A delta inside the noise band is reported as inside the noise band**, not rounded into a win.
3. **The frozen slice is touched once.** Tuning against it, even once, invalidates it for
   everyone.
4. **A clean negative result with a mechanism is full credit.** Three of them are the best
   content here.

## If something does not work

Notebooks are executed in CI on Python 3.10, 3.11 and 3.12 on every push, so a failure is more
likely local than in the repository. Check [05-operations/runbook.md](../05-operations/runbook.md)
first, then ask in **Debugging Clinic** — symptom first, then what you have already ruled out.
