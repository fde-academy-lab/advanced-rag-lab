"""
Embedding providers behind one interface.

The default is a real dense retriever, not a toy: latent semantic analysis --
TF-IDF over the corpus, then a truncated SVD. It is the original dense
retrieval method, it runs in milliseconds with no download, it is fully
deterministic, and it genuinely bridges some paraphrase gaps through
co-occurrence. What it does *not* do is bridge a gap between two words that
never co-occur anywhere in the corpus, which is exactly the honest limitation a
learner should internalise before they assume an API encoder is magic.

    LsaEmbedder                  default. offline, deterministic, fits the corpus
    HashingEmbedder              a deliberately weak encoder, for ablations
    SentenceTransformersEmbedder a real neural encoder, if the package is present
    BedrockEmbedder              Amazon Titan / Cohere via bedrock-runtime

Every provider exposes the same three things:

    fit(texts)                   optional; corpus-fitted models use it
    encode_documents(texts)      -> (n, d) L2-normalised float32
    encode_queries(texts)        -> (n, d) L2-normalised float32

The document/query split is not decoration. Encoders that take instruction
prefixes need different text on each side, and getting that wrong is one of the
most common silent recall regressions in production -- notebook 04 reproduces
it on purpose.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]+|\d+(?:\.\d+)?")

STOP = set("""a an and are as at be by for from has have in is it its of on or that the to was were
with will would can could should this these those there their they we you your our not no but if
than then when which who whom whose what how why into over under about after before during said
say says been being do does did done had having he she his her them us me my
""".split())


def tokenize(text, keep_stop=False):
    toks = [t.lower() for t in TOKEN_RE.findall(str(text))]
    return toks if keep_stop else [t for t in toks if t not in STOP and len(t) > 1]


def l2_normalize(mat):
    import numpy as np

    mat = np.asarray(mat, dtype="float32")
    if mat.ndim == 1:
        mat = mat[None, :]
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


@dataclass
class EmbedderInfo:
    """Metadata that must be pinned to every vector you write to an index.

    The deck's rule: an encoder upgrade is a full reindex, and a mixed-version
    index produces wrong answers with confident scores. You cannot enforce that
    rule unless the version travels with the vector -- so it lives here and the
    store writes it on every row.
    """

    name: str
    dim: int
    version: str
    doc_prefix: str = ""
    query_prefix: str = ""
    normalized: bool = True

    @property
    def tag(self) -> str:
        return f"{self.name}@{self.version}:d{self.dim}"


class BaseEmbedder:
    info: EmbedderInfo

    def fit(self, texts):
        return self

    def encode_documents(self, texts):
        raise NotImplementedError

    def encode_queries(self, texts):
        raise NotImplementedError


class LsaEmbedder(BaseEmbedder):
    """TF-IDF -> truncated SVD. The default offline dense retriever.

    Two choices in here are worth arguing about, because both are decisions you
    will make again with a real encoder.

    Fit on documents, encode chunks. The association between "pause between
    reconnection attempts" and "retry delay" lives at document level -- a
    support article contains the customer's register in its symptom section and
    the engineer's register in its resolution. Fit the latent space on chunks
    and you fit it on fragments that never see each other, and the encoder
    learns nothing it could not have learned from a bag of words.

    Dimension is a generalisation knob, not just a cost knob. High dimension
    reproduces the term space almost exactly and behaves like a slightly fuzzy
    BM25; low dimension smooths hard and starts bridging vocabulary. On this
    corpus the paraphrase slice peaks near 48 dimensions and the exact-match
    slice peaks near 96 -- which is the same tension the deck's embedding tree
    describes when it tells you to measure the recall you lose at 512 and 256
    before paying for 3072. Sweep it in notebook 04; do not inherit the default.
    """

    def __init__(self, dim=96, doc_prefix="", query_prefix="", min_df=1, version="1.0"):
        self.dim = dim
        self.min_df = min_df
        self.vocab = {}
        self.idf = None
        self.V = None       # term -> latent  (n_terms, k)
        self.S = None
        self.term_space = None
        self.info = EmbedderInfo("lsa", dim, version, doc_prefix, query_prefix)

    # -- internals ---------------------------------------------------------
    def _counts(self, texts):

        rows = []
        for t in texts:
            c = {}
            for tok in tokenize(t):
                c[tok] = c.get(tok, 0) + 1
            rows.append(c)
        return rows

    def _matrix(self, rows):
        import numpy as np

        X = np.zeros((len(rows), len(self.vocab)), dtype="float32")
        for i, c in enumerate(rows):
            for tok, n in c.items():
                j = self.vocab.get(tok)
                if j is not None:
                    X[i, j] = 1.0 + math.log(n)
        X *= self.idf
        return X

    # -- api ---------------------------------------------------------------
    def fit(self, texts):
        import numpy as np

        texts = [self.info.doc_prefix + t for t in texts]
        rows = self._counts(texts)
        df = {}
        for c in rows:
            for tok in c:
                df[tok] = df.get(tok, 0) + 1
        self.vocab = {t: i for i, (t, n) in enumerate(sorted(df.items())) if n >= self.min_df}
        # re-key after filtering
        self.vocab = {t: i for i, t in enumerate(sorted(self.vocab))}
        N = len(texts)
        self.idf = np.ones(len(self.vocab), dtype="float32")
        for t, i in self.vocab.items():
            self.idf[i] = math.log((1 + N) / (1 + df.get(t, 0))) + 1.0

        X = self._matrix(rows)
        k = min(self.dim, min(X.shape) - 1) if min(X.shape) > 1 else 1
        U, S, Vt = np.linalg.svd(X, full_matrices=False)
        self.S = S[:k]
        self.V = Vt[:k].T                       # (n_terms, k)
        self.term_space = l2_normalize(self.V * self.S)   # terms in latent space
        self.info.dim = k
        self.dim = k
        return self

    def _embed(self, texts, prefix):

        if self.V is None:
            raise RuntimeError("LsaEmbedder.fit(corpus_texts) must be called first.")
        rows = self._counts([prefix + t for t in texts])
        X = self._matrix(rows)
        return l2_normalize(X @ self.V)

    def encode_documents(self, texts):
        return self._embed(list(texts), self.info.doc_prefix)

    def encode_queries(self, texts):
        return self._embed(list(texts), self.info.query_prefix)

    def token_vectors(self, text, max_tokens=48):
        """Per-token latent vectors -- the input a late-interaction scorer needs."""
        import numpy as np

        toks = [t for t in tokenize(text) if t in self.vocab][:max_tokens]
        if not toks:
            return np.zeros((0, self.dim), dtype="float32"), []
        idx = [self.vocab[t] for t in toks]
        return self.term_space[idx], toks


class HashingEmbedder(BaseEmbedder):
    """Character-trigram hashing into a random-ish projection.

    Deliberately mediocre. It exists so notebooks can show what a *worse*
    encoder does to Recall@N without anyone having to take it on trust.
    """

    def __init__(self, dim=192, version="0.1"):
        self.dim = dim
        self.info = EmbedderInfo("hash-trigram", dim, version)

    def _one(self, text):
        import numpy as np

        v = np.zeros(self.dim, dtype="float32")
        s = " " + re.sub(r"\s+", " ", str(text).lower()) + " "
        for i in range(len(s) - 2):
            g = s[i:i + 3]
            h = int(hashlib.md5(g.encode()).hexdigest()[:8], 16)
            v[h % self.dim] += 1.0 if (h >> 8) & 1 else -1.0
        return v

    def encode_documents(self, texts):
        import numpy as np

        return l2_normalize(np.stack([self._one(t) for t in texts]))

    encode_queries = encode_documents


class SentenceTransformersEmbedder(BaseEmbedder):
    """A real neural encoder. Requires the package and a one-time model download."""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2",
                 doc_prefix="", query_prefix=""):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        dim = self.model.get_sentence_embedding_dimension()
        self.info = EmbedderInfo(model_name.split("/")[-1], dim, "st", doc_prefix, query_prefix)

    def encode_documents(self, texts):
        return l2_normalize(self.model.encode([self.info.doc_prefix + t for t in texts]))

    def encode_queries(self, texts):
        return l2_normalize(self.model.encode([self.info.query_prefix + t for t in texts]))


class BedrockEmbedder(BaseEmbedder):
    """Amazon Bedrock text embeddings (Titan v2 or Cohere).

        emb = BedrockEmbedder(model_id="amazon.titan-embed-text-v2:0", region="us-east-1")

    Credentials come from the ordinary boto3 chain: env vars, ~/.aws/credentials,
    an instance role, or SSO. Nothing in these notebooks reads or stores a key.
    """

    def __init__(self, model_id="amazon.titan-embed-text-v2:0", region=None, dim=1024,
                 client=None, doc_prefix="", query_prefix=""):
        import boto3

        self.model_id = model_id
        self.dim = dim
        self.client = client or boto3.client("bedrock-runtime", region_name=region)
        self.info = EmbedderInfo(model_id, dim, "bedrock", doc_prefix, query_prefix)

    def _call(self, text):
        import json

        if "cohere" in self.model_id:
            body = {"texts": [text], "input_type": "search_document"}
        else:
            body = {"inputText": text, "dimensions": self.dim, "normalize": True}
        resp = self.client.invoke_model(modelId=self.model_id, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        if "embeddings" in payload:
            return payload["embeddings"][0]
        return payload["embedding"]

    def _batch(self, texts, prefix):
        import numpy as np

        return l2_normalize(np.array([self._call(prefix + t) for t in texts], dtype="float32"))

    def encode_documents(self, texts):
        return self._batch(list(texts), self.info.doc_prefix)

    def encode_queries(self, texts):
        return self._batch(list(texts), self.info.query_prefix)


def cosine(a, b):
    """Cosine similarity between an (n,d) and an (m,d) block -> (n,m).

    After L2 normalisation this is a plain dot product, which is the whole
    content of the deck's cosine slide expressed as one line of numpy.
    """

    A, B = l2_normalize(a), l2_normalize(b)
    return A @ B.T
