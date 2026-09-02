# FD1 · Three chunkers, one of them loses the end of every document — which?

**Track** foundations · **Kind** drill · **Mode** answer · **Difficulty** easy · **~8 min**
**Prerequisites** none

---

Three implementations of `chunk()`. All three return windows no longer than `size`, all three
overlap consecutive windows, all three pass the tests their authors wrote. Read them. Do not run
them.

**A**
```python
def chunk(text, size=64, overlap=16):
    words = text.split()
    stride = size - overlap
    return [" ".join(words[i:i + size])
            for i in range(0, max(len(words) - size, 1), stride)]
```

**B**
```python
def chunk(text, size=64, overlap=16):
    words = text.split()
    stride = size - overlap
    out, start = [], 0
    while True:
        out.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            return out
        start += stride
```

**C**
```python
def chunk(text, size=64, overlap=16):
    words = text.split()
    stride = size - overlap
    n_windows = len(words) // stride
    return [" ".join(words[i * stride:i * stride + size]) for i in range(n_windows)]
```

Fill `answer.yaml` with the letters of the ones that drop words off the end of *some* document
whose length is not a multiple of the stride. Then post it, and the grader **runs all three** on
two such documents and tells you which ones actually did.

One of them only fails at some lengths. That is not a trick; it is the shape of the bug that
passes the single test its author wrote.

## Why this is a drill and not a quiz

The three loops differ in one place each: the condition that decides whether to emit one more
window. That condition is always written against the example the author had in mind, and the
example is always a document whose length divides evenly. The tail bound is the single most
shipped chunking bug in this repository's history — F1's own decoy is one of these three.

<details><summary>Hint 1 — what to look for</summary>

Ask of each loop: after the last window it emits, is there a word it did not reach? Walk a
100-word document by hand, stride 48. Then walk a 140-word one — one of the three changes its
answer.
</details>

<details><summary>Hint 2 — the shape of the bug</summary>

A bound of the form `range(0, len - size, stride)` asks "is there a whole window left", which
is a different question from "has the last window reached the end". They agree only when the
length is a multiple of the stride.
</details>
