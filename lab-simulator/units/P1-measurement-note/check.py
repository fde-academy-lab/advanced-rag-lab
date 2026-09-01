#!/usr/bin/env python3
"""Checks for P1 · Write the measurement note that survives you leaving.

Most write-up graders check structure. This one re-runs the measurement and checks that the
numbers in the note are the numbers the code produces, because structure was never the problem:
the finding this repository had to retract was well-structured, prominently placed, and wrong,
and what let it survive was that nobody could cheaply re-run it.

So the expensive check is the point. It costs about eight seconds and it is the only check here
that could not be satisfied by a careful writer who never ran anything.
"""
from __future__ import annotations

import datetime as dt
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(ROOT))
from labsim.checkkit import Checker, SolutionError, emit, run  # noqa: E402

TOL = 0.0015
NUMBER = re.compile(r"-?\d\.\d{2,6}|-?0?\.\d{2,6}")
DATE = re.compile(r"\b(20\d{2})-([01]\d)-([0-3]\d)\b")
# A bracketed pair of signed decimals: (+0.0048, +0.0254) or [-0.0101, +0.0109]
INTERVAL = re.compile(r"[\[(]\s*[-+−]?\d*\.\d+\s*,\s*[-+−]?\d*\.\d+\s*[\])]")
COMMAND = re.compile(r"`([^`\n]{6,160})`|^\s{0,3}([a-z][^\n]{6,160})$", re.M)

MECHANISM = {
    "the failure sets are nested, not overlapping":
        r"nest|overlap|subset|contain|same quest|fail together|correlat|disjoint",
    "what fusion would have needed in order to pay":
        r"complement|different quest|rescue|reach.{0,20}miss|orthogonal|adds? little"
        r"|nothing (left )?to add",
}
CONDITION = re.compile(
    r"\bwould (flip|change|reverse|no longer)|\bif the\b|\bonce the\b|\buntil\b|\bwhen the\b"
    r"|does not (say|hold|generalise|generalize)|only (holds|applies)|conditional on", re.I)


def sections(text: str) -> dict[str, str]:
    out, current = {}, "_preamble"
    buf: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            out[current] = "\n".join(buf)
            current, buf = line.lstrip("# ").strip().lower(), []
        else:
            buf.append(line)
    out[current] = "\n".join(buf)
    return out


def truth() -> dict[str, float]:
    """Re-run R3's measurement. The numbers in the note have to be these."""
    from raglab import chunking, corpus, embed, metrics, retrieve, store

    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy="structural")
    emb = embed.LsaEmbedder(dim=96).fit([d.title + "\n" + d.body for d in bundle.documents])
    index = store.InMemoryIndex()
    index.upsert(chunks, emb.encode_documents([c.text for c in chunks]),
                 index_version="v1", embedder_tag=emb.info.tag)
    index.set_alias("live", "v1")
    cfg = retrieve.RetrievalConfig(n_candidates=100, k=8, fusion="rrf")
    lexical, dense = retrieve.LexicalRetriever(index), retrieve.DenseRetriever(index, emb)
    reranker = retrieve.make_reranker("cross", emb)

    recalls, dmiss, lmiss = [], set(), set()
    for q in bundle.questions:
        gold = metrics.resolve_gold(q, chunks)[0]
        if not gold:
            continue
        d_leg = dense.search(q.query, 100, cfg)
        l_leg = lexical.search(q.query, 100, cfg)
        fused = retrieve.rrf([d_leg, l_leg], k=60)[:100]
        recalls.append(metrics.evidence_recall_at_k(
            [h.chunk_id for h in reranker.rerank(q.query, fused)[:8]], gold))
        for legs, misses in ((d_leg, dmiss), (l_leg, lmiss)):
            ids = [h.chunk_id for h in reranker.rerank(q.query, legs[:100])[:8]]
            if metrics.evidence_recall_at_k(ids, gold) < 1.0:
                misses.add(q.qid)
    return {"evidence_recall": statistics.mean(recalls),
            "failure_overlap": len(dmiss & lmiss) / len(dmiss)}


def main(attempt: str) -> int:
    path = Path(attempt) / "measurement.md"
    if not path.exists():
        raise SolutionError("No measurement.md. Run `labsim start P1` and write it.")
    text = path.read_text()
    body = sections(text)
    c = Checker()

    if not c("the note has content", len(text.split()) >= 180,
             f"{len(text.split())} words. A note nobody can act on is not shorter, it is absent"):
        return emit({}, c)
    c("no template placeholders left in", "<" not in re.sub(r"<br\s*/?>", "", text),
      "angle-bracket placeholders from the template are still present")

    # ---------------------------------------------------------------- header
    found = DATE.search(text)
    c("carries a date", bool(found),
      "a measurement without a date cannot be known to be stale, which is the only way "
      "measurements go wrong quietly")
    if found:
        try:
            when = dt.date(*(int(g) for g in found.groups()))
            c("the date is real and not in the future", when <= dt.date.today(),
              f"{when.isoformat()}")
        except ValueError:
            c("the date is real and not in the future", False, found.group(0))

    commands = [g for m in COMMAND.finditer(text) for g in m.groups() if g]
    runnable = [x for x in commands
                if re.match(r"^(python|pytest|make|bash|sh|\./)\b", x.strip())]
    c("names a command that regenerates the numbers", bool(runnable),
      "one line a reader can paste. `python -m labsim check R3` is the honest answer here")
    if runnable:
        referenced = [x for x in runnable
                      if any(part in x for part in ("labsim", "run_eval", "scripts/"))]
        c("the command points at something in this repository", bool(referenced),
          f"found {runnable[:2]} — none of them name a script or module here")

    # ---------------------------------------------------------------- the numbers
    c.note("Re-running the measurement to compare against your note...")
    real = truth()
    quoted = [float(x) for x in NUMBER.findall(text)]
    for key, value in real.items():
        near = [q for q in quoted if abs(q - value) <= TOL]
        c(f"the note's {key} matches the run", bool(near),
          f"the measurement gives {value:.4f}; the closest number in your note is "
          f"{min(quoted, key=lambda q: abs(q - value)) if quoted else 'none'}. "
          "A write-up that disagrees with its own code is the ADR-0015 failure, exactly")

    # ---------------------------------------------------------------- intervals
    interval_text = "\n".join(v for k, v in body.items() if "interval" in k or "table" in k) or text
    c("quotes an interval, not only means",
      bool(INTERVAL.search(interval_text))
      or bool(re.search(r"noise band|did not compute an interval|no interval", text, re.I)),
      "either give an interval on a difference you quote, or say plainly that you did not "
      "compute one. Implying it is the failure")

    # ---------------------------------------------------------------- mechanism
    prose = text.lower()
    for name, pattern in MECHANISM.items():
        c(f"explains: {name}", bool(re.search(pattern, prose)))

    # ---------------------------------------------------------------- the condition
    tail = "\n".join(v for k, v in body.items()
                     if "not say" in k or "condition" in k or "flip" in k)
    c("names the condition under which the answer flips",
      bool(CONDITION.search(tail or text)),
      "every number here is conditional on this corpus, this encoder and this question mix. "
      "Say what would have to change")

    if c.ok:
        c.note("This note would still be usable by somebody who has never met you. That is the "
               "whole bar, and almost nothing published clears it.")
    return emit({}, c)


if __name__ == "__main__":
    sys.exit(run(main))
