"""
Context assembly: turning ranked hits into the exact bytes the model reads.

The context window is the one budget with a hard wall, so this module treats it
as an allocation problem with named slices and hard caps, exactly as the deck's
32k budget slide does. Two properties are enforced rather than hoped for:

  * Provenance survives. Every evidence block carries a short opaque source ID,
    the doc_id and chunk ordinal, the publication date, and the score -- which
    is what lets you replay a retrieval and diff two packed contexts.
  * Nothing is truncated mid-chunk. Whole blocks are dropped by rank when the
    budget runs out, because half a chunk breaks its own citation.

Prompt segments are emitted in volatility order -- things that change per
release first, per tenant next, per query last -- so the stable prefix is
cacheable. That ordering is worth 15-30% of the input bill and costs nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .chunking import approx_tokens

ABSTAIN_TOKEN = "INSUFFICIENT_EVIDENCE"

SYSTEM_CONTRACT = (
    "Answer only from EVIDENCE. Cite every factual claim as [S#].\n"
    "If EVIDENCE is insufficient or conflicting, reply exactly: " + ABSTAIN_TOKEN + ".\n"
    "Do not use knowledge that is not present in EVIDENCE."
)

OUTPUT_CONTRACT = 'OUTPUT\nJSON: {"answer": str, "citations": [str], "sufficient": bool}'


@dataclass
class BudgetSlice:
    name: str
    cap: int
    on_overflow: str


DEFAULT_BUDGET = [
    BudgetSlice("System instructions + output contract", 2200,
                "Nothing breaks — but every edit invalidates the prompt cache below it"),
    BudgetSlice("Tool / schema definitions", 1600,
                "Tool selection degrades before the token limit does"),
    BudgetSlice("User query + conversation state", 1000,
                "Summarise older turns; never silently drop the current question"),
    BudgetSlice("Retrieved evidence, k chunks", 18000,
                "Drop whole chunks by rank — never truncate a chunk, it breaks its citation"),
    BudgetSlice("Output reserve", 4500,
                "The answer is cut off mid-sentence — the most visible failure on this list"),
    BudgetSlice("Headroom", 4700,
                "Absorbs tokenizer variance across languages and a long retry"),
]


@dataclass
class PackedContext:
    prompt: str
    blocks: list                 # [{sid, chunk_id, doc_id, ordinal, text, score, ...}]
    tokens: dict                 # per-slice token counts
    dropped: list                # hits that did not fit
    source_map: dict             # "S1" -> chunk_id

    @property
    def total_tokens(self):
        return sum(self.tokens.values())

    def resolve(self, sid):
        return self.source_map.get(sid)


def evidence_block(sid, hit, show_score=True):
    """One [S#] block. The annotations are debugging affordances, not decoration.

    doc_id plus chunk ordinal is what lets you replay the exact retrieval and
    diff the packed context between two runs. The date has to be *in the block*
    because a temporal question is unanswerable if publication dates only live
    in the index.
    """
    total = getattr(hit, "n_chunks", None)
    ord_str = f"{hit.ordinal + 1}" + (f"/{total}" if total else "")
    head = (f'[{sid}] title: "{hit.title}"\n'
            f"source: {hit.source} · published: {hit.published}\n"
            f"doc_id: {hit.doc_id} · chunk: {ord_str}")
    if show_score:
        head += f" · score: {hit.score:.3f}"
    return head + "\n---\n" + hit.text.strip()


def build_prompt(question, hits, k=8, token_cap=6000, show_score=True, tenant_config="",
                 conversation="", tools="", system=SYSTEM_CONTRACT, restate_question=True):
    """Assemble the prompt in volatility order and return a PackedContext.

    Order: contract, tools, tenant config, conversation, evidence, question.
    Everything before "evidence" is stable across queries and therefore
    cacheable; everything after it changes every call.
    """
    blocks, source_map, dropped = [], {}, []
    used = 0
    for i, h in enumerate(hits[:k], 1):
        sid = f"S{i}"
        text = evidence_block(sid, h, show_score)
        t = approx_tokens(text)
        if used + t > token_cap:
            dropped.append(h)
            continue
        blocks.append({"sid": sid, "chunk_id": h.chunk_id, "doc_id": h.doc_id,
                       "ordinal": h.ordinal, "score": h.score, "text": h.text,
                       "title": h.title, "published": h.published, "source": h.source,
                       "rendered": text, "tokens": t})
        source_map[sid] = h.chunk_id
        used += t
    dropped += list(hits[k:])

    parts = [system]
    if tools:
        parts.append("TOOLS\n" + tools)
    if tenant_config:
        parts.append("TENANT\n" + tenant_config)
    if conversation:
        parts.append("CONVERSATION\n" + conversation)
    parts.append("EVIDENCE\n" + ("\n\n".join(b["rendered"] for b in blocks) or "(none)"))
    parts.append("QUESTION\n" + question)
    if restate_question:
        # A short recap at the tail puts the task in the strong end position.
        parts.append("Answer the QUESTION above using only EVIDENCE.")
    parts.append(OUTPUT_CONTRACT)
    prompt = "\n\n".join(parts)

    tokens = {
        "system": approx_tokens(system) + approx_tokens(OUTPUT_CONTRACT),
        "tools": approx_tokens(tools) if tools else 0,
        "tenant": approx_tokens(tenant_config) if tenant_config else 0,
        "conversation": approx_tokens(conversation) if conversation else 0,
        "evidence": used,
        "question": approx_tokens(question),
    }
    return PackedContext(prompt, blocks, tokens, dropped, source_map)


def cacheable_prefix(packed: PackedContext):
    """The share of the prompt that never changes per query.

    This is the number to watch next to p95 latency: a cache hit rate that
    drops overnight almost always means someone edited the top of the prompt.
    """
    stable = packed.tokens["system"] + packed.tokens["tools"] + packed.tokens["tenant"]
    total = packed.total_tokens
    return {"stable_tokens": stable, "volatile_tokens": total - stable,
            "stable_share": stable / total if total else 0.0}


PROMPT_VOLATILITY = [
    ("Role, policy, output contract", "per release", 1),
    ("Tool / schema definitions", "per release", 2),
    ("Few-shot exemplars", "per release", 3),
    ("Tenant / persona configuration", "per tenant", 4),
    ("Conversation history", "per turn", 5),
    ("Retrieved evidence", "per query", 6),
    ("The question", "per query", 7),
]

CACHE_KILLERS = [
    ("A timestamp in the system prompt",
     'Today is 2026-08-31 14:22:07 invalidates the prefix every second',
     "Round it to the day, or move it to the tail"),
    ("A session or request ID near the front",
     "Unique per call, so nothing after it ever hits",
     "Move it below the evidence, or drop it from the prompt entirely"),
    ("Non-deterministic JSON ordering in tool schemas",
     "The same schema serialises differently between processes",
     "Sort keys when serialising"),
    ("A/B testing the system prompt per request",
     "Two variants means two caches and half the hit rate on each",
     "Pin one variant per deployment, not per request"),
]
