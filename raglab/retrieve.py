"""
Retrievers, fusion, rerankers, and context packing.

The deck's mental model is a budget: stage one buys recall cheaply, stage two
spends compute to convert recall into precision, stage three packs a scarce
token budget, stage four generates. This module is that model in code, with
every knob the deck names exposed as a parameter you can sweep:

    N              first-stage candidate depth
    hybrid weights RRF k, or the alpha of weighted score fusion
    rerank depth   how many pairs stage two is allowed to score
    k              how many chunks survive into the context
    token cap      the hard ceiling that k is really constrained by

The one rule the code enforces structurally: stage two can never rank a
document stage one did not return. `reranker_ceiling()` measures that ceiling
so it is a number in a table rather than a sentence in a slide.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .chunking import approx_tokens
from .embed import tokenize
from .store import Hit


# ------------------------------------------------------- reference BM25 -----
def bm25_scores(query, docs, k1=1.5, b=0.75):
    """A from-scratch BM25, for reading rather than for serving.

    SQLite's FTS5 does the real lexical retrieval in this toolkit. This exists
    so notebook 04 can build the formula term by term -- IDF, term-frequency
    saturation, length normalisation -- and check its output ranks the same way
    the production implementation does.
    """
    tokd = [tokenize(d) for d in docs]
    N = len(docs)
    avgdl = sum(len(t) for t in tokd) / max(1, N)
    df = {}
    for toks in tokd:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    qt = tokenize(query)
    out = []
    for toks in tokd:
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        dl = len(toks)
        s = 0.0
        for t in qt:
            f = tf.get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (N - df.get(t, 0) + 0.5) / (df.get(t, 0) + 0.5))
            s += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * dl / avgdl))
        out.append(s)
    return out


# ------------------------------------------------------------ retrievers ----
@dataclass
class RetrievalConfig:
    n_candidates: int = 100
    k: int = 8
    evidence_token_cap: int = 6000
    fusion: str = "rrf"            # rrf | weighted | dense | lexical
    rrf_k: int = 60
    alpha: float = 0.5             # weighted fusion: dense share
    rerank: str = "cross"          # none | cross | late | llm
    rerank_depth: int = 50
    ann: bool = False
    ef_search: int = 64
    dedup: bool = True
    order: str = "score"           # score | edges  (edges = lost-in-the-middle mitigation)
    index_version: str = "v1"
    filters: dict = field(default_factory=dict)
    acl_groups: tuple = None
    filter_mode: str = "pre"       # pre | post


class LexicalRetriever:
    method = "bm25"

    def __init__(self, index):
        self.index = index

    def search(self, query, n, cfg: RetrievalConfig):
        return self.index.lexical(query, n=n, index_version=cfg.index_version,
                                  acl_groups=cfg.acl_groups if cfg.filter_mode == "pre" else None,
                                  filters=cfg.filters)


class DenseRetriever:
    method = "dense"

    def __init__(self, index, embedder):
        self.index = index
        self.embedder = embedder

    def search(self, query, n, cfg: RetrievalConfig):
        qv = self.embedder.encode_queries([query])[0]
        acl = cfg.acl_groups if cfg.filter_mode == "pre" else None
        if cfg.ann:
            return self.index.ann_vector(qv, n=n, ef_search=cfg.ef_search,
                                         index_version=cfg.index_version, acl_groups=acl,
                                         filters=cfg.filters, filter_mode=cfg.filter_mode)
        return self.index.exact_vector(qv, n=n, index_version=cfg.index_version,
                                       acl_groups=acl, filters=cfg.filters)


class GrepRetriever:
    """Literal / regex search over chunk text. Perfect precision, no paraphrase.

    The deck's point about agents on a repository: for a task anchored in local
    artifacts, exactness beats semantic recall, and every step is inspectable.
    """

    method = "grep"

    def __init__(self, chunks):
        self.chunks = list(chunks)

    def search(self, pattern, n=20, cfg=None, ignore_case=True):
        flags = re.IGNORECASE if ignore_case else 0
        rx = re.compile(pattern, flags)
        out = []
        for c in self.chunks:
            hits = list(rx.finditer(c.text))
            if not hits:
                continue
            out.append(Hit(chunk_id=c.chunk_id, score=float(len(hits)), rank=0, method="grep",
                           doc_id=c.doc_id, text=c.text, title=c.title, source=c.source,
                           published=c.published, heading=c.heading, ordinal=c.ordinal,
                           acl=tuple(c.acl)))
        out.sort(key=lambda h: -h.score)
        for i, h in enumerate(out[:n], 1):
            h.rank = i
        return out[:n]


# ---------------------------------------------------------------- fusion ----
def rrf(lists, k=60, weights=None):
    """Reciprocal rank fusion: RRF(d) = sum_r 1/(k + rank_r(d)).

    Rank-based on purpose. BM25 is unbounded and cosine lives in [-1, 1]; they
    are not on the same scale and no amount of min-max normalisation makes them
    comparable across queries. Throwing magnitude away is the price of never
    having to re-tune when a score distribution drifts.
    """
    weights = weights or [1.0] * len(lists)
    agg, keep = {}, {}
    for w, lst in zip(weights, lists):
        for h in lst:
            agg[h.chunk_id] = agg.get(h.chunk_id, 0.0) + w / (k + h.rank)
            keep.setdefault(h.chunk_id, h)
    merged = sorted(agg.items(), key=lambda kv: -kv[1])
    out = []
    for i, (cid, sc) in enumerate(merged, 1):
        h = keep[cid]
        out.append(Hit(cid, sc, i, "rrf", h.doc_id, h.text, h.title, h.source, h.published,
                       h.heading, h.ordinal, h.acl))
    return out


def weighted_fusion(lists, alpha=0.5, methods=("dense", "bm25")):
    """s(d) = alpha * dense_norm(d) + (1-alpha) * bm25_norm(d).

    Keeps magnitude, so a dominant exact-identifier match can win outright --
    and inherits the instability the deck names: min-max normalisation is over
    the candidate set, so it is query-dependent, and alpha tuned on 200
    examples will not survive a corpus refresh.
    """
    norm = []
    for lst in lists:
        if not lst:
            norm.append({})
            continue
        lo = min(h.score for h in lst)
        hi = max(h.score for h in lst)
        rng = (hi - lo) or 1.0
        norm.append({h.chunk_id: (h.score - lo) / rng for h in lst})
    keep = {h.chunk_id: h for lst in lists for h in lst}
    ws = [alpha, 1 - alpha] if len(lists) == 2 else [1 / len(lists)] * len(lists)
    agg = {}
    for w, d in zip(ws, norm):
        for cid, s in d.items():
            agg[cid] = agg.get(cid, 0.0) + w * s
    out = []
    for i, (cid, sc) in enumerate(sorted(agg.items(), key=lambda kv: -kv[1]), 1):
        h = keep[cid]
        out.append(Hit(cid, sc, i, "weighted", h.doc_id, h.text, h.title, h.source, h.published,
                       h.heading, h.ordinal, h.acl))
    return out


# ------------------------------------------------------------- rerankers ----
class NoReranker:
    name = "none"
    added_latency_ms = 0

    def rerank(self, query, hits, depth=None):
        return hits


PAIR_FEATURES = ("coverage", "proximity", "phrase", "title", "maxsim", "doc_cosine",
                 "exact_id", "length")


def pair_features(query, hits, embedder=None, length_b=0.55, _cache=None):
    """Features that only a (query, passage) *pair* can produce.

    This is the concrete content of "early interaction". A bi-encoder has to
    compress the passage into one vector before it has seen the query; every
    feature below is computed after seeing both, and `maxsim` in particular
    scores each query token against each passage token, which a single passage
    vector structurally cannot do.

        coverage   share of query terms present, BM25-style length-normalised
        proximity  tightness of the window containing the matched query terms
        phrase     longest contiguous query n-gram appearing verbatim
        title      query-term overlap with the title and heading path
        maxsim     mean over query tokens of the best matching passage token
        doc_cosine whole-passage similarity in the encoder's latent space
        exact_id   an identifier (ERR_CONN_RESET, ABC-123) matched literally
        length     log passage length -- lets the model learn its own length prior
    """
    import math

    import numpy as np

    cache = _cache if _cache is not None else {}
    qtok = tokenize(query)
    qset = list(dict.fromkeys(qtok))
    qraw = str(query)
    ids = set(re.findall(r"[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]+)+|[A-Z]{2,}-\d+", qraw))

    qvecs = None
    if embedder is not None and hasattr(embedder, "token_vectors"):
        qvecs = embedder.token_vectors(query, 64)[0]
    qdoc = None
    if embedder is not None and hasattr(embedder, "encode_queries"):
        qdoc = embedder.encode_queries([query])[0]

    toks = []
    for h in hits:
        key = ("tok", h.chunk_id)
        if key not in cache:
            cache[key] = tokenize(h.text)
        toks.append(cache[key])
    avgdl = (sum(len(t) for t in toks) / len(toks)) if toks else 1.0

    rows = []
    for h, dtok in zip(hits, toks):
        dset = set(dtok)
        if qset and dtok:
            raw_cov = sum(1 for t in qset if t in dset) / len(qset)
            norm = 1 - length_b + length_b * (len(dtok) / max(1.0, avgdl))
            coverage = raw_cov / norm
        else:
            coverage = 0.0

        pos = {}
        for i, t in enumerate(dtok):
            pos.setdefault(t, []).append(i)
        present = [t for t in qset if t in pos]
        if len(present) >= 2:
            span = max(pos[t][-1] for t in present) - min(pos[t][0] for t in present) + 1
            proximity = len(present) / max(len(present), span)
        else:
            proximity = 0.3 if present else 0.0

        low = h.text.lower()
        best = 0
        for size in range(min(6, len(qtok)), 1, -1):
            if any(" ".join(qtok[i:i + size]) in low for i in range(len(qtok) - size + 1)):
                best = size
                break
        phrase = best / max(2, len(qtok))

        head = set(tokenize((h.title or "") + " " + (h.heading or "")))
        title = sum(1 for t in qset if t in head) / max(1, len(qset)) if qset else 0.0

        maxsim = 0.0
        if qvecs is not None and len(qvecs):
            key = ("vec", h.chunk_id)
            if key not in cache:
                cache[key] = embedder.token_vectors(h.text, 64)[0]
            dv = cache[key]
            if len(dv):
                maxsim = float((qvecs @ dv.T).max(axis=1).mean())

        doc_cosine = 0.0
        if qdoc is not None:
            key = ("doc", h.chunk_id)
            if key not in cache:
                cache[key] = embedder.encode_documents([h.text])[0]
            doc_cosine = float(np.dot(qdoc, cache[key]))

        exact_id = 1.0 if (ids and any(i in h.text for i in ids)) else 0.0
        length = math.log1p(len(dtok)) / 8.0
        rows.append([coverage, proximity, phrase, title, maxsim, doc_cosine, exact_id, length])
    return np.asarray(rows, dtype="float32"), cache


# Weights fitted by logistic regression on this corpus's *dev* slice only --
# see notebook 04, which refits them in front of you and then checks the gain
# survives on the frozen slice. In a client engagement you fit your own; the
# numbers below are not a universal constant and should not be treated as one.
DEFAULT_CROSS_WEIGHTS = {
    "coverage": 1.1148, "proximity": 0.1382, "phrase": -0.5067, "title": 0.5836,
    "maxsim": -0.0590, "doc_cosine": 1.2589, "exact_id": 0.6051, "length": -0.7266,
    "bias": -0.7722,
}


class ProxyCrossEncoder:
    """A learned early-interaction reranker with a real cross-encoder's cost model.

    Be precise about what this is. A shipped cross-encoder is a transformer that
    attends over the concatenated query and passage and was trained on millions
    of labelled pairs. This is a logistic regression over eight pair features,
    fitted on a few hundred labelled pairs from this corpus. It is far simpler
    and far weaker -- and it is architecturally the same animal:

        it scores the pair, not two independent representations
        nothing can be precomputed, because the features depend on the pair
        cost is linear in N: reranking 100 candidates is 100 scorings, per query
        batching, not looping, is what keeps the latency in the tens of ms

    It is also honest about the thing people forget: a reranker is a *model*,
    so it has training data, it can overfit, and its gain has to survive on a
    slice it never saw. `fit()` and the frozen-slice check in notebook 04 are
    that discipline, not decoration.

    Swap in `SentenceTransformersReranker` or `BedrockReranker` for the real
    thing; every measurement downstream keeps working.
    """

    name = "cross-encoder (learned proxy)"
    added_latency_ms = 220

    def __init__(self, embedder=None, weights=None, length_b=0.55):
        import numpy as np

        self.embedder = embedder
        self.length_b = length_b
        w = dict(weights or DEFAULT_CROSS_WEIGHTS)
        self.bias = float(w.pop("bias", 0.0))
        self.w = np.array([w.get(f, 0.0) for f in PAIR_FEATURES], dtype="float32")
        self._cache = {}

    def score_all(self, query, hits):
        import numpy as np

        if not hits:
            return []
        X, self._cache = pair_features(query, hits, self.embedder, self.length_b, self._cache)
        z = X @ self.w + self.bias
        return 1.0 / (1.0 + np.exp(-z))

    def rerank(self, query, hits, depth=50):
        pool = hits[:depth]
        if not pool:
            return hits
        scores = self.score_all(query, pool)
        order = sorted(zip(scores, range(len(pool))), key=lambda t: (-t[0], t[1]))
        out = []
        for rank, (sc, i) in enumerate(order, 1):
            h = pool[i]
            out.append(Hit(h.chunk_id, float(sc), rank, "cross", h.doc_id, h.text, h.title,
                           h.source, h.published, h.heading, h.ordinal, h.acl))
        return out + hits[depth:]

    # ------------------------------------------------------------ training --
    def fit(self, training_pairs, epochs=400, lr=0.6, l2=0.02, verbose=False):
        """Fit on labelled (query, hits, gold_chunk_ids) triples.

        Plain logistic regression by gradient descent -- deliberately small
        enough to read. The interesting part is not the optimiser, it is that
        the training set must come from questions the frozen slice does not
        contain, or the number you report at the end is a memory, not a result.
        """
        import numpy as np

        Xs, ys = [], []
        for query, hits, gold in training_pairs:
            if not hits:
                continue
            X, self._cache = pair_features(query, hits, self.embedder, self.length_b, self._cache)
            Xs.append(X)
            ys.append(np.array([1.0 if h.chunk_id in gold else 0.0 for h in hits],
                               dtype="float32"))
        if not Xs:
            return self
        X = np.vstack(Xs)
        y = np.concatenate(ys)
        pos = max(1.0, y.sum())
        wpos = (len(y) - pos) / pos          # class weight: gold pairs are rare
        w = np.zeros(X.shape[1], dtype="float32")
        b = 0.0
        for ep in range(epochs):
            z = X @ w + b
            p = 1.0 / (1.0 + np.exp(-z))
            sw = np.where(y > 0, wpos, 1.0)
            g = (sw * (p - y))
            gw = X.T @ g / len(y) + l2 * w
            gb = g.mean()
            w -= lr * gw
            b -= lr * gb
            if verbose and ep % 100 == 0:
                loss = -(sw * (y * np.log(p + 1e-9) + (1 - y) * np.log(1 - p + 1e-9))).mean()
                print(f"    epoch {ep:>4}  loss {loss:.4f}")
        self.w, self.bias = w.astype("float32"), float(b)
        return self

    @property
    def learned_weights(self):
        d = {f: round(float(v), 4) for f, v in zip(PAIR_FEATURES, self.w)}
        d["bias"] = round(self.bias, 4)
        return d


class LateInteractionReranker:
    """MaxSim over token-level vectors: sum_i max_j q_i . d_j.

    Real late interaction, computed on the LSA term space. Passage token
    vectors are precomputable, which is the whole trade the deck describes:
    10-100x the storage in exchange for latency an order of magnitude below a
    cross-encoder.
    """

    name = "late interaction (MaxSim)"
    added_latency_ms = 25

    def __init__(self, embedder, max_tokens=48):
        self.embedder = embedder
        self.max_tokens = max_tokens
        self._cache = {}

    def _doc_vecs(self, h):
        if h.chunk_id not in self._cache:
            self._cache[h.chunk_id] = self.embedder.token_vectors(h.text, self.max_tokens)[0]
        return self._cache[h.chunk_id]

    def rerank(self, query, hits, depth=50):

        qv, _ = self.embedder.token_vectors(query, self.max_tokens)
        pool = hits[:depth]
        scored = []
        for h in pool:
            dv = self._doc_vecs(h)
            if len(qv) == 0 or len(dv) == 0:
                scored.append((0.0, h))
                continue
            scored.append((float((qv @ dv.T).max(axis=1).sum() / len(qv)), h))
        scored.sort(key=lambda t: -t[0])
        out = [Hit(h.chunk_id, s, i, "late", h.doc_id, h.text, h.title, h.source, h.published,
                   h.heading, h.ordinal, h.acl) for i, (s, h) in enumerate(scored, 1)]
        return out + hits[depth:]


class SentenceTransformersReranker:
    name = "cross-encoder (real)"
    added_latency_ms = 180

    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder

        self.model = CrossEncoder(model_name)

    def rerank(self, query, hits, depth=50):
        pool = hits[:depth]
        if not pool:
            return hits
        scores = self.model.predict([(query, h.text) for h in pool])
        order = sorted(zip(scores, pool), key=lambda t: -t[0])
        out = [Hit(h.chunk_id, float(s), i, "cross-real", h.doc_id, h.text, h.title, h.source,
                   h.published, h.heading, h.ordinal, h.acl) for i, (s, h) in enumerate(order, 1)]
        return out + hits[depth:]


class BedrockReranker:
    """Amazon Bedrock rerank API (e.g. cohere.rerank-v3-5:0 / amazon.rerank-v1:0)."""

    name = "bedrock rerank"
    added_latency_ms = 300

    def __init__(self, model_id="amazon.rerank-v1:0", region=None, client=None):
        import boto3

        self.model_id = model_id
        self.client = client or boto3.client("bedrock-agent-runtime", region_name=region)
        self.region = region

    def rerank(self, query, hits, depth=50):
        pool = hits[:depth]
        if not pool:
            return hits
        resp = self.client.rerank(
            queries=[{"type": "TEXT", "textQuery": {"text": query}}],
            sources=[{"type": "INLINE", "inlineDocumentSource":
                      {"type": "TEXT", "textDocument": {"text": h.text}}} for h in pool],
            rerankingConfiguration={
                "type": "BEDROCK_RERANKING_MODEL",
                "bedrockRerankingConfiguration": {
                    "numberOfResults": len(pool),
                    "modelConfiguration": {"modelArn": self.model_id}}})
        out = []
        for i, r in enumerate(resp["results"], 1):
            h = pool[r["index"]]
            out.append(Hit(h.chunk_id, float(r["relevanceScore"]), i, "bedrock-rerank", h.doc_id,
                           h.text, h.title, h.source, h.published, h.heading, h.ordinal, h.acl))
        return out + hits[depth:]


def make_reranker(kind, embedder=None):
    if kind in (None, "none"):
        return NoReranker()
    if kind == "cross":
        return ProxyCrossEncoder(embedder)
    if kind == "late":
        return LateInteractionReranker(embedder)
    raise KeyError(kind)


# ------------------------------------------------------------- retrieval ----
class HybridRetriever:
    """First stage: run both legs wide, then merge. One candidate set out."""

    def __init__(self, index, embedder):
        self.index = index
        self.lexical = LexicalRetriever(index)
        self.dense = DenseRetriever(index, embedder)

    def search(self, query, cfg: RetrievalConfig):
        n = cfg.n_candidates
        legs, names = [], []
        if cfg.fusion in ("rrf", "weighted", "lexical"):
            legs.append(self.lexical.search(query, n, cfg))
            names.append("bm25")
        if cfg.fusion in ("rrf", "weighted", "dense"):
            legs.append(self.dense.search(query, n, cfg))
            names.append("dense")
        if cfg.fusion == "lexical":
            return legs[0][:n]
        if cfg.fusion == "dense":
            return legs[0][:n]
        if cfg.fusion == "weighted":
            dense_leg = legs[names.index("dense")]
            lex_leg = legs[names.index("bm25")]
            return weighted_fusion([dense_leg, lex_leg], alpha=cfg.alpha)[:n]
        return rrf(legs, k=cfg.rrf_k)[:n]


def dedup_hits(hits, jaccard=0.82):
    """Drop near-identical chunks before packing.

    Duplicates are distractors that also cost tokens, which is why the deck
    puts deduplication in the free-savings tier of the cost levers.
    """
    kept, sigs = [], []
    for h in hits:
        s = set(tokenize(h.text))
        if any(len(s & t) / max(1, len(s | t)) >= jaccard for t in sigs):
            continue
        kept.append(h)
        sigs.append(s)
    for i, h in enumerate(kept, 1):
        h.rank = i
    return kept


def order_for_position(hits, mode="score"):
    """'edges' places the two strongest chunks at the head and the tail.

    The cheapest available mitigation for the U-shaped position effect: put the
    best evidence where attention is strongest and let the weakest chunks take
    the middle.
    """
    if mode != "edges" or len(hits) < 3:
        return hits
    rest = hits[2:]
    return [hits[0]] + rest + [hits[1]]


def pack_context(hits, k=8, token_cap=6000, dedup=True, order="score"):
    """Select the evidence that reaches the model, under a hard token cap.

    Whole chunks are dropped by rank; a chunk is never truncated mid-way,
    because a half chunk breaks its own citation.
    """
    pool = dedup_hits(hits) if dedup else list(hits)
    selected, used = [], 0
    for h in pool:
        if len(selected) >= k:
            break
        t = approx_tokens(h.text)
        if used + t > token_cap:
            continue
        selected.append(h)
        used += t
    selected = order_for_position(selected, order)
    return selected, used


def reranker_ceiling(first_stage_hits, gold_chunk_ids, k=8):
    """The ceiling stage two cannot exceed, measured rather than asserted."""
    got = {h.chunk_id for h in first_stage_hits}
    gold = set(gold_chunk_ids)
    if not gold:
        return 1.0
    return len(gold & got) / len(gold)
