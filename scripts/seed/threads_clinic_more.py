"""Four more Debugging Clinic threads: failures nobody in the thread can explain at the top.

The clinic's house style is that threads run long and the first three hypotheses are wrong, and
the wrong ones are written to be *specific*. A bad hypothesis that names a real mechanism ("FTS5
reads a bare hyphen as an operator") teaches the reader a real mechanism and then teaches them
how it was ruled out. A bad hypothesis that says "have you tried rebuilding it" teaches nothing
and makes the eventual answer look lucky rather than earned.

Each of the four is drawn from something this repository documents and can be reproduced against
it: the analyser pair in ADR-0013, a partial re-embed that leaves a homogeneous label over a
heterogeneous index, an eval number that moved because the corpus moved, and the two permission
leaks in ADR-0011 that survive a pre-filter.

Every figure quoted is one of the repository's own, out of an ADR, a playbook, the release-gate
doc or the committed baseline. Where an observation has no committed number behind it, it is
written in words rather than given a decimal it has not earned.
"""
from __future__ import annotations

CAT = "Debugging Clinic"
ADR = "/fde-academy-lab/advanced-rag-lab/blob/main/docs/01-architecture/adr"

THREADS = [
{
 "category": CAT, "author": "tomas",
 "title": "Hyphenated identifiers return zero rows since we picked up the tokenizer change. Underscored ones are fine.",
 "body": """Running this stack over our own incident corpus. Since we took the
`tokenchars '_-'` change from ADR-0013, one class of query returns **nothing at all**, and it is
the class support paste into the box all day.

```python
idx.lexical("ERR_CONN_RESET")   # fine, right document first
idx.lexical("doc-loymnp")       # 0 rows
idx.lexical("nw-8842")          # 0 rows
```

Underscore form works. Hyphen form returns an empty list. Same index, same session, same
persona.

What I have already ruled out:

- **The document is there.** `SELECT chunk_id, tombstoned FROM chunks WHERE chunk_id LIKE
  'doc-loymnp%'` returns the row, `tombstoned=0`, `index_version='v1'`.
- **Not the vector path.** `exact_vector` on the same query text finds the document, so the
  content is indexed and the failure is on the lexical leg only.
- **Not permissions.** I am running as `counsel`, which holds every group in this corpus, and
  the persona isolation assertion is green.
- **Not the reranker or fusion.** This is `InMemoryIndex.lexical()` on its own, before anything merges
  or reorders.

A string that is literally present in the text returning zero rows is a wiring failure rather
than a scoring one. And the underscore case working is the part I cannot fit into any story: if
identifiers were simply hard here, both shapes would be bad. It is the hyphen specifically.

Before ADR-0013 shipped, hyphenated ids matched. That change was supposed to make identifiers
*better*. Where do I look?""",
 "replies": [
  {"by": "dan", "body": """Obvious one first, since nobody has said it. Is the change actually
live on the box you are querying?

The tokenizer string lives in `store.py`, but the FTS table is created once and the create
statement is guarded by `IF NOT EXISTS`. If your process opened a database that was built before
you deployed, the table keeps whatever tokenizer it was created with, your new string does
nothing, and nothing anywhere errors.

```sql
SELECT sql FROM sqlite_master WHERE name = 'chunks_fts';
```

That prints the tokenizer the table is actually using, which is not necessarily the one sitting
in your source tree. I have been caught by that exact gap on a long-lived dev database, where
the source said one thing and the file said another for about a fortnight."""},
  {"by": "tomas", "body": """Good check and I should have led with it. Ran it:

```
tokenize = "unicode61 remove_diacritics 2 tokenchars '_-'"
```

So the table is on the new analyser, and the behaviour agrees with that, which is the
frustrating part. `ERR_CONN_RESET` only survives as a single token *because* `_` is in
tokenchars, and it does survive. Under the old default it would have been shredded into three
common words, which is the whole thing ADR-0013 was written to stop.

So the change is live, it is doing what it says on the underscore case, and it is the thing that
broke us on the hyphen case. Both halves of that sentence are supported by the same one-line
query."""},
  {"by": "wei", "body": """Then it is your query expression, and I have watched this exact bug
twice at my last place.

FTS5 has a query syntax. A bare hyphen is not a letter to it, and depending on position it reads
as a column filter or as a negation, so `doc-loymnp` unquoted means something closer to "doc, but
not loymnp". Zero rows is precisely what that produces when the corpus has no bare `doc` token
either.

The fix is to quote the whole thing before it reaches MATCH:

```python
idx.lexical("x", fts_expr='"doc-loymnp"')
```

We shipped a wrapper that quoted every token and the identifier complaints stopped that week. I
would bet on this one before I looked anywhere near the tokenizer."""},
  {"by": "tomas", "body": """That returns the row. Straight away, correct document, one hit.

Which would close the thread, except that `fts_query` **already quotes every token**. It is in
the docstring and the reason given there is identifiers. So the production path quotes and
returns nothing, and my hand-written quoted expression returns the row.

Two quoted queries for the same identifier against the same table, one works and one does not. I
am further from an explanation than I was this morning, and I now have a fix I do not
understand, which is worse than having neither."""},
  {"by": "lena", "body": """This is the known weakness of word-level inverted indexes on
identifier-shaped tokens, and there is a literature on it. The code-search work moved to
character trigram indexes for exactly this reason: you stop trying to guess where an identifier's
boundaries are and index overlapping trigrams instead, so `doc-loymnp` matches regardless of how
either side segments it. Precision drops a little and the index gets bigger.

I would build a trigram sidecar over the identifier fields and route identifier-shaped queries to
it. It is a known-good answer to a known-hard problem and it stops this class of bug recurring
every time somebody edits a tokenizer setting."""},
  {"by": "sofia", "body": """Hold off on the sidecar. Print the two expressions and compare them,
because Tomás has already given us the answer and nobody has read it as one.

```python
>>> InMemoryIndex.fts_query("doc-loymnp")
'"doc" OR "loymnp"'
```

His hand-written version was `'"doc-loymnp"'`. One token. The production path sends two.

Now look at what the index holds:

```sql
CREATE VIRTUAL TABLE v USING fts5vocab(chunks_fts, 'row');
SELECT term FROM v WHERE term LIKE 'doc%';
```

You will get `doc-loymnp` and no bare `doc`, because the table tokenizer keeps the hyphen. So the
query asks for two terms the index does not contain and gets zero rows, correctly.

The cause is that `fts_query` does its own tokenising in Python before SQLite sees anything:

```python
toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\\d+", text)
```

That pattern keeps `_` and splits on `-`. ADR-0013 added `-` to the index side and left the query
side alone. Underscores work because both halves agree about underscores; hyphens fail because
only one half was changed.""", "accepted": True},
  {"by": "tomas", "body": """Added `-` to the query-side pattern, rebuilt nothing, and the hyphen
cases came back immediately. No index change was needed at all, which tells you where the bug
was.

What surprised me is that **the aggregate never moved**. ADR-0013's own table puts the original
tokenizer incident at 0.81 against 0.34 on the identifier slice, a drop of 0.47, while the
overall average went 0.7645 to 0.7104 — 0.054, which is the kind of number that passes review.
This is the same shape with the sign reversed and our dashboard would not have paged anyone for
it either. It was found by a support engineer pasting a document id into a box.

The regression test I have added is a round trip rather than a unit test on either half: index
one document carrying an underscore identifier and a hyphen identifier, then assert `lexical()`
finds it by each. That fails if either side of the analyser changes without the other, which is
the only property I actually care about."""},
  {"by": "maintainer", "body": f"""Marked Sofia's. The general statement is worth having in
words, because [ADR-0013]({ADR}/0013-analyzer-in-index-identity.md) states half of it and this
thread is the other half.

**An analyser is a pair of functions rather than one setting.** There is the one that turns a
document into terms and the one that turns a query into terms, and a lexical index only works
while they agree. ADR-0013 put the index-side half into the index identity so that changing it
forces a rebuild. It put the query-side half nowhere, so the two could drift, and the first thing
that made them drift was ADR-0013 itself.

Wei's answer would have been right, and is right in general: `fts_query` quotes every token
precisely because an unquoted identifier reaching MATCH means something other than what you
wrote. Had the quoting not been there, his was the fix. What made it wrong here is that the
quoting happens *after* a split that had already destroyed the token, so it faithfully quoted the
wrong two things.

Two consequences for anyone running this in production. Query-side analysis belongs in the index
identity next to the tokenizer. And the test that catches drift has to span both halves, which
makes it a round-trip test and rules out testing either side on its own."""},
 ],
},
{
 "category": CAT, "author": "priya",
 "title": "Dense leg is now worse than BM25 and mixed_version_check says the index is clean",
 "body": """Re-embedded `v1` under a new encoder tag. The job was killed roughly two thirds of
the way through, the box ran out of memory, and I restarted it with the same script, which picks
up where it left off.

Since then the dense leg has fallen behind the lexical one, which on this corpus is the wrong way
round:

| arm | committed evidence_recall | now |
|---|---|---|
| BM25 alone | 0.7118 | unchanged |
| Dense alone | 0.7733 | below the BM25 number |

The committed gap is `bm25 → dense +0.0616, ci (+0.0382, +0.0870)`. The gap has inverted. That is well outside the 0.02 gate tolerance and the paired bootstrap on the new run
does not straddle zero.

Ruled out:

- **Mixed versions.** First thing the runbook sends you to, and it says the index is fine:

  ```python
  >>> idx.mixed_version_check("v1")
  {'ok': True, 'tags': {'<new-tag>': 2430}}
  ```

  One tag. All 2,430 chunks. No second encoder anywhere in it.
- **Not the ANN path.** `ann=False`, so this is exact search over the stored vectors.
- **Not the reranker.** `rerank='none'` shows the same inversion.
- **Vectors are not corrupt.** No NaNs, norms all near 1, no zero rows, count matches.

Everything I know how to ask says the index is homogeneous and healthy, and the leg it feeds is
behaving like a different encoder. What is left to check?""",
 "replies": [
  {"by": "sofia", "body": """Check the ACL column before you go near the encoder. A re-embed
script that rebuilds `Chunk` objects from a different source can insert them with a narrower
`acl` than the rows they replace — the ids match, so it looks like an update, and nothing in the
run reports it.

If the resumed half wrote a narrower group list than the killed half, your dense leg is searching
a smaller permitted set than the lexical one and you would see exactly this shape. It would show
up concentrated in whichever persona holds the fewest groups, which here is `analyst` with
`G_PUBLIC` only.

Slice the run by persona. If `analyst` has collapsed and `counsel` has not, this is your bug and
it has nothing to do with embeddings at all."""},
  {"by": "dan", "body": """If it is not that, then it is the search structure rather than the
data. The ANN thread on this board ended with a graph that was correctly built and completely
unnavigable, and the graph is cached per index version, so a half-written index would have had
its graph built over whatever happened to be there at the time.

That thread also turned up a cache-poisoning bug where a `build_graph=False` call stored
`graph=None` and the ANN path silently fell back to exact search. A half-finished job is exactly
the situation that leaves a cache holding something built from a state that no longer exists.

Clear `_cache`, rebuild the graph, re-run."""},
  {"by": "priya", "body": """Neither, and I have checked both properly.

On Sofia's: it cannot be a *rewrite*, because `upsert`'s conflict clause does not touch `acl` —

```sql
ON CONFLICT(chunk_id,index_version) DO UPDATE SET
  text=excluded.text, vector=excluded.vector, tombstoned=0,
  content_hash=excluded.content_hash, embedder_tag=excluded.embedder_tag
```

An existing row keeps the `acl` it had. A fresh *insert* under a new id could carry a narrower
one, which is the version of Sofia's hypothesis that survives, so I checked it: row counts per
ACL group are identical to the snapshot I took before the re-embed, all four personas move
together, and `counsel`, which holds every group in this corpus, is down as much as `analyst`.
Uniform across the population, which is what sent me to the index in the first place.

On Dan's: `upsert` already clears `_cache` for the version it wrote, and I restarted the process
anyway, so there is no cached anything to poison. `ann=False` keeps the graph out of the path
entirely. I rebuilt it regardless and nothing changed, which I expected but it was cheap."""},
  {"by": "aarav", "body": """Genuine question rather than a hypothesis. How much of this reaches
the thing a user sees?

On this corpus every retrieval arm lands inside the noise band on `answer_correct`. That is
ADR-0015's third corrected finding: evidence recall spans 0.7118 to 0.7790 across arms, a 9.4%
relative range, and answer correctness does not move across any of them. The numerically best
answers came from the numerically worst retriever.

If the answers are the same, we have a metric problem and a Thursday. I would rather ship this
behind a ticket than hold a release for a leg that provably does not move the output."""},
  {"by": "tomas", "body": """No, and there are two separate reasons.

An index you cannot explain is not the same object as an index you have measured and accepted.
Priya does not know what is in it, so she does not know what else it does, and "answers look fine
on 243 questions" is a statement about 243 questions rather than about the index. None of those
questions is an identifier lookup, for one.

Also, do the operational step first and have the argument afterwards. The index is versioned
behind an alias, so put users back on the previous one now:

```python
idx.set_alias("live", "v_previous")
```

The playbook is blunt about this and it is right. A reverted system you are investigating beats a
broken system you are investigating."""},
  {"by": "wei", "body": """Your check is green because it is checking the wrong object.

`mixed_version_check` groups by `embedder_tag`. That column is a **label**, and it is written by
the same statement that writes the vector:

```sql
ON CONFLICT(chunk_id,index_version) DO UPDATE SET
  text=excluded.text, vector=excluded.vector, tombstoned=0,
  content_hash=excluded.content_hash, embedder_tag=excluded.embedder_tag
```

Whatever tag your resume script passed to `upsert` was stamped on every row it touched, including
rows where it did not compute a new vector.

Which it will not have, if your script uses the incremental shortcut ADR-0004 exists to enable.
That shortcut skips re-encoding when `content_hash` is unchanged, and it is keyed on the
**content**. Change the chunker and it is correct. Change the *encoder* and the key no longer
covers the thing that changed, so every unchanged chunk keeps its old vector and gets the new tag
written over the top of it.

Test against the vectors rather than the label. Take a sample of chunk ids, re-encode their text
with the current encoder, and compare with what is stored:

```python
sims = [float(stored[c] @ emb.encode_documents([text[c]])[0]) for c in sample]
```

Anything materially below 1 was not written by this encoder. I expect those to be exactly the
chunks whose `content_hash` did not change, and roughly the fraction of the corpus your job had
already passed when it died.""", "accepted": True},
  {"by": "priya", "body": """That is it. Roughly two thirds of the sample came back materially
below 1 against their own text, and every one of them is a chunk the resume script logged as
"unchanged, reusing stored vector". The kill point matches.

So the index really was half in one embedding space and half in another, and cosine across two
spaces is meaningless and silent, exactly as the playbook says. My check told me it was clean
because my script had already told my check it was clean.

Re-embedded from scratch with the shortcut disabled. Dense alone is back at 0.7733 and
`bm25 → dense` is back inside its committed interval.

What surprised me is how ordinary the mistake is. The shortcut is documented, correct, and I used
it in the one situation it does not cover. Nothing warned me, and the check that exists for this
family of failure reported success."""},
  {"by": "maintainer", "body": f"""Marked Wei's. Two things to take away, and the second one
generalises well past retrieval.

**A content hash covers the content, not the function applied to it.**
[ADR-0004]({ADR}/0004-stable-chunk-ids.md) buys incremental updates by saying an unchanged chunk
needs no new vector. That sentence holds only while the encoder is fixed. Any encoder change
invalidates every cached vector regardless of content, and the shortcut cannot know that, because
the encoder is not part of its key.

**A check whose input is written by the operation it audits cannot fail independently of it.**
`mixed_version_check` is a good check and it did its job for the failure it was written for, which
is two jobs running against one index under different tags. It cannot see one job lying
consistently. The version that can is the one Wei wrote: re-encode a sample and compare against
what is stored, which reads the artefact rather than the paperwork.

Aarav deserves an answer rather than an override, because he was right about the finding.
Retrieval on this corpus really does not move `answer_correct`. It is not a licence to ship an
index you cannot describe: "nothing we measured changed" is only as strong as the set of things
measured."""},
 ],
},
{
 "category": CAT, "author": "aarav",
 "title": "full_chain_recall dropped 0.0385 and nothing under raglab/ has changed",
 "body": """Gate failed on a branch that touches documentation and the corpus generator. No
retrieval code in the diff at all.

```
gate
  ok     evidence_recall        0.7645 → 0.7691  (+0.0046)
  FAIL   full_chain_recall      0.4686 → 0.4301  (-0.0385)   tolerance 0.03
  ok     answer_correct         0.4115 → 0.4102  (-0.0013)
```

`git log --oneline raglab/` has nothing since the last green run. `RetrievalConfig` diffed against
the previous run is identical field for field, including `k`, `alpha`, `fusion`, `rerank` and
`rerank_depth`.

I have a client readout on Thursday that quotes the committed 0.4686, so what I need to know is
whether that number is still true, rather than whether the gate can be persuaded to go green.

Ruled out so far:

- **Config drift.** Diffed, identical.
- **A stale kernel.** This is CI on a clean checkout rather than my notebook.
- **The reranker.** Same `rerank='cross'`, same depth.

The shape bothers me. Per-piece recall went *up* slightly and per-question recall fell hard, and
the release-gate doc describes that exact combination as the signature of a change that fills the
window with more of the evidence you already had. Except I have not made any change that could
fill a window with anything, and the two files I did touch are a markdown page and a padding
helper in the generator.""",
 "replies": [
  {"by": "dan", "body": """Before anyone hunts for a mechanism, is 0.0385 outside the noise band?

The tolerances are set at roughly the width of the paired-bootstrap interval for each metric at
n=243, and full chain's is 0.03, the loosest tolerance we set, against 0.02 for evidence recall. A move that is only a little past a
tolerance on the noisiest of the three metrics is the sort of thing that is a resample rather than
an event, and the playbook puts that check first for a reason.

Run `metrics.paired_bootstrap` on the two arms and look at whether the interval crosses zero. If
it does, there is nothing here to explain."""},
  {"by": "aarav", "body": """Ran it, on the dev slice and on the full 243. The interval does not
cross zero and it is not close to crossing zero. I also re-ran the failing commit twice to rule
out anything non-deterministic in the harness, and both runs land on the same 0.4301 to four
decimals, which is what I would expect: the corpus generator, the encoder and the ANN walk all
take an explicit seed.

So it is a real difference between two runs of code that is byte-identical under `raglab/`. That
is worse rather than better. A noisy number I could have explained to the client in a sentence;
a reproducible one I cannot explain at all is the thing I have to stand behind on Thursday.

Happy to be told I am ruling out the wrong things in the wrong order here."""},
  {"by": "priya", "body": """Then trust the signature and go looking for duplicates.

Per-piece up with per-question down is near-duplicate evidence crowding the window. You retrieve
a second copy of a chunk you already had, the per-piece average is unmoved or slightly up because
you still hold that piece, and a question that needed a *different* second piece loses its slot to
the copy.

The corpus generator is in your diff. If it now emits more near-duplicate passages, k=8 is holding
fewer distinct pieces than it was — `dedup=True` is a token-Jaccard filter at 0.82, so two
passages that paraphrase each other below that threshold both still land in the window.

Content-hash the top 8 per query on both runs and compare the distinct counts. That takes a minute
and either kills the hypothesis or hands you the fix."""},
  {"by": "wei", "body": """Priya's diagnosis and a bigger k are the same fix, and the second is
one line.

The k sweep here is unambiguous. Evidence recall on the shipped configuration is 0.7645 at k=8 and
0.8567 at k=20, and full chain climbs with it. If the window is crowded, stop running a crowded
window.

We held k=8 for a year for latency reasons that stopped being true after a hardware change, and
nobody re-measured until a customer complaint forced it. Raise it to 20, re-baseline in the same
PR with the reason and the interval in the body, and Thursday quotes a better number than the one
you were worried about losing."""},
  {"by": "aarav", "body": """Distinct content hashes in the top 8 are the same on both runs, query
by query. No duplicate crowding, so that is not it.

And I am not raising k to make a failure go away before I know what the failure is. If I
re-baseline now, I have moved the number I am about to put in front of a client using a change I
made because I could not explain the previous change. The gate doc names that move specifically:
never re-baseline to make a failing gate pass, because if you cannot explain the movement you do
not yet understand your change."""},
  {"by": "marcus", "body": """Both hypotheses test the retriever, and the retriever is not in
your diff. Look at what full-chain recall is a function of.

Evidence recall is a per-piece average, so it is linear in the pieces and moves slowly. Full chain
needs *every* piece, so under independence at per-piece probability p it is p raised to the pieces
that question requires, averaged over questions. A product is convex in its exponent, which makes
the second metric far more sensitive to the **distribution of pieces per question** than to p.

Our committed distribution over the 207 answerable questions:

| pieces | 1 | 2 | 3 | 4 | 6 |
|---|---|---|---|---|---|
| questions | 21 | 59 | 21 | 100 | 6 |

Weighting p = 0.7645 over that predicts **0.4603**; measured is 0.4686, so +0.0083 above it. This
corpus sits at independence, which makes the prediction close to the whole story.

The 4-piece bucket alone is 100 of 207 and contributes p⁴, so moving a handful of questions into
it drops full chain hard while the per-piece average barely notices.

So check the corpus shape first:

```python
len(bundle.documents), len(bundle.questions)
idx.stats("v1")                         # {"documents": …, "chunks": …}
metrics.resolve_gold(q, chunks)[1]      # anchors no chunk can satisfy
```

Committed shape is 484 documents, 2,430 chunks, 243 questions, 207 answerable, 36 null. If any of
that moved, or `resolve_gold` returns unresolved anchors it did not last week, your eval set
changed and the delta between the runs is uninterpretable.

I would also not put 0.4686 in front of anyone on Thursday under any outcome here. The frozen
slices have not been re-run against whatever this corpus now is, and that is next week.""", "accepted": True},
  {"by": "aarav", "body": """The shape moved. Chunk count is not 2,430 any more, the pieces
histogram is not the one above, and `resolve_gold` returns unresolved anchors on a handful of
questions that resolved cleanly last week.

Cause: the padding helper draws from a `random.Random(SEED + 5)` stream shared with everything
downstream of it. Consuming a different number of draws shifted the document bodies. Chunk ids are
`doc_id:ordinal:sha1(text)[:10]`, so new text means new ids, and gold anchors that resolved against
the old chunk boundaries stopped resolving against the new ones. The questions that lost an anchor
are exactly the ones that stopped scoring full chain.

The retriever was never involved. It scored a different eval set and reported the difference as a
regression, correctly, in the only language the gate has.

Docs change pushed on its own branch, generator change on its own with its own re-baseline. Green
on both.

On Thursday I am quoting 0.4686 with the corpus commit beside it. That is the honest version and
it costs one extra sentence. Waiting a week to say a number we have measured and can point at
would cost more credibility than it buys."""},
  {"by": "maintainer", "body": f"""Marked Marcus's. Aarav's last paragraph is the right call under
[ADR-0009]({ADR}/0009-frozen-slice-lifecycle.md): a *claim* has to clear both frozen slices, while
a committed baseline quoted with the commit it was cut from is a different kind of statement and
does not need next week.

Three things worth keeping.

**The gate cannot catch this and says so.** Its own limitations section is explicit: it compares
against a baseline computed on the current eval set, so change both and it passes happily. Here it
failed rather than passed, which was luck — the corpus moved far enough to trip a tolerance. A
smaller change would have gone through green with a baseline that quietly no longer described the
same questions. The rule against changing the eval set and the code in one commit is a rule
because no check can enforce it.

**This is the family the fusion retraction came from.**
[ADR-0015]({ADR}/0015-correct-the-fusion-finding.md) puts its most likely origin at a label slip,
in which 0.7645 ended up attributed to BM25 alone, whose real number is 0.7118. Once an
attribution is loose, a mechanism story gets built on it and nobody re-runs the measurement.

**And on the arithmetic.** The retracted version of that independence calculation quoted 128
single-hop, 61 two-hop and 18 three-plus questions, predicted 0.6838, and announced a 21-point
shortfall. Those counts were invented. Marcus's distribution is the one the harness prints, which
is why his version is checkable and the old one never was."""},
 ],
},
{
 "category": CAT, "author": "sofia",
 "title": "The analyst persona's result count changes when legal ingests documents it cannot see",
 "body": """Reporting this as a leak rather than a bug, because that is what it is regardless of
cause.

Legal ingested a batch into `G_LEGAL` overnight. Nothing in `G_PUBLIC` changed. The `analyst`
persona holds `G_PUBLIC` and nothing else, so from its position in the world that ingest did not
happen.

Two things moved for `analyst` this morning:

1. **Result lists got shorter.** Asking for 10 now returns fewer than 10 on queries that returned
   a full page yesterday, and the shortfall varies by query.
2. **A top-8 reordered.** Same query text, same permitted documents, different order.

Both are observable by an unprivileged user with no access to anything that changed. That is an
oracle. Somebody watching how their own result count moves overnight can infer that documents were
ingested, and by varying query terms can narrow down what those documents are about. In our
setting that is a reportable event rather than a defect queue item.

Ruled out:

- No deploy. `git log` is empty for the window.
- Public documents unchanged: same document count, same chunk ids, same content hashes.
- The `acl` column on the new rows is correct, `G_LEGAL` only, verified by query.
- `assert_persona_isolation` is green. No `analyst` result is a document it may not see.

So nothing leaks *content*. What leaks is the shape of the result set, which is the channel
ADR-0011 warns about and which I thought pre-filtering had closed. I want to take `analyst` search
offline until we know how wide it is.""",
 "replies": [
  {"by": "dan", "body": """The shorter lists at least have a standard fix. If you ask for 10 and
filter afterwards you get fewer than 10, so ask for more: fetch ten times what you need, filter,
truncate back to 10.

Every write-up I have read does some version of that, it costs one constant, and it does not
require anybody to understand the ranking. Worth trying before we start talking about taking a
persona offline, because that is a big lever for a symptom nobody has priced yet."""},
  {"by": "sofia", "body": """That is the fix ADR-0011 rejects, and the reason is arithmetic rather
than taste. Over-fetching to compensate is unbounded, because the multiplier you need is a
function of the requesting user's selectivity. A user permitted 0.1% of the corpus needs k = 10,000
to reliably see 10 results, and there is no single constant that is both affordable for `counsel`
and sufficient for the most restricted role.

It also leaves the count a function of permissions, just with a bigger pool behind it, and it does
nothing at all about the reordering, which is the half I care about more."""},
  {"by": "marcus", "body": """Then treat the count as the leaking channel and reduce its
information content directly. Do not publish an exact count: round it to a bucket, or add
zero-mean noise and publish the noised value.

You would want the bucket width chosen against how much an observer learns per observation rather
than picked by eye, and there is a well-developed literature for doing that properly. The shape of
the fix is not controversial and it does not require you to find the cause first, which is worth
something while the cause is still unknown."""},
  {"by": "tomas", "body": """It becomes controversial the moment the observer can repeat the query.

Noise redrawn per request averages away over repeated identical queries, and noise fixed per query
is a constant the observer subtracts once they have a day of history. To hold up you would have to
bind it to the pair of user and query and keep it stable for the life of the corpus, at which
point it is a lookup table rather than noise, and it is a lookup table that is wrong in a fixed
direction for every user.

Separately, and before any of this: what pages at 3am? Right now nothing does. Aggregate recall
cannot see a per-group collapse, which is the entire argument for a per-ACL eval slice, and last
time this came up it was left open against the eval set rather than the retriever."""},
  {"by": "wei", "body": """Solve it structurally instead. One index per ACL group.

A user queries only the index they are entitled to, the corpus statistics inside that index are
computed over documents they can see, and both of Sofia's symptoms become impossible rather than
mitigated. We ran per-tenant indexes for three years and never had this conversation once.

Storage is not the constraint people assume either. Duplication is bounded by how many groups a
document belongs to, and in every corpus I have worked on that number is close to one."""},
  {"by": "sofia", "body": """It is close to one here too and it still does not work, which is the
part I had to be talked through when we first wrote this down.

ADR-0011 does the arithmetic at 14 ACL groups with 1.3 groups per document: partitioning duplicates
roughly 4% of documents fourteen times. Storage is affordable. **Consistency is not.** Fourteen
copies updated non-atomically means a window in which the answer depends on who asked, and in a
regulated setting that is two different answers to one question with an audit trail proving it.

Your per-tenant case is a different problem. When groups are disjoint and every document belongs to
exactly one, there is nothing to update twice and the objection disappears."""},
  {"by": "maintainer", "body": f"""Marked. Sofia's two symptoms have different causes and only one
is a bug.

**The short lists are a code bug with a free fix.** Check `cfg.filter_mode`. It defaults to
`"pre"`, but the retrievers pass the ACL through only when it is:

```python
acl = cfg.acl_groups if cfg.filter_mode == "pre" else None
```

In post mode the ACL never reaches the retrievers at all: `pack_context` fills k from the whole
corpus and `pipeline.py` drops the forbidden rows afterwards, so a narrowly-scoped user gets two
chunks where a broad one gets eight. That is k-collapse, and it moves whenever the invisible part
of that pool grows. (On the ANN path it is worse — `ann_vector` also *traverses* through nodes
the user cannot see — but `cfg.ann` defaults to False, so that is not what is biting you here.)
Most likely copied out of the notebook cell that runs both modes to show the recall gap.

**The reordering survives that fix and is not a bug.** Scores come from
`bm25(chunks_fts, 4.0, 2.0, 1.0)`, and BM25's IDF is computed over the whole FTS table, which is
one inverted index and is not ACL-filtered. Ingest legal documents carrying a term and that term's
document frequency moves for **every** user, so a permitted document's score changes and a close
pair swaps. Pre-filtering keeps forbidden documents out of your results, not out of the statistics
that rank them.

That is the score leak [ADR-0011]({ADR}/0011-prefilter-acl.md) names, observed rather than
predicted for the first time. Closing it needs per-group statistics, so per-group indexes, the
trade rejected above. It becomes an accepted risk with an owner.

Tomás is right that nothing pages. A per-ACL eval slice is a change to the eval set rather than the
retriever, which is why it was easy to defer, and it is the only thing that would have caught 0.31
recall for the most-restricted role against 0.94 unrestricted with a clean aggregate.""", "accepted": True},
  {"by": "sofia", "body": """`filter_mode` was `"post"` in the service config and `"pre"`
everywhere else, and it came from a notebook, as guessed. Set to `"pre"`, counts stopped moving
overnight, and the shortfall is gone.

The IDF channel is still open, and it now has a ticket, an owner and a paragraph that says what it
is, rather than a silence that implies it does not exist.

Two things I got wrong, both worth writing down since I opened this asking to take a persona
offline.

I called one channel when there were two, and the one I could see was the one with a free fix while
the one I could not see is the one we have to live with. Had we only fixed the counts, I would have
closed this as resolved and left the harder half undocumented.

And taking `analyst` offline would have been the wrong call. It removes the observation rather than
the channel, and it removes it from us as well as from anyone watching. A leak you can measure is
in better shape than one you have stopped looking at."""},
 ],
},
]
