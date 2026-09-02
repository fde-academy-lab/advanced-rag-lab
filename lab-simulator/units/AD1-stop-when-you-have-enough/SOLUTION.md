# AD1 · solution

```python
gathered = set()
for i, found in enumerate(steps):
    gathered |= set(found)
    if required <= gathered:
        return i
return None
```

Three things, and each is one of the checks.

**The running set.** Sufficiency is about everything gathered, so the loop keeps a union.
Testing each step on its own forgets what earlier steps paid for — the `fail-never-stops` decoy,
which on `[{a}, {}, {b}]` needing `{a, b}` never fires.

**Subset, not intersection.** `required <= gathered` is "everything needed is known".
`found & required` is "something useful arrived", which is the agentic version of evidence
recall mistaken for full-chain recall — the `fail-stops-on-any-evidence` decoy.

**`None` is an answer.** The loop that runs out of budget must say so. Returning the last index
lets the caller answer on a chain it knows is incomplete, which is the confident wrong answer
this whole repository is about.
