"""Further threads: a cost investigation, a derivation argument, and an exercise."""
from __future__ import annotations

THREADS = [
{
 "category": "Debugging Clinic", "author": "aarav",
 "title": "Prompt cache hit rate is 4%. The prefix looks identical to me.",
 "body": """Costs are roughly triple what I modelled because almost nothing is hitting the
prompt cache. Provider reports a 4% hit rate.

The prefix looks stable to me. System prompt, then instructions, then eight retrieved chunks,
then the question. The system prompt and instructions never change, and they are ~1,100 tokens
— well over the minimum cacheable length.

What I have ruled out: the model version has not changed mid-run, and I am not sending different
system prompts per user.

Where else does a cache miss come from?""",
 "replies": [
  {"by": "dan", "body": """Is the cache keyed on the whole prompt or just the prefix? If it is
the whole prompt then the chunks changing per query would explain it."""},
  {"by": "wei", "body": """Prefix, not the whole prompt — that is the point of prefix caching. So
Dan's explanation would be right for a naive full-prompt cache and is not the issue here.

Aarav: paste the first 200 characters of two consecutive requests, byte for byte. Not what your
template looks like — what actually went over the wire. Nine times out of ten the answer is
visible there and invisible in the template."""},
  {"by": "aarav", "body": """That was it, and it is embarrassing.

```
Request 1: "You are a retrieval assistant. Current time: 2026-08-24T09:14:02Z\\nYou have..."
Request 2: "You are a retrieval assistant. Current time: 2026-08-24T09:14:07Z\\nYou have..."
```

There is a timestamp in the system prompt. Five characters different, at position 58, and every
single token after it is uncacheable — which is the entire prompt.

I added that timestamp three weeks ago so the model could reason about "as of" questions. It
cost roughly two thirds of the inference budget and nobody noticed because the feature worked
fine."""},
  {"by": "marcus", "body": """This is the single most common prompt-cache bug and it is worth
stating as a rule rather than an anecdote, because it generalises past timestamps.

Prompt caching requires a **byte-identical prefix**. Therefore the ordering of your context
blocks is a cost decision, not a formatting one, and it has a strict rule: **order blocks by
volatility, most stable first.** Anything that changes per request goes last, after everything
you want cached.

Your timestamp belongs immediately before the question, not in the system prompt. It is the most
volatile thing you have and you put it at position 58.

The corollary people miss: this makes retrieved chunks — which change every query — a hard
barrier. Everything after them is uncacheable, so the question goes after them and nothing else
does.""", "accepted": True},
  {"by": "tomas", "body": """Instrument it. Cache hit rate belongs on the dashboard next to
latency and cost, because this failure is completely silent — the feature works, the answers are
right, and the only symptom is a bill.

We alert on hit rate dropping more than 10 points week over week. It has caught two regressions,
both of them somebody adding a field to the system prompt for a good reason."""},
  {"by": "aarav", "body": """Moved the timestamp to just before the question. Hit rate 4% → 71%.
Cost per query down 58%.

Adding Tomás's alert. Also adding a test that asserts the first N tokens of the assembled prompt
are identical across two different queries, which would have caught this the day I introduced
it."""},
 ],
},
{
 "category": "Math & Theory", "author": "dan",
 "title": "Why is there a +0.5 in the BM25 IDF? Someone told me it is 'just smoothing'",
 "body": """The IDF term in BM25 is usually written

$$\\mathrm{IDF}(t) = \\log\\frac{N - n_t + 0.5}{n_t + 0.5}$$

I was told the 0.5s are "just smoothing so you do not divide by zero". That cannot be the whole
story, because you could smooth with any constant. Why 0.5 specifically, and why in both the
numerator and the denominator?""",
 "replies": [
  {"by": "lena", "body": """It is not arbitrary and the answer is genuinely interesting.

BM25's IDF is not an information-theoretic quantity invented for the formula — it falls out of
the **Robertson–Spärck Jones relevance weight**. Under a binary independence model, the log-odds
contribution of observing term $t$ is

$$w_t = \\log \\frac{p_t(1-q_t)}{q_t(1-p_t)}$$

where $p_t = P(t \\mid \\text{relevant})$ and $q_t = P(t \\mid \\text{non-relevant})$.

With no relevance judgements you estimate $q_t \\approx n_t/N$ and treat $p_t$ as roughly
constant, and the expression collapses to the familiar form. The 0.5s are what you get from a
**Jeffreys prior** — a $\\mathrm{Beta}(\\tfrac12, \\tfrac12)$ prior on the underlying
probabilities, which is the reference prior for a Bernoulli parameter.

So: it is smoothing, but it is a specific smoothing with a derivation, and 0.5 is the Jeffreys
value rather than a choice. Both numerator and denominator get it because both are estimates of
a Bernoulli proportion and the prior applies to each.""", "accepted": True},
  {"by": "marcus", "body": """Worth adding the practical consequence, because there is one and it
bites.

This form can go **negative** for a term appearing in more than half the documents:
$n_t > N/2$ makes the numerator smaller than the denominator. A term in 90% of documents
contributes a negative score, so a document containing it ranks *below* one that does not.

That is defensible under the probabilistic model and usually undesirable in practice — it means
adding a common word to your query can actively demote correct documents. Which is why most
implementations, including Lucene's, use

$$\\log\\left(1 + \\frac{N - n_t + 0.5}{n_t + 0.5}\\right)$$

The $1 +$ keeps it non-negative. It is a deliberate departure from the derivation, and knowing
that it *is* a departure is the part that separates someone who read the formula from someone
who read the paper."""},
  {"by": "dan", "body": """Checked our implementation and it has the `1 +`. So we are using the
Lucene variant, which I did not know was a variant.

Reproduced the negative case on a toy corpus to see it: term in 3 of 4 documents, raw RSJ form
gives IDF −0.51. Good to have seen it rather than just been told."""},
  {"by": "maintainer", "body": """Marked Lena's, and Marcus's follow-up is the interview-grade
half.

The pattern worth internalising: **"just smoothing" is almost always a real derivation somebody
compressed.** Constants in retrieval formulas — the 0.5 here, the 60 in RRF, the log base in nDCG
— each come from an argument, and the argument tells you when the formula stops applying.

Full treatment, including the follow-up about bimodal document lengths, is in the mathematics
interview bank."""},
 ],
},
{
 "category": "Exercises & Submissions", "author": "maintainer",
 "title": "EX-07 · Find the k where more context starts making answers worse",
 "body": """**Difficulty** ★★★☆☆ · **Seam** ⑧ packer · **Time** 2 h · **Notebook** `05`

### Setup
Evidence recall rises monotonically with k. Answer correctness does not. Somewhere between them
there is a k where adding another chunk stops helping and starts hurting.

### Task
Sweep k from 2 to 20. Plot evidence recall, context precision and answer correctness on the same
axis. Find the crossover and explain the mechanism.

### Acceptance
- All three curves, same plot, k on the x-axis.
- The k you would ship, with the reason.
- An interval on the answer-correctness difference between your chosen k and k+4. If they
  overlap, say so — "the curve is flat here" is a legitimate and useful finding.

### The trap
The crossover is not where the curves cross visually. It is where the *derivative* of answer
correctness goes negative, and with n=243 that derivative is noisy enough that eyeballing it will
give you a different answer than measuring it. Bootstrap the difference between adjacent k.

Reply with your approach first.""",
 "replies": [
  {"by": "priya", "body": """**Approach.** One index, sweep k in the retrieval config only,
hold everything else fixed. Bootstrap adjacent-k differences rather than reading the plot.

Prediction: correctness peaks around k=8–10, because that is roughly where context precision
falls below ~0.25 and the generator starts having more distractor than evidence."""},
  {"by": "priya", "body": """| k | evidence_recall | ctx_precision | answer_correct |
|---|---|---|---|
| 2 | 0.5912 | 0.6104 | 0.3210 |
| 5 | 0.7301 | 0.3512 | 0.3909 |
| 8 | 0.7645 | 0.2433 | 0.4115 |
| 12 | 0.7913 | 0.1702 | 0.4062 |
| 16 | 0.8067 | 0.1301 | 0.3951 |
| 20 | 0.8154 | 0.1088 | 0.3884 |

Peak correctness at k=8, and it is a genuinely flat top: k=8 vs k=12 is −0.0053,
[−0.041, +0.030]. Inside the band. So the honest statement is that correctness is flat between
about 8 and 12 and clearly declining by 16.

Ship k=8, because it is the cheapest point on a flat top. Recall keeps climbing past it and that
is precisely the trap — the metric that looks best is not the metric the user experiences."""},
  {"by": "dan", "body": """Does this mean recall past k=8 is useless? It feels wasteful to
retrieve evidence and then have it hurt you."""},
  {"by": "wei", "body": """Not useless — mis-used. The extra evidence at k=12 is real evidence;
the generator is just worse at finding it in a longer context with more distractors.

Which points at the actual fix, and it is not a smaller k. Retrieve wide, **then compress**:
pull 20, rerank, and pack the 8 best *after* reranking rather than the 8 best from first-stage
retrieval. You keep the recall of k=20 and the precision of k=8.

That is seam ⑧ and it is the difference between "how much context" and "how much *of the right*
context", which is the question the exercise is really asking.""", "accepted": True},
  {"by": "maintainer", "body": """Marked Wei's. Priya's submission is full credit — one change,
intervals on the adjacent-k differences, and an honest "flat top" rather than a spurious peak
read off a plot.

Note what the flat top means for anyone repeating this: a submission claiming a sharp optimum at
a specific k has almost certainly eyeballed the curve. The derivative is noisy at n=243 and the
bootstrap says so.

The recall/correctness divergence here is the single clearest demonstration in the curriculum of
why you gate on the metric the user experiences rather than the one that improves most easily."""},
 ],
},
]
