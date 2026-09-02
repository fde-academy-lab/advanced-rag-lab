# CD1 · One line makes every request a cache miss. Move it, do not delete it.

**Track** cost · **Kind** drill · **Mode** diagnose · **Difficulty** easy · **~10 min**
**Prerequisites** none

---

`starter.py` assembles a prompt from four blocks. Somebody added `Current time:` to the first
one so the model could answer "as of when?" questions. The feature works. Every request is now
billed at full price, because the cache in front of the model reuses the longest
**byte-identical prefix** — and the prefix now differs at about byte 130 on every call.

Fix `assemble()` so that two requests with different questions, different evidence and
different times share the longest prefix they can. Keep the timestamp: the feature it enables
is real.

## What the grader checks

| check | the mistake it catches |
|---|---|
| `stable blocks share a prefix across requests` | the fix that is not a fix |
| `the timestamp is still in the prompt` | deleting the feature to clear the check |
| `the evidence still comes before the question` | reordering blocks that were never the problem |

C1 is the full version of this, with a 200-request simulator and two bars that tell a fix from
a workaround. This is the one-idea version: **order by volatility, most stable first.**

<details><summary>Hint 1</summary>

Which of the four blocks change between requests, and which do not? Put the ones that do not
change first.
</details>

<details><summary>Hint 2</summary>

The timestamp can go anywhere after the last stable block. Next to the question is a natural
home — it is per-request information about the request.
</details>
