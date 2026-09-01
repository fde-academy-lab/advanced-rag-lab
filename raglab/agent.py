"""
Agentic search: decompose, choose a tool, retrieve, check sufficiency, stop.

The sufficiency check is the whole design. Without it the loop either stops too
early -- a two-hop question answered from one hop, with full confidence -- or
never stops, and a single hard question costs forty times a normal one. So it
is a separate, cheap, schema-constrained decision here, not a vibe inside the
main prompt.

Every stop condition from the deck is a config value with a default, written
down before the loop was written:

    success   sufficiency satisfied · no new information · confidence plateau
    exhausted turn cap · token budget · wall clock · repeat detector

A budget exhaustion produces an explicit partial answer with a stated gap. It
never produces a confident synthesis of half the evidence, and the stop reason
travels in the trace.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from .context import build_prompt
from .embed import tokenize

ID_RX = re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+\b|\b[A-Z]{3,}-\d+\b")


@dataclass
class AgentBudget:
    max_turns: int = 5
    max_evidence_tokens: int = 6000
    wall_clock_s: float = 20.0
    max_total_tokens: int = 60000


@dataclass
class Turn:
    n: int
    sub_question: str
    tool: str
    query_issued: str
    new_chunk_ids: list
    all_chunk_ids: list
    sufficient: bool
    missing: list
    stop_reason: str = ""
    elapsed_ms: float = 0.0


@dataclass
class AgentResult:
    question: str
    sub_questions: list
    turns: list
    working_evidence: list          # Hit objects, in discovery order
    final_context_ids: list
    answer: str
    citations: list
    stop_reason: str
    usage: dict = field(default_factory=dict)

    @property
    def turn_count(self):
        return len(self.turns)


# ------------------------------------------------------------ decomposition --
def decompose(question, max_parts=3):
    """Split a question into sub-questions with a dependency order.

    Offline and rule-based: it splits on conjunctions and on relative clauses
    ("the company that acquired X"), which covers the shapes in this corpus.
    Pass `llm=` a generator to do it with a model instead -- the loop does not
    care which produced the list, and `decomposition_quality()` scores either.
    """
    q = question.strip().rstrip("?")
    parts = []
    m = re.search(r"(.*?)\bthat\b(.*)", q, re.I)
    if m and len(m.group(2).split()) > 2:
        # inner clause first: it names the entity the outer clause depends on
        parts.append("Which entity " + m.group(2).strip() + "?")
        parts.append(m.group(1).strip() + " (of that entity)?")
    for seg in re.split(r"\band\b|,\s*and\b|;", q):
        seg = seg.strip()
        if len(seg.split()) >= 3 and seg not in parts:
            parts.append(seg + "?")
    parts = [p for p in dict.fromkeys(parts) if p][:max_parts]
    return parts or [question]


def choose_tool(sub_question, available=("lexical", "dense", "hybrid", "grep")):
    """Pick a retrieval tool from the shape of the sub-question.

    Identifiers and error codes go lexical -- an embedding will find related
    incidents and slide right past ERR_CONN_RESET. Conceptual phrasing goes
    dense. Everything else goes hybrid, which is the honest default.
    """
    if ID_RX.search(sub_question):
        return "lexical" if "lexical" in available else "hybrid"
    if re.search(r"\b(file|path|function|class|def |import )\b", sub_question):
        return "grep" if "grep" in available else "lexical"
    if re.search(r"\b(why|how|approach|strategy|concept|mean|difference)\b", sub_question, re.I):
        return "dense" if "dense" in available else "hybrid"
    return "hybrid"


def sufficiency_check(sub_questions, evidence_hits, threshold=0.34):
    """Does the working evidence answer every sub-question?

    Cheap, separate, and schema-constrained: it returns a boolean and the list
    of sub-questions still unsupported. That list is what the next turn
    searches for -- which is also what stops the agent drifting off the
    original question by turn four.
    """
    texts = [h.text for h in evidence_hits]
    missing = []
    for sq in sub_questions:
        qt = [t for t in dict.fromkeys(tokenize(sq))]
        if not qt:
            continue
        best = 0.0
        for t in texts:
            tt = set(tokenize(t))
            best = max(best, sum(1 for x in qt if x in tt) / len(qt))
        if best < threshold:
            missing.append(sq)
    return {"sufficient": not missing, "missing": missing,
            "covered": len(sub_questions) - len(missing), "total": len(sub_questions)}


# -------------------------------------------------------------------- loop ---
class AgenticSearch:
    def __init__(self, pipeline, budget: AgentBudget = None, escalate_only=False,
                 sufficiency_threshold=0.34):
        self.p = pipeline
        self.budget = budget or AgentBudget()
        self.escalate_only = escalate_only
        self.sufficiency_threshold = sufficiency_threshold

    def _retrieve(self, query, tool, cfg):
        from dataclasses import replace

        fusion = {"lexical": "lexical", "dense": "dense", "hybrid": "rrf"}.get(tool, "rrf")
        c = replace(cfg, fusion=fusion)
        hits = self.p.retriever.search(query, c)
        return self.p.reranker.rerank(query, hits, depth=c.rerank_depth)[: c.k]

    def run(self, question, acl_groups=None, verbose=False):
        from dataclasses import replace

        t_start = time.perf_counter()
        cfg = self.p.cfg
        if acl_groups is not None:
            cfg = replace(cfg, acl_groups=tuple(acl_groups))

        subs = decompose(question)
        working, seen_ids, issued = [], set(), set()
        turns, stop_reason = [], ""
        pending = [question] + [s for s in subs if s != question]

        for n in range(1, self.budget.max_turns + 1):
            t0 = time.perf_counter()
            target = pending[0] if pending else question
            # Re-anchor every turn: the original question is always in the query.
            query = target if n == 1 else f"{question} {target}"
            norm = " ".join(sorted(set(tokenize(query))))
            if norm in issued:
                stop_reason = "repeat detector: this query was already issued"
                break
            issued.add(norm)

            tool = choose_tool(target)
            hits = self._retrieve(query, tool, cfg)
            new = [h for h in hits if h.chunk_id not in seen_ids]
            for h in new:
                seen_ids.add(h.chunk_id)
                working.append(h)

            suff = sufficiency_check(subs, working, self.sufficiency_threshold)
            turn = Turn(n, target, tool, query, [h.chunk_id for h in new],
                        [h.chunk_id for h in working], suff["sufficient"], suff["missing"],
                        elapsed_ms=(time.perf_counter() - t0) * 1000)
            turns.append(turn)
            if verbose:
                print(f"  turn {n}: tool={tool:<8} new={len(new):<2} "
                      f"covered={suff['covered']}/{suff['total']}  «{target[:52]}»")

            if suff["sufficient"]:
                stop_reason = "sufficiency satisfied"
                break
            if not new:
                stop_reason = "no new information on the last turn"
                break
            if self.escalate_only and n == 1:
                stop_reason = "single-shot only (escalation disabled)"
                break
            if (time.perf_counter() - t_start) > self.budget.wall_clock_s:
                stop_reason = "wall-clock deadline"
                break
            pending = suff["missing"] or [question]
        else:
            stop_reason = f"turn cap ({self.budget.max_turns})"

        # Evidence retention: what survived from working evidence into the context.
        from .retrieve import pack_context

        selected, used = pack_context(working, k=cfg.k,
                                      token_cap=min(cfg.evidence_token_cap,
                                                    self.budget.max_evidence_tokens),
                                      dedup=cfg.dedup, order=cfg.order)
        packed = build_prompt(question, selected, k=cfg.k,
                              token_cap=self.budget.max_evidence_tokens)
        ans = self.p.generator.generate(question, packed)

        text = ans.text
        if "sufficiency satisfied" not in stop_reason and not ans.abstained:
            gap = (", ".join(turns[-1].missing[:2])
                   if turns and turns[-1].missing else "part of the question")
            text = (f"{text}\n\nPARTIAL: the loop stopped because {stop_reason}. "
                    f"Unconfirmed: {gap}.")

        return AgentResult(question, subs, turns, working, [b["chunk_id"] for b in packed.blocks],
                           text, ans.citations, stop_reason,
                           {"turns": len(turns), "evidence_tokens": used, **ans.usage})


# --------------------------------------------------------- trace evaluation --
def score_trace(result: AgentResult, gold_map, min_turns=None):
    """Score the search trace, not just the answer.

    Answer-only scoring cannot tell a lucky agent from a good one. Evidence
    retention is the row almost nobody instruments, and it is where multi-turn
    systems quietly lose to single-shot ones: you found the gold chunk on turn
    two and then threw it away while packing.
    """
    gold_items = list(gold_map.values())
    all_ids = {cid for h in result.working_evidence for cid in [h.chunk_id]}
    final_ids = set(result.final_context_ids)

    n_gold = len(gold_items)
    cumulative = (sum(1 for g in gold_items if g & all_ids) / n_gold) if n_gold else None
    retained = (sum(1 for g in gold_items if g & final_ids) / n_gold) if n_gold else None
    found_then_lost = [i for i, g in enumerate(gold_items)
                       if (g & all_ids) and not (g & final_ids)]

    covered_subs = sum(1 for sq in result.sub_questions
                       if any(set(tokenize(sq)) & set(tokenize(h.text))
                              for h in result.working_evidence))
    decomposition = covered_subs / max(1, len(result.sub_questions))
    min_turns = min_turns or max(1, len(gold_items))
    efficiency = min_turns / max(1, result.turn_count)

    return {
        "decomposition_quality": round(decomposition, 3),
        "turns": result.turn_count,
        "turn_efficiency": round(min(1.0, efficiency), 3),
        "cumulative_evidence_recall": None if cumulative is None else round(cumulative, 3),
        "evidence_retention": None if retained is None else round(retained, 3),
        "found_then_lost": len(found_then_lost),
        "stop_reason": result.stop_reason,
        "stopped_well": result.stop_reason == "sufficiency satisfied",
    }


TRACE_PROPERTIES = [
    ("Decomposition quality", "Do the sub-questions cover every gold evidence item?",
     "The plan was wrong; no amount of retrieval will rescue it"),
    ("Tool selection accuracy", "Fraction of turns using the tool an expert would have used",
     "Tool descriptions are ambiguous, or there are too many tools"),
    ("Turn efficiency", "Turns taken ÷ minimum turns needed for full evidence",
     "Cost is being burned on redundant search"),
    ("Cumulative evidence recall", "Gold evidence found anywhere in the trace",
     "The loop never reached the second hop"),
    ("Evidence retention", "Gold found early that survived into the final context",
     "You found it and then threw it away — the worst, most invisible failure"),
    ("Stop-decision quality", "Precision/recall of the sufficiency check vs human judgment",
     "Either premature confidence, or loops that never terminate"),
]
