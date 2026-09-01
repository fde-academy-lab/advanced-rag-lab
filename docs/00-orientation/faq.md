# FAQ

### Why is there no vector database?

Because you would learn less. A vector database turns retrieval into configuration, and the
failures this repository is built to teach — a k-NN graph that stops being navigable as the
corpus grows, a tokenizer that shreds identifiers, a reranker that discards the signal it was
added to exploit — are all *inside* the box you would otherwise be configuring.

Everything has a documented upgrade path to a real stack. Swapping in Bedrock Knowledge Bases or
a hosted vector store changes the retriever and leaves the harness, the metrics and the eval set
untouched. That property is the lesson.

### Is the corpus real?

No, and deliberately so. It is generated from a fact graph — 24 fictional organisations across
6 quarters, 484 documents, 2,430 chunks. Two consequences that matter:

- **Gold evidence is true by construction**, so there is no annotation-error floor under any
  number. When a metric moves, it moved because the system changed.
- **No client data, ever.** Nothing here is under anyone's NDA.

The cost is that some real-world effects cannot be measured on it, and where that happens the
repository says so rather than pretending otherwise — see finding 2 in
[start-here.md](start-here.md).

### Why does the reranker use fitted weights? Can I trust the numbers?

The weights in `DEFAULT_CROSS_WEIGHTS` were fitted by logistic regression on a dev slice of this
corpus with this encoder. They are **not transferable** and should not be quoted anywhere else.
Hand-tuning was tried first and never beat the baseline; that failure is issue #4 and is worth
reading.

### Why is `answer_correct` only 0.41?

Because the generator is extractive by default and the questions include multi-hop chains and
deliberately unanswerable questions. A number near 0.9 would mean the eval set was too easy to
measure anything.

If a configuration change makes every metric jump, suspect the eval set before celebrating.

### Do I need an AWS account?

No. `bedrock.preflight()` is read-only and makes **no AWS calls** — it inspects local
configuration and reports what would be needed. Nobody can bill an account by pressing Run All,
which is deliberate.

### Why SQLite for vectors?

Because at this corpus size it is fast enough and it makes the index legible. You can `SELECT`
the state of the world mid-experiment, which is worth more while learning than the speed you are
giving up. `store.py` documents where this stops being true.

### The notebooks take how long?

Between 3 seconds (`00`) and 135 seconds (`09`); about ten minutes for all ten. CI enforces a
10-minute hard limit per notebook.

### Can I use this in an interview or on my CV?

Yes — that is one of its purposes. [07-career/portfolio.md](../07-career/portfolio.md) has the
CV lines, the LinkedIn post and the 90-second walkthrough. Lead with the three findings rather
than the architecture: "I built a RAG system" is a crowded claim, and "I measured three widely
repeated claims and three of them failed, here is the mechanism" is not.

### Why are the seeded discussions written by fictional people?

So that a fifteen-reply thread is readable. Every seeded post carries a footer saying it is a
worked example. See [10-community/personas.md](../10-community/personas.md).

### Something contradicts something else. Which is right?

The notebook, because it computed the number. Then open an issue — a documentation drift is a
real defect and issue #13 exists for exactly this class.
