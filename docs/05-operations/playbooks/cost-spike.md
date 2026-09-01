# The bill went up and nothing shipped

**Symptom:** inference cost rose materially with no corresponding deploy.

## Ask for the composition first

Do not start optimising. Get the breakdown, because the answer is nearly always in one line and
it is usually not the line people reach for.

Typical split for a RAG system: **generation 70–85%**, retrieval infrastructure 5–15%, embedding
and storage under 5%. If yours differs sharply from that, the difference *is* the incident.

Four token categories, tracked separately — input, output, cache-write, cache-read. A spike that
is invisible in one is usually obvious in another.

## The three causes, in order

**1 · Cache hit rate collapsed.** By far the most common, and completely silent — right answers,
working feature, larger bill.

Prompt caching requires a **byte-identical** prefix. Anything volatile that moved earlier in the
prompt destroys the cache for everything after it. A timestamp at byte 58 of a system prompt took
one system from 71% hits to 4%, and cost per query up 58%.

Check: log the first 200 characters of two consecutive requests and diff them byte for byte. Not
the template — what actually went over the wire.

**2 · Output length drifted.** A prompt change, a model change, or a rubric edit that made the
model more verbose. Output tokens are usually the largest single line and the least examined.
Plot mean output tokens per day.

**3 · Retry or loop behaviour.** An agent whose stop condition degraded, or a retry path that
fires more often than anyone thinks. Check step-count distribution rather than the mean — this
shows up as a fat tail, not a shifted centre.

## The check that finds most of these in one minute

```
cost per query  =  (bill / queries)
```

If cost per query is flat and the bill rose, you have a **volume** story, not a cost story, and
the investigation is entirely different. People skip this and spend a day optimising a system
that is behaving correctly under more load.

## What to write down

- Cost per query before and after, not the total.
- Which of the four token categories moved.
- The alert threshold that would have caught it sooner. Cache hit rate belongs on the dashboard
  next to latency; a 10-point week-over-week drop is worth a page.
