# CD1 · solution

Move `Current time:` out of the first block and put it with the question:

```python
parts = [SYSTEM, INSTRUCTIONS, "Evidence:\n" + ..., f"Current time: {now}\nQuestion: {question}"]
```

The two requests now share the whole of `SYSTEM` and `INSTRUCTIONS` as a byte-identical prefix,
and the timestamp is still in the prompt.

**The decoy that deletes it** clears the prefix check and removes the feature. **The decoy that
reorders everything** moves the question ahead of the evidence, which is a different prompt —
the model reads in order — and buys nothing, because the evidence was already after the volatile
byte.

ADR-0012 has the production version: hit rate 4% → 71% from this one move.
