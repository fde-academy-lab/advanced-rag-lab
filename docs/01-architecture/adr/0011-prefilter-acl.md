# ADR-0011 · Pre-filter permissions, and evaluate them at query time

- **Status:** Accepted
- **Date:** 2026-08-30
- **Deciders:** Maintainers
- **Related:** Design review thread (regulated insurer), issue #16

## Context

Documents carry an `acl_group`. Different users see different subsets. Two decisions follow and
they are usually conflated: **where** the filter runs, and **when** the permission is evaluated.

## Decision 1 · Pre-filter, not post-filter

Constrain the candidate set before scoring.

Post-filtering — retrieve top k, drop what the user cannot see — fails two ways:

**k-collapse.** Ask for 10, get 10, filter to 2. Result count becomes a function of the user's
permissions, so the most restricted users get the emptiest search. Over-fetching to compensate is
unbounded: a user permitted 0.1% of the corpus needs k = 10,000 to reliably see 10 results.

**Score leak.** Scores, and any statistic derived from the corpus, let a restricted user infer
that documents exist and roughly what they contain. This is an exfiltration channel, and it is
the first thing a security reviewer asks about.

## Decision 2 · Evaluate at query time against the source of truth

Not baked into the index at ingest.

Permissions change far more often than documents do. An index that caches permissions serves a
revoked user their old access until the next reindex — which, on a nightly rebuild, is up to 24
hours of unauthorised access with an audit trail showing the system granted it.

The cost is a lookup per query. That is a real latency cost and it is the correct trade.

## The failure that is not obvious

Raised in the insurer design review and worth recording, because it is invisible until it bites.

**A filtered graph search can disconnect the graph for a restricted user.** The long-range links
that make a small-world graph navigable (ADR-0010) may all point at documents the user cannot
see. Greedy search then cannot cross the space and recall collapses — for exactly the users with
the tightest permissions, which is the worst possible distribution of failure.

Reported in the field at 0.31 recall for the most-restricted role against 0.94 unrestricted, with
nothing in the aggregate showing it.

**Mitigation:** a selectivity threshold, *measured rather than guessed*. Below some filter
selectivity, fall back to exact search over the permitted set. Costs latency on a minority of
queries and is correct.

**Consequence for evaluation:** aggregate recall cannot detect this. An eval slice **per ACL
group** is required, which is a change to the eval set rather than to the retriever. That is
issue #16, and it is the part that would have been missed.

## Partitions versus a single filtered index

Considered and rejected for this corpus.

With 14 ACL groups and 1.3 groups per document on average, partitioning duplicates ~4% of
documents fourteen times. Storage is affordable. Consistency is not: fourteen copies updated
non-atomically means a window where the answer depends on who asked — in a regulated setting,
two different answers to the same question with an audit trail proving it.

Single index, ACL as a column, filtered search.

## Consequences

**Good.** No k-collapse, no score leak, no stale-permission window, no multi-copy consistency
problem.

**Bad.** A permission lookup on every query. Filtered ANN needs the selectivity fallback, which
is one more measured threshold that will drift and need rechecking.

**Testable.** `tests/` asserts persona isolation and k-collapse behaviour. Neither test would
have caught the graph-disconnection failure, which is why it is written down here rather than
only in code.
