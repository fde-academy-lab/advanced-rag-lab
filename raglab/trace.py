"""
Traces: the record that makes a failure reproducible.

The deck's query-time slide ends with one requirement people skip in
interviews and regret in production -- record the retrieved items, their
scores, the selected context, the model response and the latency, so a failure
can be replayed. Everything downstream depends on it: you cannot debug what you
did not log, you cannot build an eval set from production failures you cannot
reconstruct, and you cannot diff two runs of the same query to find out what
your change actually did.

The trace store is another in-memory SQLite database, which makes traces
queryable -- "show me every query where the gold chunk was retrieved and then
dropped during packing" is a SQL statement, not a grep.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass, field

TRACE_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    trace_id      TEXT PRIMARY KEY,
    qid           TEXT,
    query         TEXT,
    config        TEXT,
    stage_ms      TEXT,
    candidates    TEXT,
    reranked      TEXT,
    packed        TEXT,
    answer        TEXT,
    citations     TEXT,
    usage         TEXT,
    metrics       TEXT,
    persona       TEXT,
    k_collapse    INTEGER,
    index_version TEXT,
    created_at    REAL
);
"""


@dataclass
class Trace:
    trace_id: str
    qid: str = ""
    query: str = ""
    config: dict = field(default_factory=dict)
    stage_ms: dict = field(default_factory=dict)
    candidates: list = field(default_factory=list)   # [{chunk_id, score, rank, method}]
    reranked: list = field(default_factory=list)
    packed: list = field(default_factory=list)       # [{sid, chunk_id, tokens}]
    answer: str = ""
    citations: list = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    persona: str = ""
    index_version: str = "v1"
    k_collapse: int = 0
    created_at: float = field(default_factory=time.time)

    @property
    def packed_ids(self):
        return [b["chunk_id"] for b in self.packed]

    @property
    def candidate_ids(self):
        return [c["chunk_id"] for c in self.candidates]

    def summary(self):
        return {
            "trace_id": self.trace_id, "qid": self.qid,
            "N": len(self.candidates), "k": len(self.packed),
            "evidence_tokens": sum(b.get("tokens", 0) for b in self.packed),
            "latency_ms": round(sum(self.stage_ms.values()), 1),
            "answer": (self.answer[:70] + "…") if len(self.answer) > 70 else self.answer,
        }


class TraceStore:
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(TRACE_SCHEMA)

    def put(self, t: Trace):
        self.db.execute(
            "INSERT OR REPLACE INTO traces VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (t.trace_id, t.qid, t.query, json.dumps(t.config, default=str),
             json.dumps(t.stage_ms), json.dumps(t.candidates), json.dumps(t.reranked),
             json.dumps(t.packed), t.answer, json.dumps(t.citations), json.dumps(t.usage),
             json.dumps(t.metrics), t.persona, t.k_collapse, t.index_version,
             t.created_at))
        self.db.commit()
        return t.trace_id

    def get(self, trace_id):
        r = self.db.execute("SELECT * FROM traces WHERE trace_id=?", (trace_id,)).fetchone()
        if not r:
            return None
        d = dict(r)
        for k in ("config", "stage_ms", "candidates", "reranked", "packed", "citations",
                  "usage", "metrics"):
            d[k] = json.loads(d[k] or "null")
        return Trace(**d)

    def query(self, sql, params=()):
        import pandas as pd

        return pd.read_sql_query(sql, self.db, params=params)

    def count(self):
        return self.db.execute("SELECT COUNT(*) FROM traces").fetchone()[0]


def diff_traces(a: Trace, b: Trace):
    """What changed between two runs of the same question.

    The 'exceeds the bar' line in the build rubric is exactly this: traces that
    are diffable between two runs of the same query. Retrieved-then-dropped is
    the row people are always surprised by.
    """
    ca, cb = set(a.candidate_ids), set(b.candidate_ids)
    pa, pb = set(a.packed_ids), set(b.packed_ids)
    return {
        "query": a.query,
        "candidates_only_in_a": sorted(ca - cb),
        "candidates_only_in_b": sorted(cb - ca),
        "packed_only_in_a": sorted(pa - pb),
        "packed_only_in_b": sorted(pb - pa),
        "retrieved_then_dropped_a": sorted(ca - pa),
        "retrieved_then_dropped_b": sorted(cb - pb),
        "rank_moves": {
            cid: (next((c["rank"] for c in a.candidates if c["chunk_id"] == cid), None),
                  next((c["rank"] for c in b.candidates if c["chunk_id"] == cid), None))
            for cid in sorted(ca & cb)
        },
        "answer_a": a.answer, "answer_b": b.answer,
        "latency_delta_ms": round(sum(b.stage_ms.values()) - sum(a.stage_ms.values()), 1),
    }
