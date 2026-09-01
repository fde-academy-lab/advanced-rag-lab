"""
LLM-as-a-judge, and the calibration that makes its verdict admissible.

An uncalibrated judge is an opinion with a number attached. The loop the deck
prescribes is implemented here: write the rubric as a decision procedure rather
than an adjective, label a calibration set by hand, score agreement with
Cohen's kappa rather than raw accuracy, and pin every artefact -- judge model,
temperature, rubric text, exemplars -- as a release object.

The offline judge is heuristic and deterministic. It checks span-level support
rather than making a holistic call, which is the same discipline you want from
a model judge and happens to be the one thing a heuristic can do honestly. The
bias probes below then attack *it* the same way you should attack a real one.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .embed import tokenize

SENT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Rubric:
    """A rubric is a release artefact. Version it or you cannot explain a jump."""

    name: str
    criterion: str            # written as a procedure, not an adjective
    scale: tuple = ("fail", "pass")
    version: str = "1.0"
    exemplars: tuple = ()

    @property
    def fingerprint(self):
        blob = f"{self.name}|{self.criterion}|{self.scale}|{self.version}|{self.exemplars}"
        return hashlib.sha1(blob.encode()).hexdigest()[:10]


FAITHFULNESS = Rubric(
    "faithfulness",
    "For each factual claim in the answer, find a span in a cited evidence block that "
    "entails it. PASS only if every claim maps to such a span. A claim that is true in "
    "general but absent from the evidence is a FAIL.",
    version="1.2")

COMPLETENESS = Rubric(
    "completeness",
    "List the sub-questions the question contains. PASS only if the answer resolves every "
    "one of them. A two-part question answered halfway is a FAIL, even if the half is right.",
    version="1.1")

CITATION = Rubric(
    "citation_accuracy",
    "Every [S#] in the answer must resolve to a packed evidence block, and that block must "
    "contain support for the claim it is attached to. An unresolvable ID and a resolvable ID "
    "on an unsupported claim are both FAIL, and they are different bugs.",
    version="1.0")


@dataclass
class Verdict:
    rubric: str
    label: str
    score: float
    reasons: list = field(default_factory=list)
    judge: str = "heuristic-offline"
    rubric_version: str = ""

    @property
    def passed(self):
        return self.label == "pass"


class HeuristicJudge:
    """Deterministic, span-level, offline. No model, no drift, no cost.

    It is weaker than a good model judge on nuance and stronger on consistency.
    Use it here to learn the calibration loop; swap in BedrockJudge to run the
    same loop against the thing you would actually ship.
    """

    name = "heuristic-offline"

    def __init__(self, support_threshold=0.5):
        self.support_threshold = support_threshold

    def _claims(self, answer):
        stripped = re.sub(r"\[S\d+\]", "", answer)
        return [s.strip() for s in SENT.split(stripped) if len(s.strip()) > 12]

    def _supported(self, claim, evidence_texts):
        ct = [t for t in dict.fromkeys(tokenize(claim))]
        if not ct:
            return True, 1.0
        best = 0.0
        for ev in evidence_texts:
            et = set(tokenize(ev))
            best = max(best, sum(1 for t in ct if t in et) / len(ct))
        return best >= self.support_threshold, best

    def faithfulness(self, answer, packed):
        texts = [b["text"] for b in packed.blocks]
        claims = self._claims(answer)
        if not claims:
            return Verdict(FAITHFULNESS.name, "pass", 1.0, ["no factual claim to check"],
                           self.name, FAITHFULNESS.version)
        bad = []
        for c in claims:
            ok, sc = self._supported(c, texts)
            if not ok:
                bad.append(f"unsupported ({sc:.2f}): {c[:70]}")
        score = 1 - len(bad) / len(claims)
        return Verdict(FAITHFULNESS.name, "pass" if not bad else "fail", score,
                       bad or ["every claim maps to a cited span"], self.name,
                       FAITHFULNESS.version)

    def completeness(self, answer, question, gold_answer=None):
        parts = [p for p in re.split(r"\band\b|,|;", question) if len(p.strip()) > 8]
        atok = set(tokenize(answer))
        missing = []
        for p in parts:
            keys = [t for t in tokenize(p) if len(t) > 3][:6]
            if keys and sum(1 for t in keys if t in atok) / len(keys) < 0.25:
                missing.append(p.strip()[:60])
        score = 1 - len(missing) / max(1, len(parts))
        return Verdict(COMPLETENESS.name, "pass" if not missing else "fail", score,
                       missing or ["all parts addressed"], self.name, COMPLETENESS.version)

    def citation_accuracy(self, answer, packed):
        sids = re.findall(r"\[(S\d+)\]", answer)
        if not sids:
            return Verdict(CITATION.name, "fail", 0.0, ["no citations emitted"], self.name,
                           CITATION.version)
        unresolved = [s for s in sids if not packed.resolve(s)]
        by_sid = {b["sid"]: b["text"] for b in packed.blocks}
        weak = []
        for chunk in re.split(r"(?=\[S\d+\])", answer):
            m = re.search(r"\[(S\d+)\]", chunk)
            if not m:
                continue
            claim = re.sub(r"\[S\d+\]", "", chunk)
            ok, sc = self._supported(claim, [by_sid.get(m.group(1), "")])
            if not ok:
                weak.append(f"{m.group(1)} does not support its claim ({sc:.2f})")
        bad = [f"unresolvable: {s}" for s in unresolved] + weak
        score = 1 - len(bad) / max(1, len(sids))
        return Verdict(CITATION.name, "pass" if not bad else "fail", score,
                       bad or ["all citations resolve and support their claims"], self.name,
                       CITATION.version)

    def judge_all(self, question, answer, packed, gold_answer=None):
        return {
            "faithfulness": self.faithfulness(answer, packed),
            "completeness": self.completeness(answer, question, gold_answer),
            "citation_accuracy": self.citation_accuracy(answer, packed),
        }


JUDGE_PROMPT = """You are grading one answer against one rubric. Follow the rubric as a
procedure. Do not reward fluency, length, or confidence.

