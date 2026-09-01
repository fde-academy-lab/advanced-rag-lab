# ADR-0009 · What happens to the frozen slice when the corpus grows

- **Status:** Accepted
- **Date:** 2026-08-27
- **Deciders:** Maintainers
- **Supersedes:** —
- **Related:** ADR-0002 (synthetic corpus), ADR-0008 (eval gate)

## Context

15% of the eval set is frozen: never used for tuning, thresholds or model selection, touched
once at the end of a piece of work. It is the only defence against the fact that testing twenty
variants at 95% confidence will produce one that clears by chance.

P4 requires growing the corpus — 484 documents is too few to exercise the ANN path realistically
and too few to support per-slice questions at usable n. Growing it raises a question nobody had
answered: what happens to the frozen slice?

Three options were on the table, and a standup thread surfaced the argument that decided it.

## Options

### A · Preserve the existing frozen slice unchanged

Keep the same 36 questions. New corpus documents are added; the frozen questions still resolve
against their original evidence.

- **For:** the slice retains its meaning. Numbers before and after the growth are comparable.
- **Against:** coverage decays. The slice was stratified against the old corpus's distribution,
  and as the corpus grows it becomes progressively less representative of it. Eventually it is
  measuring a corpus that no longer exists.

### B · Regenerate the frozen slice from the grown corpus

Re-stratify, re-sample 15%, freeze that.

- **For:** representative again. Obvious, and the option most people reach for first.
- **Against:** **this leaks.** The regeneration is performed by people who have already seen
  results from the old frozen slice. Every choice made in re-stratifying — which strata, what
  proportions, which difficulty band — is informed by knowledge the slice exists to be protected
  from. It looks principled and is a laundered peek.

### C · Start a new frozen slice, report both during transition

Keep the old slice, generate a new one, report against both for one phase, then retire the old.

- **For:** the leak argument in B applies to the new slice too, but the *old* slice is still
  clean, and reporting both means any divergence between them is visible rather than absorbed.
- **Against:** two numbers to explain, and for one phase every result carries an asterisk.

## Decision

**Option C.**

The deciding argument, from the week-3 standup: regenerating a frozen slice is a subtle way of
leaking exactly the thing the slice protects. The people re-stratifying have seen results from
the old one, and there is no procedure that unsees them.

Option A was tempting and is what we would have done without that argument. Its failure is
slower and quieter — a slice that measures a corpus that no longer exists still produces
confident numbers.

Transition rule: for the phase in which both exist, **any claim must clear both slices.** A
result that holds on the new slice and not the old is treated as unproven, not as evidence the
old slice is stale.

## Consequences

**Good.** No peek. Divergence between old and new slices becomes a visible signal about the
corpus change rather than a hidden one.

**Bad.** Two numbers for a phase, and reviewers must be told why. A result that clears one slice
and not the other blocks, which will be frustrating at least once.

**Ugly.** This has to happen again the next time the corpus grows, and the transition cost is
paid each time. We considered whether that argues for growing the corpus rarely and in large
steps rather than continuously. It does, and that is now the practice.

## What would change this decision

Evidence that the divergence between old and new slices is consistently inside the noise band.
If two independently-drawn frozen slices never disagree, the leak in option B costs nothing
measurable, and B's simplicity wins. We do not have that evidence and will not have it until
this has happened three or four times.
