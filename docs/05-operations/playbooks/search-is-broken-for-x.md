# "Search is broken for X" while the aggregate is fine

**Symptom:** users complain about a specific query class. Your dashboard is green.

This is the most common shape of a real retrieval incident, and the aggregate is why it took so
long to notice.

## Believe the users

The first instinct is to defend the number. Resist it: a green aggregate and unhappy users is
almost never a perception problem. It is an averaging problem, a metric-product mismatch, or an
eval set that no longer describes production.

## Twenty queries, by hand

Before instrumenting anything, take twenty of the complained-about queries and run them yourself.
Twenty is usually enough to see the pattern and it costs an afternoon rather than a sprint.

Look at what came back, not at the score. You are trying to name the class.

## The classes, and what each implies

| What you see | Class | Where to look |
|---|---|---|
| Identifier queries return unrelated documents | Analyzer shredded the token | FTS5 `tokenize` argument, and whether it is in the index version |
| Right document, wrong version | Temporal | Effective-date metadata and whether anything filters on it |
| Some users get few results, others fine | Permissions | Post-filter k-collapse, or a filtered graph disconnecting for restricted users |
| Answer needs two documents, gets one | Multi-hop | Per-piece vs per-question recall; single-shot retrieval has a ceiling here |
| Near-duplicates fill the window | Deduplication | Content hashing on gold and on results |
| Query is ambiguous or badly posed | The question, not the system | Reformulation rate — a reformulation is a labelled failure the user gave you free |

## Then measure the class

Once you can name it, build the slice and measure it. A complaint becomes tractable the moment it
becomes a number with a denominator.

If the slice does not exist in your eval set, that is the finding: **your eval set cannot see the
failure your users are having.** Add the slice before fixing anything, or you will not be able to
tell whether the fix worked.

## What to write down

- The class, and the query that made it obvious.
- Whether the slice existed in the eval set beforehand. If not, that is the real defect.
- The alert that would have caught it. Aggregate alerting will not; this is the argument for
  per-slice thresholds.
