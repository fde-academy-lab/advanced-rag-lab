"""
The retrieval store: SQLite in memory, doing real work.

Everything a production RAG stack keeps -- a lexical index, a vector index, a
chunk store with provenance, metadata and ACLs, versioned indexes with an alias
you can swap -- exists here inside `sqlite3.connect(":memory:")`. Nothing to
install, nothing to run as a service, no state left on disk when the kernel
stops. The point is not that SQLite is what you would ship at 100M chunks; the
point is that every architectural idea in the deck is small enough to hold in
one file, and once you have held it you can argue about the managed version.

What is real here rather than mocked:

  * BM25 comes from SQLite's own FTS5 implementation, over a real inverted index.
  * Vector search is a real navigable-small-world graph with a genuine
    recall/efSearch tradeoff you can measure against exact search.
  * Filtered ANN really does dead-end when the filter is selective, which is
    the failure the deck warns about on the permission-aware retrieval slide.
  * Blue/green index versions with an atomic alias swap, chunk-level upserts
    keyed on doc_id + ordinal + content hash, and tombstones.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks (
    row_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    chunk_id      TEXT NOT NULL,
    index_version TEXT NOT NULL,
    doc_id        TEXT NOT NULL,
    ordinal       INTEGER NOT NULL,
    n_chunks      INTEGER NOT NULL,
    title         TEXT,
    heading       TEXT,
    source        TEXT,
    published     TEXT,
    tenant        TEXT,
    acl           TEXT,           -- json array of groups
    content_hash  TEXT,
    embedder_tag  TEXT,           -- pinned encoder identity, per the deck's rule
    text          TEXT NOT NULL,
    vector        BLOB,
    tombstoned    INTEGER DEFAULT 0,
    UNIQUE(chunk_id, index_version)
);
CREATE INDEX IF NOT EXISTS ix_chunks_ver   ON chunks(index_version, tombstoned);
CREATE INDEX IF NOT EXISTS ix_chunks_doc   ON chunks(index_version, doc_id);
CREATE INDEX IF NOT EXISTS ix_chunks_meta  ON chunks(index_version, source, published);

-- tokenchars '_-' is not a detail. The default unicode61 tokenizer splits
-- ERR_CONN_RESET into err / conn / reset, which appear in every incident
-- report in the corpus -- so the one query lexical retrieval should win
-- outright silently becomes its worst case. Your analyzer decides whether
-- identifiers are searchable at all, and nothing downstream will tell you.
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, title, heading,
    chunk_id UNINDEXED, index_version UNINDEXED,
    tokenize = "unicode61 remove_diacritics 2 tokenchars '_-'"
);

CREATE TABLE IF NOT EXISTS aliases (
    name          TEXT PRIMARY KEY,
    index_version TEXT NOT NULL,
    swapped_at    TEXT
);

CREATE TABLE IF NOT EXISTS index_versions (
    index_version TEXT PRIMARY KEY,
    embedder_tag  TEXT,
    chunker       TEXT,
    created_at    TEXT,
    note          TEXT
);
"""


@dataclass
class Hit:
    chunk_id: str
    score: float
    rank: int
    method: str
    doc_id: str = ""
    text: str = ""
    title: str = ""
    source: str = ""
    published: str = ""
    heading: str = ""
    ordinal: int = 0
    acl: tuple = ()

    def brief(self, n=90):
        return f"[{self.rank:>2}] {self.score:7.4f}  {self.doc_id}#{self.ordinal}  {self.text[:n]}"


