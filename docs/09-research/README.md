# 09 · Research

| File | What it covers |
|---|---|
| [reading-list.md](reading-list.md) | The papers behind each section, with what to look for in each |
| [paper-notes/](paper-notes/) | Structured notes: claim, method, what replicated here, what did not |
| [extension-points.md](extension-points.md) | 20 techniques you could add, each as a falsifiable hypothesis |
| [measurements/](measurements/) | Comparisons between configurations, with the command that reproduces each |

An extension point is not a to-do list item. It names the metric, the slice, the direction and
the size of the effect it expects — so that adding it either succeeds or fails, rather than
being declared a success because it is now present.

## Why `measurements/` exists

The eval gate compares one configuration against **its own history** and blocks a merge on a
regression. It has no concept of comparing configurations against each other — so a claim of the
form *"X beats Y"* sits entirely outside what CI is capable of checking, and the more the gate is
trusted the less anyone re-runs the comparison by hand.

That gap let a wrong finding stand in this repository for months, quoted in about twenty places
([ADR-0015](../01-architecture/adr/0015-correct-the-fusion-finding.md)). A measurement note here
is the fix: every claim about which configuration wins carries the command that regenerates it,
and a claim you cannot re-run in one command is a claim nobody will re-run.
