# Session plans

One per delivery session. Each carries timings, the live demo, the discussion prompt, and the
**exit check** — the specific thing a participant should be able to do before the session ends.

| Session | Covers | Notebooks | Length |
|---|---|---|---|
| [session-01-baseline.md](session-01-baseline.md) | The recall budget, and declaring a baseline before you see numbers | `00`, `01` | 3 h |
| [session-02-retrieval.md](session-02-retrieval.md) | BM25 internals, ANN failure, fusion, reranking | `03`, `04` | 3.5 h |

## The shape every session follows

**Open with a failure, not a definition.** Session 2 opens by showing ANN recall at 0.00 and
asking what could cause that. Nobody remembers a definition of navigability; everybody remembers
the graph that could not be crossed.

**Run before explaining.** The notebook cell executes, the number appears, *then* the mechanism.
Reversing this produces a room that believes you and has learned nothing.

**One discussion prompt per session, posted in advance.** Threads run better when people arrive
having thought about it.

**Exit check is a number they produced**, not a concept they can restate.

## For the facilitator

The two things that reliably go wrong:

- **Running long on setup.** `make setup` on hotel wifi is the single largest schedule risk.
  Have participants run it before the session and check in the thread that it worked.
- **Answering the question a peer is about to answer better.** Wait. A room where the facilitator
  answers everything produces a cohort that asks the facilitator everything.
