# C1 · How we did it

The fix is an ordering, not a deletion:

```python
parts = [
    SYSTEM,                                       # 1  never changes
    f"Tenant: {tenant_id}",                       #    stable *within its own cache partition*
    INSTRUCTIONS,                                 # 2  changes on deploy
    EXAMPLES,                                     # 3  changes on deploy
    "Evidence:\n" + "\n\n".join(chunks),          # 4  the barrier
    f"Current time: {now.isoformat(...)}",        # 5  volatile, and now free
    f"Requester role: {user_role}",               # 5
    f"Question: {question}",                      # 6
]
```

Nothing is removed. Every feature still works. The measurement:

| | cache_hit_rate | prefix_tokens_billed |
|---|---|---|
| as given | 0.2612 | 154.04 |
| **correct ordering** | **0.8176** | **38.07** |
| delete the timestamp | 0.7942 | 42.16 |
| move the stable blocks too | 0.6969 | 63.23 |

## The rule

> A volatile field does not make its own block uncacheable. It makes **everything after it**
> uncacheable.

That single sentence is the unit. It converts a formatting preference into an architectural
constraint, and it is why the block order is a *cost* decision that belongs in a decision record
rather than a style guide.

The corollary people miss: this makes prompt assembly **order-dependent in a way that is not
visible in the output**. Two assemblers producing semantically identical prompts can differ by a
factor of four in cost, and nothing in a diff of the rendered prompts explains it. You have to be
looking at position.

## Why there are two bars

Because one bar cannot distinguish a fix from a workaround, and this failure has an extremely
attractive workaround.

**Delete the timestamp.** `cache_hit_rate` goes to 0.7942, comfortably over the bar. Cost drops.
Ticket closed. And the assistant can no longer answer *"as of when?"*, which is the question the
field was added for — a regression that no cost dashboard will ever surface, and which somebody
will fix in four months by putting the timestamp back exactly where it was.

`prefix_tokens_billed` is what makes that visible: 42.16 against the correct 38.07. Close, and
consistently worse, because deleting a field removes its tokens without moving the barrier — you
paid a feature for four tokens.

**Move everything that looked volatile.** `tenant_id` varies across the request trace, so a diff
flags it. Push it past the barrier along with the examples, "to be safe". The hit rate is 0.6969
— still respectable-looking — and the bill is *worse than either*: 63.23, because every cacheable
token you push past the barrier is billed at full rate on every request forever.

That is the general trap with caches: **the safe-looking direction is expensive.** Shortening a
prefix always feels conservative and always costs money.

## The `tenant_id` question, which is the interesting one

It changes between requests in the trace. It is also in `CACHE_KEY_INCLUDES`, so the cache is
partitioned per tenant — and *within any one partition*, the field is constant.

Volatility is not a property of a field. It is a property of a field **relative to the cache
key**. A field that varies globally and is constant within a partition belongs *before* the
barrier, and moving it costs you every token in its block.

This is the part that separates someone who has read about prompt caching from someone who has
operated one, and it is why hint 4 exists rather than the answer being in the brief.

## How to find it, without reading the code

The brief's first hint is the actual technique and it takes thirty seconds:

```python
a = assemble(q1, chunks1, now=t1, tenant_id="acme-eu", user_role="analyst")
b = assemble(q2, chunks2, now=t2, tenant_id="acme-eu", user_role="analyst")
next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)     # -> where the cache ends
```

The first differing byte position *is* the end of your cacheable prefix. Everything after it is
billed at full rate. Then move that field, and diff again — there is more than one.

Reading the assembler top to bottom is the slower path and it is what most people do, because
the code is short enough to look readable. The diff is faster and it does not depend on your
judgement about which fields *look* volatile — which is exactly the judgement that gets
`tenant_id` moved.

## Why this is a `diagnose` unit

There is no failing test, no stack trace, and no incorrect output. The feature that causes the
problem was added deliberately, for a good reason, works correctly, and had its own passing test.
The only symptom is a number on a different team's dashboard, six weeks later.

That is what most real work looks like, and almost no practice material simulates it, because
generating a broken program is easy and generating a *correct program that is expensive* requires
having been there.

The grading follows: `DIAGNOSIS` is checked for naming a field and a mechanism rather than
restating the symptom. `reference/fail-diagnosis-names-no-block/` has the correct ordering and
clears both bars, and its write-up says the cache was not hitting and now it is — which is where
the investigation started. Nobody reading it learns the rule, so nobody applies it to the next
prompt, and the next prompt is being written this sprint.

## What we got wrong first

**We measured the cache hit *rate* as the share of requests that hit anything.** Under that
definition, the broken assembler scores 0.99 — every request shares the system prompt with some
earlier one, so every request "hits". The dashboard read 99% while the bill did not move.

The metric that means something is the share of each prompt's *tokens* served from cache, which
is why the simulator computes that instead. It is the same class of error as reporting evidence
recall without full-chain recall in E1: a metric that counts events when the decision depends on
magnitude.

**We shipped the fix without writing the rule down.** It came back four months later, in a new
prompt, in the same position. [ADR-0012](../../../docs/01-architecture/adr/0012-prompt-block-ordering.md)
is what stopped it happening a third time, and the volatility table in it is the artefact — not
the commit that reordered the list.

## Where this lives in the real system

`raglab/context.py` orders blocks by volatility and `raglab/costs.py` prices the result across
the four token categories. The ADR carries the production numbers: a 4% hit rate traced to a
timestamp at byte 58 of the system prompt, moved to block 5, hit rate 4% → 71%, cost per query
down 58%.

Five characters differed between consecutive requests. Every token after them was uncacheable,
which was the entire prompt.