class InMemoryIndex:
    """A versioned lexical + vector index living entirely in RAM."""

    def __init__(self, name="rag"):
        self.name = name
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self._cache = {}          # index_version -> {ids, mat, graph}
        self._acl_cache = {}      # (version, acl, filters) -> visible chunk ids
        self.embedder_tag = None

    # ------------------------------------------------------------- writes --
    def create_version(self, index_version, embedder_tag="", chunker="", note=""):
        import datetime as dt

        self.db.execute(
            "INSERT OR REPLACE INTO index_versions VALUES (?,?,?,?,?)",
            (index_version, embedder_tag, chunker, dt.datetime.now().isoformat(timespec="seconds"),
             note))
        self.db.commit()
        return index_version

    def upsert(self, chunks, vectors=None, index_version="v1", embedder_tag=""):
        """Chunk-level upsert keyed on the stable chunk_id.

        Upsert-then-tombstone, never delete-then-insert: an in-flight query that
        already holds a row id keeps reading a consistent row.
        """
        import numpy as np

        rows = []
        for i, c in enumerate(chunks):
            vec = None
            if vectors is not None:
                vec = np.asarray(vectors[i], dtype="float32").tobytes()
            rows.append((c.chunk_id, index_version, c.doc_id, c.ordinal, c.n_chunks, c.title,
                         c.heading, c.source, c.published, c.tenant, json.dumps(list(c.acl)),
                         c.content_hash, embedder_tag, c.text, vec, 0))
        self.db.executemany(
            "INSERT INTO chunks (chunk_id,index_version,doc_id,ordinal,n_chunks,title,heading,"
            "source,published,tenant,acl,content_hash,embedder_tag,text,vector,tombstoned) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(chunk_id,index_version) DO UPDATE SET "
            "text=excluded.text, vector=excluded.vector, tombstoned=0, "
            "content_hash=excluded.content_hash, embedder_tag=excluded.embedder_tag", rows)
        self.db.executemany(
            "INSERT INTO chunks_fts (text,title,heading,chunk_id,index_version) VALUES (?,?,?,?,?)",
            [(c.text, c.title, c.heading, c.chunk_id, index_version) for c in chunks])
        self.db.commit()
        self.embedder_tag = embedder_tag or self.embedder_tag
        self._cache.pop(index_version, None)
        self._acl_cache.clear()
        self.create_version(index_version, embedder_tag, note="")
        return len(rows)

    def tombstone(self, chunk_ids, index_version="v1"):
        """Soft delete. Rows stay filterable until compaction so in-flight
        queries stay consistent -- the deck's soft-delete sweep."""
        self.db.executemany(
            "UPDATE chunks SET tombstoned=1 WHERE chunk_id=? AND index_version=?",
            [(cid, index_version) for cid in chunk_ids])
        self.db.commit()
        self._cache.pop(index_version, None)
        self._acl_cache.clear()
        return len(chunk_ids)

    def compact(self, index_version="v1"):
        cur = self.db.execute(
            "SELECT chunk_id FROM chunks WHERE tombstoned=1 AND index_version=?", (index_version,))
        ids = [r[0] for r in cur.fetchall()]
        self.db.execute("DELETE FROM chunks WHERE tombstoned=1 AND index_version=?",
                        (index_version,))
        self.db.executemany("DELETE FROM chunks_fts WHERE chunk_id=? AND index_version=?",
                            [(i, index_version) for i in ids])
        self.db.commit()
        self._cache.pop(index_version, None)
        self._acl_cache.clear()
        return len(ids)

    def set_alias(self, alias, index_version):
        """The atomic swap. Rollback is a pointer change, not a rebuild."""
        import datetime as dt

        self.db.execute("INSERT OR REPLACE INTO aliases VALUES (?,?,?)",
                        (alias, index_version, dt.datetime.now().isoformat(timespec="seconds")))
        self.db.commit()
        return index_version

    def resolve(self, alias_or_version):
        row = self.db.execute("SELECT index_version FROM aliases WHERE name=?",
                              (alias_or_version,)).fetchone()
        return row[0] if row else alias_or_version

    # -------------------------------------------------------------- reads --
    def _where(self, index_version, acl_groups=None, filters=None, params=None):
        sql = ["c.index_version = ?", "c.tombstoned = 0"]
        params = params if params is not None else []
        params.append(index_version)
        f = filters or {}
        if f.get("source"):
            srcs = f["source"] if isinstance(f["source"], (list, tuple)) else [f["source"]]
            sql.append("c.source IN ({})".format(",".join("?" * len(srcs))))
            params += list(srcs)
        if f.get("tenant"):
            sql.append("c.tenant = ?")
            params.append(f["tenant"])
        if f.get("published_from"):
            sql.append("c.published >= ?")
            params.append(f["published_from"])
        if f.get("published_to"):
            sql.append("c.published <= ?")
            params.append(f["published_to"])
        if f.get("doc_ids"):
            sql.append("c.doc_id IN ({})".format(",".join("?" * len(f["doc_ids"]))))
            params += list(f["doc_ids"])
        if acl_groups is not None:
            # ACL predicate pushed into the query, not applied to the results.
            ors = " OR ".join(["c.acl LIKE ?"] * len(acl_groups)) or "0"
            sql.append("(" + ors + ")")
            params += [f'%"{g}"%' for g in acl_groups]
        return " AND ".join(sql), params

    def count(self, index_version="v1", acl_groups=None, filters=None):
        where, params = self._where(index_version, acl_groups, filters)
        return self.db.execute(f"SELECT COUNT(*) FROM chunks c WHERE {where}", params).fetchone()[0]

    def get(self, chunk_id, index_version="v1"):
        r = self.db.execute("SELECT * FROM chunks WHERE chunk_id=? AND index_version=?",
                            (chunk_id, index_version)).fetchone()
        return dict(r) if r else None

    def _hit(self, row, score, rank, method):
        return Hit(chunk_id=row["chunk_id"], score=float(score), rank=rank, method=method,
                   doc_id=row["doc_id"], text=row["text"], title=row["title"],
                   source=row["source"], published=row["published"], heading=row["heading"] or "",
                   ordinal=row["ordinal"], acl=tuple(json.loads(row["acl"] or "[]")))

    # -- lexical ------------------------------------------------------------
    @staticmethod
    def fts_query(text):
        """Turn free text into an FTS5 OR query, quoting every token.

        Quoting matters: identifiers like ERR_CONN_RESET contain characters FTS5
        would otherwise read as operators, and an unquoted query either errors
        or silently means something else.
        """
        import re

        toks = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", text)
        toks = [t for t in toks if len(t) > 1]
        quoted = ['"{}"'.format(t.replace('"', '""')) for t in toks]
        return " OR ".join(quoted) or '"_"'

    def lexical(self, query, n=100, index_version="v1", acl_groups=None, filters=None,
                fts_expr=None):
        """BM25 over FTS5. Negated because SQLite returns bm25() as a cost."""
        where, params = self._where(index_version, acl_groups, filters,
                                    params=[fts_expr or self.fts_query(query)])
        sql = (
            "SELECT c.*, bm25(chunks_fts, 4.0, 2.0, 1.0) AS bm "
            "FROM chunks_fts JOIN chunks c "
            "  ON c.chunk_id = chunks_fts.chunk_id AND c.index_version = chunks_fts.index_version "
            f"WHERE chunks_fts MATCH ? AND {where} "
            "ORDER BY bm LIMIT ?"
        )
        rows = self.db.execute(sql, params + [n]).fetchall()
        return [self._hit(r, -r["bm"], i + 1, "bm25") for i, r in enumerate(rows)]

    # -- vector -------------------------------------------------------------
    def _matrix(self, index_version, build_graph=False, M=16):
        """Materialise the vectors as a numpy block; build the k-NN graph lazily.

        The graph is cached separately from the matrix so that an exact search
        (which does not need it) cannot poison the cache for an approximate one
        — a bug worth naming, because the production version of it is an index
        that silently serves the wrong structure after a partial rebuild.
        """
        import numpy as np

        entry = self._cache.get(index_version)
        if entry is None:
            rows = self.db.execute(
                "SELECT chunk_id, vector FROM chunks WHERE index_version=? AND tombstoned=0 "
                "AND vector IS NOT NULL ORDER BY row_id", (index_version,)).fetchall()
            ids = [r["chunk_id"] for r in rows]
            mat = (np.stack([np.frombuffer(r["vector"], dtype="float32") for r in rows])
                   if ids else np.zeros((0, 1), dtype="float32"))
            entry = {"ids": ids, "mat": mat, "graph": None, "M": M}
            self._cache[index_version] = entry

        if build_graph and entry["graph"] is None and len(entry["ids"]) > 2:
            mat = entry["mat"]
            n = len(entry["ids"])
            sims = mat @ mat.T
            np.fill_diagonal(sims, -2.0)
            k = min(M, n - 1)
            near = np.argsort(-sims, axis=1)[:, :k]

            # The "navigable" half of navigable small world. A pure k-NN graph is a
            # lattice of tight neighbourhoods with no shortcuts between them: greedy
            # search walks into the nearest cluster and cannot leave it, so recall
            # collapses as the corpus grows even though every edge is correct. A
            # handful of long-range links per node -- Kleinberg's construction, and
            # what HNSW's upper layers provide -- restores the logarithmic hop count.
            rng = np.random.RandomState(17)
            longr = rng.randint(0, n, size=(n, min(4, max(1, n - 1))))
            entry["graph"] = np.concatenate([near, longr], axis=1)
            entry["M"] = M
        return entry["ids"], entry["mat"], entry["graph"]

    def _scope_key(self, index_version, acl_groups, filters):
        return (index_version, tuple(acl_groups) if acl_groups else None,
                tuple(sorted((k, tuple(v) if isinstance(v, (list, tuple)) else v)
                             for k, v in (filters or {}).items())))

    def _allowed_ids(self, index_version, acl_groups=None, filters=None):
        """The set of chunk ids visible under one (version, ACL, filter) scope.

        Cached, because a search re-asks the same question for every query and the
        answer only changes on a write. Fetching every row's full record to answer
        it -- which is what the naive version does -- costs more than the vector
        search it is supporting.
        """
        key = self._scope_key(index_version, acl_groups, filters)
        hit = self._acl_cache.get(key)
        if hit is None:
            where, params = self._where(index_version, acl_groups, filters)
            hit = {r[0] for r in self.db.execute(
                f"SELECT c.chunk_id FROM chunks c WHERE {where}", params).fetchall()}
            if len(self._acl_cache) > 16:
                self._acl_cache.clear()
            self._acl_cache[key] = hit
        return hit

    def _rows_for(self, chunk_ids, index_version, acl_groups=None, filters=None):
        if not chunk_ids:
            return {}
        allowed = self._allowed_ids(index_version, acl_groups, filters)
        wanted = [c for c in chunk_ids if c in allowed]
        if not wanted:
            return {}
        marks = ",".join("?" * len(wanted))
        rows = self.db.execute(
            f"SELECT c.* FROM chunks c WHERE c.chunk_id IN ({marks}) "
            "AND c.index_version = ? AND c.tombstoned = 0",
            wanted + [index_version]).fetchall()
        return {r["chunk_id"]: r for r in rows}

    def exact_vector(self, qvec, n=100, index_version="v1", acl_groups=None, filters=None):
        """Flat search: recall = 1.0 by construction. The ground truth an
        approximate index must be measured against."""
        import numpy as np

        ids, mat, _ = self._matrix(index_version, build_graph=False)
        if not ids:
            return []
        q = np.asarray(qvec, dtype="float32").reshape(-1)
        sims = mat @ q
        order = np.argsort(-sims)
        allowed = self._allowed_ids(index_version, acl_groups, filters)
        picked = []
        for j in order:
            cid = ids[j]
            if cid in allowed:
                picked.append((cid, float(sims[j])))
                if len(picked) >= n:
                    break
        rows = self._rows_for([c for c, _ in picked], index_version, acl_groups, filters)
        return [self._hit(rows[cid], sc, i + 1, "dense-flat")
                for i, (cid, sc) in enumerate(picked) if cid in rows]

    def ann_vector(self, qvec, n=10, ef_search=40, index_version="v1", acl_groups=None,
                   filters=None, filter_mode="pre", entry_points=4, seed=7):
        """Greedy best-first search over a navigable small-world graph.

        This is a genuine approximate search, not a simulation: raise ef_search
        and recall rises, lower it and the index starts missing chunks whose
        embeddings were perfectly correct. `filter_mode='pre'` refuses to
        traverse *through* forbidden nodes, which is how a selective filter
        strands a graph index in a sparse region -- run it both ways and the
        recall gap is the thing the deck warns you about.
        """
        import heapq
        import random

        import numpy as np

        ids, mat, graph = self._matrix(index_version, build_graph=True)
        if not ids or graph is None:
            return self.exact_vector(qvec, n, index_version, acl_groups, filters)
        q = np.asarray(qvec, dtype="float32").reshape(-1)
        allowed_ids = self._allowed_ids(index_version, acl_groups, filters)
        allowed = {i for i, cid in enumerate(ids) if cid in allowed_ids}

        self.last_ann_visits = 0
        rng = random.Random(seed)
        starts = rng.sample(range(len(ids)), min(entry_points, len(ids)))
        if filter_mode == "pre":
            starts = [s for s in starts if s in allowed] or list(allowed)[:entry_points]

        visited, results, frontier = set(), [], []
        for s in starts:
            heapq.heappush(frontier, (-float(mat[s] @ q), s))
        while frontier:
            negsim, node = heapq.heappop(frontier)
            if node in visited:
                continue
            visited.add(node)
            self.last_ann_visits += 1
            if filter_mode != "pre" or node in allowed:
                results.append((-negsim, node))
            if len(visited) >= ef_search:
                break
            for nb in graph[node]:
                nb = int(nb)
                if nb in visited:
                    continue
                if filter_mode == "pre" and nb not in allowed:
                    continue          # cannot traverse through what we cannot see
                heapq.heappush(frontier, (-float(mat[nb] @ q), nb))

        results.sort(key=lambda t: -t[0])
        picked = [(ids[node], sim) for sim, node in results if ids[node] in allowed_ids][:n]
        rows = self._rows_for([c for c, _ in picked], index_version, acl_groups, filters)
        return [self._hit(rows[cid], sc, i + 1, f"dense-ann(ef={ef_search})")
                for i, (cid, sc) in enumerate(picked) if cid in rows]

    # ------------------------------------------------------------- reports --
    def stats(self, index_version="v1"):
        row = self.db.execute(
            "SELECT COUNT(*) n, SUM(tombstoned) t, COUNT(DISTINCT doc_id) d, "
            "COUNT(DISTINCT embedder_tag) e FROM chunks WHERE index_version=?",
            (index_version,)).fetchone()
        return {"index_version": index_version, "chunks": row["n"], "tombstoned": row["t"] or 0,
                "documents": row["d"], "distinct_embedders": row["e"],
                "aliases": dict(self.db.execute(
                    "SELECT name, index_version FROM aliases").fetchall())}

    def mixed_version_check(self, index_version="v1"):
        """The check that catches the outage the freshness HLD warns about:
        vectors from two different encoders sitting in one index."""
        rows = self.db.execute(
            "SELECT embedder_tag, COUNT(*) n FROM chunks WHERE index_version=? AND tombstoned=0 "
            "GROUP BY embedder_tag", (index_version,)).fetchall()
        tags = {r["embedder_tag"]: r["n"] for r in rows}
        return {"ok": len(tags) <= 1, "tags": tags}
