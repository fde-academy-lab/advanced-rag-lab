"""
Token accounting, prompt caching, latency budgets, and unit economics.

Cost is a design constraint, not an afterthought -- in client work it is often
the constraint that picks the architecture. This module makes the deck's cost
slides executable, so "AI is expensive" becomes a line-item table with a total
you can defend.

Four categories on the same request, kept separate because you cannot optimise
what your dashboard has already summed into one number:

    input                 new prompt tokens
    output                generated tokens
    cache_write           reusable prefix processed and stored
    cache_read            that prefix reused on a later request

Rates below are the illustrative ones the deck uses ($3 / MTok in,
$15 / MTok out, reads at 0.1x). They are placeholders on purpose. Providers
change prices; the arithmetic is the transferable part. Put real numbers in
`Rates` before you quote anything to a client.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Rates:
    """Per-million-token prices. Illustrative -- override before quoting."""

    input_per_mtok: float = 3.00
    output_per_mtok: float = 15.00
    cache_read_multiplier: float = 0.10      # Anthropic: 0.1x base input
    cache_write_multiplier: float = 1.25     # 5-minute retention; 2.0x for 1 hour
    rerank_per_1k_docs: float = 0.008
    embed_per_mtok: float = 0.02
    name: str = "illustrative"

    def cost(self, input_tokens=0, output_tokens=0, cache_read=0, cache_write=0):
        return (
            input_tokens * self.input_per_mtok / 1e6
            + output_tokens * self.output_per_mtok / 1e6
            + cache_read * self.input_per_mtok * self.cache_read_multiplier / 1e6
            + cache_write * self.input_per_mtok * self.cache_write_multiplier / 1e6
        )


ANTHROPIC_5M = Rates(cache_write_multiplier=1.25, name="anthropic · 5-minute cache")
ANTHROPIC_1H = Rates(cache_write_multiplier=2.00, name="anthropic · 1-hour cache")
OPENAI_STYLE = Rates(cache_read_multiplier=0.25, cache_write_multiplier=1.25,
                     name="openai-style · explicit prefix")


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    rerank_docs: int = 0
    embed_tokens: int = 0

    def __add__(self, other):
        return Usage(*[getattr(self, f) + getattr(other, f) for f in
                       ("input_tokens", "output_tokens", "cache_read", "cache_write",
                        "rerank_docs", "embed_tokens")])

    def cost(self, rates: Rates):
        return (rates.cost(self.input_tokens, self.output_tokens, self.cache_read,
                           self.cache_write)
                + self.rerank_docs / 1000 * rates.rerank_per_1k_docs
                + self.embed_tokens * rates.embed_per_mtok / 1e6)


class PromptCache:
    """A prefix cache with the property that actually matters: a prefix is a
    hit only if it is byte-identical to what was written.

    Change one character near the front of the prompt and everything after it
    misses. That single rule is the whole of cache engineering, and this class
    exists so a notebook can demonstrate it rather than assert it.
    """

    def __init__(self, ttl_requests=None):
        self.store = {}
        self.hits = 0
        self.misses = 0
        self.writes = 0
        self.ttl = ttl_requests
        self._clock = 0

    def lookup(self, prefix_text, tokens):
        import hashlib

        self._clock += 1
        key = hashlib.sha1(prefix_text.encode()).hexdigest()
        entry = self.store.get(key)
        if entry and (self.ttl is None or self._clock - entry["at"] <= self.ttl):
            self.hits += 1
            entry["at"] = self._clock
            return Usage(cache_read=tokens)
        self.store[key] = {"at": self._clock, "tokens": tokens}
        self.misses += 1
        self.writes += 1
        return Usage(cache_write=tokens)

    @property
    def hit_rate(self):
        total = self.hits + self.misses
        return self.hits / total if total else 0.0

    def report(self):
        return {"requests": self.hits + self.misses, "hits": self.hits, "misses": self.misses,
                "hit_rate": round(self.hit_rate, 3), "distinct_prefixes": len(self.store)}


# --------------------------------------------------------- latency budget ----
LATENCY_BUDGET = [
    ("Query embed + rewrite", 150),
    ("Hybrid retrieve, N=100", 90),
    ("Fusion + dedup", 20),
    ("Cross-encoder rerank, 50", 220),
    ("Pack + guardrail checks", 50),
    ("Generation, ~450 out tok", 1550),
    ("Headroom for the tail", 420),
]
LATENCY_P95_TARGET_MS = 2500


def latency_model(cfg=None, n_candidates=100, rerank_depth=50, out_tokens=450, reranker="cross",
                  turns=1):
    """A component-wise latency estimate with the deck's coefficients.

    Not a benchmark of this laptop -- a budget. The value of a budget is that it
    turns an argument about architecture into arithmetic, and it shows
    immediately that generation dominates, which is why cutting the reranker to
    save 200 ms is usually the wrong trade.
    """
    rerank_ms = {"none": 0, "late": 10 + 0.6 * rerank_depth, "cross": 20 + 4.0 * rerank_depth,
                 "llm": 300 + 12.0 * rerank_depth}.get(reranker, 0)
    items = [
        ("Query embed + rewrite", 150),
        (f"Hybrid retrieve, N={n_candidates}", 40 + 0.5 * n_candidates),
        ("Fusion + dedup", 20),
        (f"Rerank {reranker}, {rerank_depth}", rerank_ms),
        ("Pack + guardrail checks", 50),
        (f"Generation, ~{out_tokens} out tok", 250 + 2.9 * out_tokens),
    ]
    per_turn = sum(v for _, v in items)
    total = per_turn * turns
    items.append(("Headroom for the tail", max(0.0, LATENCY_P95_TARGET_MS - total)))
    return {"items": items, "subtotal_ms": total, "turns": turns,
            "target_ms": LATENCY_P95_TARGET_MS, "within_budget": total <= LATENCY_P95_TARGET_MS}


# ---------------------------------------------------------- unit economics ---
def unit_economics(prefix_tokens=3000, k=8, tokens_per_chunk=550, question_tokens=200,
                   output_tokens=450, rerank_candidates=50, rates: Rates = None,
                   cached=True, monthly_queries=200_000):
    """One grounded answer, priced line by line -- the deck's worked example.

    Returns the table and the totals so a notebook can re-run it under a
    different k, a different cache policy, or a client's real rate card.
    """
    rates = rates or Rates()
    evidence_tokens = k * tokens_per_chunk
    lines = []
    if cached:
        c = rates.cost(cache_read=prefix_tokens)
        lines.append(("Cached prefix (system, tools, shots)", prefix_tokens,
                      rates.input_per_mtok * rates.cache_read_multiplier, c))
    else:
        c = rates.cost(input_tokens=prefix_tokens)
        lines.append(("Uncached prefix (system, tools, shots)", prefix_tokens,
                      rates.input_per_mtok, c))
    lines.append((f"Evidence, k={k} x {tokens_per_chunk} tok", evidence_tokens,
                  rates.input_per_mtok, rates.cost(input_tokens=evidence_tokens)))
    lines.append(("Question + conversation state", question_tokens, rates.input_per_mtok,
                  rates.cost(input_tokens=question_tokens)))
    lines.append(("Generated answer", output_tokens, rates.output_per_mtok,
                  rates.cost(output_tokens=output_tokens)))
    lines.append((f"Rerank {rerank_candidates} candidates (hosted)", None, None,
                  rerank_candidates / 1000 * rates.rerank_per_1k_docs))
    lines.append(("Query embedding + ANN search", None, None, 0.00004))
    total = sum(l[3] for l in lines)
    return {"lines": lines, "total_per_query": total,
            "monthly": total * monthly_queries, "monthly_queries": monthly_queries,
            "rates": rates}


COST_LEVERS = [
    (1, "Cache the stable prefix; reorder the prompt by volatility", "15–30%", "Nothing",
     "free"),
    (2, "Deduplicate near-identical chunks before packing", "5–15%",
     "Usually improves it — duplicates are distractors", "free"),
    (3, "Cap output length and enforce a terse schema", "10–25%",
     "None if the contract is well specified", "free"),
    (4, "Lower k after proving full-chain recall holds", "20–40%",
     "Real risk on multi-hop — measure the tail, not the mean", "trade"),
    (5, "Route easy queries to a smaller model", "30–60%",
     "Needs a router you must also evaluate — a second system", "trade"),
    (6, "Semantic caching of full answers", "varies wildly",
     "A near-miss cache hit serves a confidently wrong answer", "trade"),
    (7, "Drop the reranker", "~2%",
     "The worst trade on this list — large quality loss, trivial saving", "avoid"),
]
