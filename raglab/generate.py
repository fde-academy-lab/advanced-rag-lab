"""
Generators: turning packed evidence into a cited answer.

The default generator runs offline and is *extractive*. Given a question and a
packed evidence block it selects the supporting sentences and emits them with
their [S#] citations, or returns INSUFFICIENT_EVIDENCE when nothing clears the
support threshold. That makes it faithful by construction, which is a feature
and a limitation worth stating plainly:

  * Feature -- the retrieval half of the curriculum can be measured without an
    LLM in the loop adding its own variance to every number.
  * Limitation -- it cannot hallucinate, so it cannot demonstrate a grounding
    failure. `UngroundedGenerator` exists for that: a deliberate fault-injection
    device that answers from the question's own priors and ignores evidence.
    Nothing about it is a claim about how real models behave; it is a fixture
    that gives the judge and the faithfulness metric something real to catch.

Point `BedrockGenerator` or `AnthropicGenerator` at the same interface and
every measurement in these notebooks keeps working against a real model.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .context import ABSTAIN_TOKEN, PackedContext
from .embed import tokenize

SENT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Answer:
    text: str
    citations: list = field(default_factory=list)
    sufficient: bool = True
    raw: str = ""
    usage: dict = field(default_factory=dict)
    model: str = "extractive-offline"

    @property
    def abstained(self):
        return not self.sufficient or ABSTAIN_TOKEN in self.text


class BaseGenerator:
    name = "base"

    def generate(self, question, packed: PackedContext, **kw) -> Answer:
        raise NotImplementedError


class ExtractiveGenerator(BaseGenerator):
    """Selects the best-supported sentences from EVIDENCE and cites them.

    Scoring is deliberately simple and deliberately explicit, because every
    ingredient is a decision a real generation prompt also makes:

      * coverage is IDF-weighted over the packed blocks, so a rare query term
        like a company name counts for more than "the company". Unweighted
        overlap is how an extractive reader ends up quoting a funding round in
        answer to a question about a chief executive -- both sentences share
        the entity name, only one shares the rare term that matters.
      * the retrieval rank is a prior, not a tiebreak. Stage two already spent
        compute deciding block 1 was better than block 6; throwing that away at
        read time is a waste of the reranker you just paid for.
      * numbers only help when the question asks for one.

    `support_threshold` is the abstention contract in numeric form: below it,
    the generator returns the exact abstention token rather than a plausible
    sentence. A fixed string is parseable; "I'm not sure" is not.
    """

    name = "extractive-offline"

    QUANTITY = re.compile(r"\b(how much|how many|revenue|growth|price|rate|percentage|"
                          r"consideration|paid|cost|amount|sales|top line)\b", re.I)

    def __init__(self, support_threshold=0.15, max_sentences=2, rank_prior=0.14,
                 min_evidence_score=None):
        self.support_threshold = support_threshold
        self.max_sentences = max_sentences
        self.rank_prior = rank_prior
        # An explicit retrieval-score gate, off by default. Off is the honest
        # baseline: a system with no threshold never abstains, which is exactly
        # the failure the deck's null questions are designed to expose.
        # Notebook 06 turns it on and justifies the value with a
        # precision/recall curve instead of a hunch.
        self.min_evidence_score = min_evidence_score

    def _idf(self, blocks):
        import math

        n = max(1, len(blocks))
        df = {}
        for b in blocks:
            for t in set(tokenize(b["text"])):
                df[t] = df.get(t, 0) + 1
        return {t: math.log((1 + n) / (1 + d)) + 1.0 for t, d in df.items()}, n

    def generate(self, question, packed: PackedContext, **kw) -> Answer:
        qtok = [t for t in dict.fromkeys(tokenize(question))]
        if self.min_evidence_score is not None:
            top = max((b["score"] for b in packed.blocks), default=0.0)
            if not packed.blocks or top < self.min_evidence_score:
                return Answer(ABSTAIN_TOKEN, [], False, ABSTAIN_TOKEN,
                              {"input_tokens": packed.total_tokens, "output_tokens": 6},
                              self.name)
        wants_number = bool(self.QUANTITY.search(question))
        idf, _ = self._idf(packed.blocks)
        qw = {t: idf.get(t, 1.6) for t in qtok}          # unseen query term = rare
        total_w = sum(qw.values()) or 1.0

        scored = []
        for bi, b in enumerate(packed.blocks):
            prior = self.rank_prior / (1 + bi)
            for s in SENT.split(b["text"]):
                s = s.strip()
                if len(s) < 20:
                    continue
                stok = set(tokenize(s))
                cov = sum(w for t, w in qw.items() if t in stok) / total_w
                bonus = 0.10 if (wants_number and re.search(r"\d", s)) else 0.0
                scored.append((cov + prior + bonus, cov, s, b["sid"]))
        scored.sort(key=lambda t: -t[0])
        best = [x for x in scored if x[1] >= self.support_threshold][: self.max_sentences]
        if not best:
            return Answer(ABSTAIN_TOKEN, [], False, ABSTAIN_TOKEN,
                          {"input_tokens": packed.total_tokens, "output_tokens": 6}, self.name)
        seen, parts, cites = set(), [], []
        for _, _, sent, sid in best:
            if sent in seen:
                continue
            seen.add(sent)
            parts.append(f"{sent} [{sid}]")
            if sid not in cites:
                cites.append(sid)
        text = " ".join(parts)
        return Answer(text, cites, True, text,
                      {"input_tokens": packed.total_tokens,
                       "output_tokens": max(8, len(text) // 4)}, self.name)


class UngroundedGenerator(BaseGenerator):
    """A fault-injection fixture: answers confidently, ignores the evidence.

    Used only to prove that the faithfulness metric and the judge catch what
    they claim to catch. Never enable this outside a demonstration.
    """

    name = "ungrounded-fixture"

    def __init__(self, priors=None):
        self.priors = priors or {}

    def generate(self, question, packed: PackedContext, **kw) -> Answer:
        for key, val in self.priors.items():
            if key.lower() in question.lower():
                return Answer(f"{val} [S1]", ["S1"], True, val,
                              {"input_tokens": packed.total_tokens, "output_tokens": 24}, self.name)
        subject = " ".join(question.split()[1:6]).rstrip("?")
        return Answer(
            f"Based on the available information, {subject} is confirmed by the sources. [S1]",
            ["S1"], True, "", {"input_tokens": packed.total_tokens, "output_tokens": 24}, self.name)


def _parse_model_json(raw):
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"answer": raw.strip(), "citations": re.findall(r"\[(S\d+)\]", raw),
                "sufficient": ABSTAIN_TOKEN not in raw}
    try:
        d = json.loads(m.group(0))
    except Exception:
        return {"answer": raw.strip(), "citations": re.findall(r"\[(S\d+)\]", raw),
                "sufficient": ABSTAIN_TOKEN not in raw}
    return {"answer": str(d.get("answer", "")), "citations": list(d.get("citations", [])),
            "sufficient": bool(d.get("sufficient", True))}


class BedrockGenerator(BaseGenerator):
    """Amazon Bedrock Converse API.

        gen = BedrockGenerator(model_id="anthropic.claude-sonnet-4-5-20250929-v1:0",
                               region="us-east-1")

    Credentials come from the standard boto3 chain. Usage counters are returned
    so the cost notebook can bill a real call the same way it bills a modelled one.
    """

    name = "bedrock"

    def __init__(self, model_id="anthropic.claude-sonnet-4-5-20250929-v1:0", region=None,
                 client=None, temperature=0.0, max_tokens=600):
        import boto3

        self.model_id = model_id
        self.client = client or boto3.client("bedrock-runtime", region_name=region)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, question, packed: PackedContext, system=None, **kw) -> Answer:
        resp = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": packed.prompt}]}],
            inferenceConfig={"temperature": self.temperature, "maxTokens": self.max_tokens},
        )
        raw = resp["output"]["message"]["content"][0]["text"]
        parsed = _parse_model_json(raw)
        u = resp.get("usage", {})
        return Answer(parsed["answer"], parsed["citations"], parsed["sufficient"], raw,
                      {"input_tokens": u.get("inputTokens"), "output_tokens": u.get("outputTokens"),
                       "cache_read_input_tokens": u.get("cacheReadInputTokens"),
                       "cache_write_input_tokens": u.get("cacheWriteInputTokens")},
                      self.model_id)


class AnthropicGenerator(BaseGenerator):
    """The Claude API directly, with prompt caching on the stable prefix."""

    name = "anthropic"

    def __init__(self, model="claude-sonnet-4-5", api_key=None, max_tokens=600, cache_prefix=True):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.cache_prefix = cache_prefix

    def generate(self, question, packed: PackedContext, system=None, **kw) -> Answer:
        head, _, tail = packed.prompt.partition("EVIDENCE\n")
        sys_blocks = [{"type": "text", "text": head}]
        if self.cache_prefix:
            sys_blocks[0]["cache_control"] = {"type": "ephemeral"}
        msg = self.client.messages.create(
            model=self.model, max_tokens=self.max_tokens, system=sys_blocks,
            messages=[{"role": "user", "content": "EVIDENCE\n" + tail}])
        raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
        parsed = _parse_model_json(raw)
        u = msg.usage
        return Answer(parsed["answer"], parsed["citations"], parsed["sufficient"], raw,
                      {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
                       "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0),
                       "cache_write_input_tokens": getattr(u, "cache_creation_input_tokens", 0)},
                      self.model)
