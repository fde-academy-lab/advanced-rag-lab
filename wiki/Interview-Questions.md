# Interview questions this repository answers

**Takeaways**

1. The strongest answers in an FDE loop are stories with a number in them. This repository
   has a dozen, and you have the command that regenerates each.
2. Interviewers score the delta between a mid-level and a senior answer. Each entry below gives
   both.
3. The full banks with model answers, follow-ups and mock loops are in
   [docs/06-interview-prep](https://github.com/fde-academy-lab/advanced-rag-lab/tree/main/docs/06-interview-prep);
   the timed drill is `python interview-bank/practice.py --drill models`.

Format: the question, what the panel is testing, a mid-level answer, the senior answer, and the
number from this repository that makes it yours.

### 1. Your hybrid search beat BM25 alone. Is it real?
*Tests:* whether you distinguish a delta from a difference.
*Mid:* "Yes, two points on recall." *Senior:* "Against BM25 alone, yes: +0.0624 with an interval
of +0.0407 to +0.0857. Against the dense leg alone, no: +0.0008, interval −0.0101 to +0.0109.
The legs fail on the same questions, overlap 0.9684, so fusion has nothing to add. We
published the first claim, then retracted it." *Number:* `run_eval.py --compare`.

### 2. The client wants context precision above 0.30. What is wrong with that gate?
*Tests:* whether you know what the metric divides by.
*Mid:* "Precision measures how much of the context is relevant." *Senior:* "Precision divides
by k. On the BM25 arm it is 0.3029 at k=5 and 0.1948 at k=10 while recall rises from 0.6329 to
0.7279. The gate is cleared by lowering k, which improves nothing. Gate on recall with a cost
budget instead." *Number:* `run_eval.py --ksweep`; drill `XD1`.

### 3. Evidence recall went up and full-chain recall stayed flat. Where do you look?
*Tests:* whether you think in stages.
*Mid:* "Tune retrieval more." *Senior:* "Retrieval found it and the chain lost it: the packer
or the reader. Two recalls are reported for exactly this; the independence check shows they
move separately (+0.0083 when the packer is bypassed)." *Number:* `scripts/independence.py`.

### 4. A finding you published turned out wrong. What did you do?
*Tests:* judgement under embarrassment.
*Mid:* "Fixed the doc." *Senior:* "Kept the finding public with a banner, wrote the retraction
as an ADR with the mechanism that let it stand (a gate that compares only against history),
added a repository-wide test so the retracted sentence cannot reappear, and turned it into a
drill where learners predict the number before they look." *Number:* ADR-0015, drill `RD2`.

### 5. Why is your ANN recall zero?
*Tests:* whether you have debugged a graph index.
*Mid:* "Increase ef." *Senior:* "At 230 chunks a greedy graph worked; at 2,430 it fell to 0.00
because the graph had no long-range links and search got stuck in a local neighbourhood. Adding
them took it to 0.94 at ef=64. Exact search would have hidden the lesson." *Number:* ADR-0010.

### 6. Identifiers like `INV_2024-Q3` were unfindable. Why?
*Tests:* whether you know analyzers are part of index identity.
*Mid:* "Use a different tokenizer." *Senior:* "FTS5's default tokenizer splits on `_` and `-`,
so the identifier never existed as a token. `tokenchars '_-'` took identifier-slice recall from
0.34 to 0.81, and the analyzer is now part of the index's identity so query and index can never
disagree." *Number:* ADR-0013.

### 7. How do you know your LLM judge is not drifting?
*Tests:* whether evaluation has its own evaluation.
*Mid:* "We use a strong model." *Senior:* "A frozen human-labelled slice, never tuned on,
re-scored by the judge on a schedule; drift is the change in agreement. Personas in the eval
set raise failure overlap to 0.9910, which is itself a drift signal to watch." *Number:*
`docs/04-evaluation/judge.md`, `failure_overlap.py --with-personas`.

### 8. Where does permission-aware retrieval leak?
*Tests:* security thinking in ranking systems.
*Mid:* "Filter the results by ACL." *Senior:* "Post-filtering leaks because the forbidden
chunks already shaped the candidate set and the scores; filter before retrieval, at the index,
and accept the recall cost. ADR-0011 has the measurement." *Number:* ADR-0011.

### 9. What should a status email with a number in it contain?
*Tests:* client communication.
*Mid:* "The metric and the improvement." *Senior:* "The configuration (k, fusion rule, encoder,
question count), the before and after, the interval, and the command. The measurement-note
format in this repository is the email." *Number:* unit `P1`.

### 10. When does a reranker not help?
*Tests:* whether you can read a failure signature.
*Mid:* "When the model is weak." *Senior:* "When it is uniformly slightly worse at every k.
That shape means the wiring is right and the features are wrong; a wiring bug is catastrophic,
not uniform. We lost four days verifying code that was fine." *Number:* week 3 standup, ADR-0005.

### 11. What did prompt block ordering cost, and what did it buy?
*Tests:* cost as architecture.
*Mid:* "Caching saves money." *Senior:* "Ordering the stable blocks first makes the prefix
cacheable; the cache hit rate is on the dashboard and the ordering is an ADR because it is a
design decision with a number, not a trick." *Number:* ADR-0012.

### 12. When would you tell the client not to build RAG at all?
*Tests:* whether you can say no with evidence.
*Mid:* "If the data is bad." *Senior:* "When the questions are answerable from a schema or a
form, when the corpus is small enough to put in the window, or when the failure the client
pays to remove is not a retrieval failure. The design review category exists so this decision is
made before week three." *Number:* the seeded use-case reviews in Design Reviews.