RUBRIC ({name} v{version})
{criterion}

QUESTION
{question}

EVIDENCE SHOWN TO THE ANSWERING MODEL
{evidence}

ANSWER
{answer}

Return JSON only: {{"label": "pass"|"fail", "reasons": [str]}}"""


class BedrockJudge:
    """The same rubrics, evaluated by a model on Bedrock.

    Use a different model family from the generator where you can -- judges
    favour output from their own family, and self-preference is the one bias
    you cannot prompt your way out of.
    """

    name = "bedrock-judge"

    def __init__(self, model_id="anthropic.claude-sonnet-4-5-20250929-v1:0", region=None,
                 client=None, temperature=0.0):
        import boto3

        self.model_id = model_id
        self.client = client or boto3.client("bedrock-runtime", region_name=region)
        self.temperature = temperature

    def _ask(self, rubric, question, answer, packed):
        import json

        evidence = "\n\n".join(b["rendered"] for b in packed.blocks) or "(none)"
        prompt = JUDGE_PROMPT.format(name=rubric.name, version=rubric.version,
                                     criterion=rubric.criterion, question=question,
                                     evidence=evidence, answer=answer)
        resp = self.client.converse(
            modelId=self.model_id,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"temperature": self.temperature, "maxTokens": 400})
        raw = resp["output"]["message"]["content"][0]["text"]
        m = re.search(r"\{.*\}", raw, re.S)
        d = json.loads(m.group(0)) if m else {"label": "fail", "reasons": ["unparseable"]}
        return Verdict(rubric.name, d.get("label", "fail"),
                       1.0 if d.get("label") == "pass" else 0.0,
                       list(d.get("reasons", [])), f"{self.name}:{self.model_id}", rubric.version)

    def judge_all(self, question, answer, packed, gold_answer=None):
        return {r.name: self._ask(r, question, answer, packed)
                for r in (FAITHFULNESS, COMPLETENESS, CITATION)}


# ------------------------------------------------------------ calibration ----
def calibration_report(judge_labels, human_labels, rubric=None):
    from .metrics import agreement_report

    rep = agreement_report(judge_labels, human_labels)
    rep["rubric"] = rubric.name if rubric else ""
    rep["rubric_version"] = rubric.version if rubric else ""
    rep["rubric_fingerprint"] = rubric.fingerprint if rubric else ""
    rep["usable"] = rep["cohens_kappa"] >= 0.6
    rep["note"] = ("Kappa clears the bar for relative comparisons."
                   if rep["usable"] else
                   "Kappa below 0.6 — fix the rubric before trusting any delta it reports.")
    return rep


def verbosity_probe(judge, question, packed, short_answer, padded_answer):
    """Feed the same claim twice, once padded. A verdict that moves is bias.

    The padding adds no information and no support. If a judge upgrades the
    padded version it is scoring length, and every quality delta it has ever
    reported for you is partly a length delta.
    """
    a = judge.judge_all(question, short_answer, packed)
    b = judge.judge_all(question, padded_answer, packed)
    moved = {k: (a[k].label, b[k].label) for k in a if a[k].label != b[k].label}
    return {"stable": not moved, "moved": moved,
            "verdict": "no verbosity bias detected" if not moved
                       else "verbosity bias: padding changed the verdict"}


def position_probe(judge, question, packed_a, packed_b, answer):
    """Same evidence, different order. A judge whose verdict moves has position
    bias, and in pairwise mode you must swap A and B and require agreement."""
    a = judge.judge_all(question, answer, packed_a)
    b = judge.judge_all(question, answer, packed_b)
    moved = {k: (a[k].label, b[k].label) for k in a if a[k].label != b[k].label}
    return {"stable": not moved, "moved": moved,
            "verdict": "order-invariant" if not moved else "position sensitive"}


JUDGE_BIASES = [
    ("Position bias", "In pairwise comparison the first option wins more often",
     "Swap A and B; require the verdict to hold in both orders"),
    ("Verbosity bias", "Longer answers score higher regardless of support",
     "Cap length, or normalise for it, and run a padding probe"),
    ("Self-preference", "A judge favours output from its own model family",
     "Use a different family from the generator where you can"),
    ("Scale compression", "A 1–10 scale collapses to 7s and 8s",
     "Prefer binary or three-point rubrics with explicit criteria"),
    ("Leniency on grounding", "Judges accept plausible unsupported claims",
     "Force span-level citation checking, not a holistic judgment"),
]
