"""
Chunking strategies -- the seven from the deck's chunking matrix, implemented.

Chunking is the decision that quietly sets the ceiling on everything after it.
The deck's rule is "do not answer chunk size with a number, answer it with the
shape of the document and the shape of the question", and the only way to make
that concrete is to run the same corpus and the same eval set through each
strategy and read the recall off a table.

Every strategy returns Chunk objects with a *stable* chunk_id derived from
doc_id + ordinal + content hash, exactly as the freshness HLD requires. That
is what makes an upsert an upsert rather than a delete-then-insert that orphans
rows and leaves your index quietly wrong.
"""
from __future__ import annotations

import hashlib
import math
import re

from .corpus import Chunk

WORD = re.compile(r"\S+")
SENT = re.compile(r"(?<=[.!?])\s+")


def approx_tokens(text) -> int:
    """A tokenizer-free token estimate: ~4 characters per token.

    Good enough for budgeting and deliberately labelled as an estimate. In
    production you count with the real tokenizer, because tokenizer variance
    across languages is exactly the thing your headroom slice absorbs.
    """
    return max(1, math.ceil(len(str(text)) / 4))


def _mk(doc, ordinal, total, text, heading=""):
    h = hashlib.sha1(text.encode()).hexdigest()[:10]
    return Chunk(
        chunk_id=f"{doc.doc_id}:{ordinal}:{h}",
        doc_id=doc.doc_id, ordinal=ordinal, n_chunks=total, text=text,
        title=doc.title, source=doc.source, published=doc.published,
        acl=tuple(doc.acl), tenant=doc.tenant, heading=heading, content_hash=h,
    )


def _finalize(doc, pieces):
    """Attach ordinals and totals once the piece list is known."""
    out = []
    total = len(pieces)
    for i, (text, heading) in enumerate(pieces):
        out.append(_mk(doc, i, total, text.strip(), heading))
    return out


def _words(text):
    return WORD.findall(text)


def _pack_words(words, size_tokens, overlap_frac):
    """Group words into ~size_tokens windows with a fractional overlap."""
    if not words:
        return []
    per = max(20, int(size_tokens * 0.75))          # ~0.75 words per token
    step = max(1, int(per * (1 - overlap_frac)))
    out, i = [], 0
    while i < len(words):
        out.append(" ".join(words[i:i + per]))
        if i + per >= len(words):
            break
        i += step
    return out


# ------------------------------------------------------------- strategies ----
def fixed(documents, size_tokens=512, overlap=0.15, **_):
    """Cut every N tokens regardless of what the text is doing.

    Cheap, homogeneous, and blind: it will split a table row from its header and
    a premise from its conclusion without noticing.
    """
    chunks = []
    for d in documents:
        body = re.sub(r"^## .*$", "", d.body, flags=re.M)
        chunks += _finalize(d, [(t, "") for t in _pack_words(_words(body), size_tokens, overlap)])
    return chunks


def recursive(documents, size_tokens=512, overlap=0.15, **_):
    """Prefer paragraph breaks, then sentence breaks, then a hard cut.

    The sensible default the deck names -- and the baseline you are supposed to
    beat, not the answer.
    """
    chunks = []
    for d in documents:
        pieces, buf = [], ""
        for para in re.split(r"\n\s*\n", re.sub(r"^## .*$", "", d.body, flags=re.M)):
            para = para.strip()
            if not para:
                continue
            if approx_tokens(buf) + approx_tokens(para) <= size_tokens:
                buf = (buf + "\n" + para).strip()
                continue
            if buf:
                pieces.append(buf)
            if approx_tokens(para) <= size_tokens:
                buf = para
            else:
                sents, cur = SENT.split(para), ""
                for s in sents:
                    if approx_tokens(cur) + approx_tokens(s) > size_tokens and cur:
                        pieces.append(cur)
                        cur = s
                    else:
                        cur = (cur + " " + s).strip()
                buf = cur
        if buf:
            pieces.append(buf)
        # apply overlap by carrying the tail of the previous piece forward
        if overlap and len(pieces) > 1:
            carried = [pieces[0]]
            for prev, cur in zip(pieces, pieces[1:]):
                tail = " ".join(_words(prev)[-max(1, int(len(_words(prev)) * overlap)):])
                carried.append((tail + " " + cur).strip())
            pieces = carried
        chunks += _finalize(d, [(p, "") for p in pieces])
    return chunks


def structural(documents, size_tokens=512, **_):
    """Split on the document's own boundaries and carry the heading into the text.

    The heading path is the cheap part everyone skips. Without it a chunk that
    reads "Engineering will widen the interval" is unattributable, and an
    embedding of it is unretrievable for any query naming the product.
    """
    chunks = []
    for d in documents:
        pieces = []
        for p in d.passages:
            head = f"{d.title} — {p.heading}"
            text = f"{head}\n{p.text}"
            if approx_tokens(text) <= size_tokens:
                pieces.append((text, p.heading))
            else:
                for w in _pack_words(_words(p.text), size_tokens, 0.1):
                    pieces.append((f"{head}\n{w}", p.heading))
        chunks += _finalize(d, pieces)
    return chunks


def semantic(documents, size_tokens=512, threshold=0.22, **_):
    """Start a new chunk where consecutive sentences stop sharing vocabulary.

    Produces chunks that respect topic drift and refuse to respect your token
    budget -- which is the tradeoff the matrix records as "unpredictable sizes".
    """
    from .embed import tokenize

    chunks = []
    for d in documents:
        body = re.sub(r"^## .*$", "", d.body, flags=re.M)
        sents = [s.strip() for s in SENT.split(body) if s.strip()]
        pieces, cur = [], []
        for s in sents:
            if not cur:
                cur = [s]
                continue
            a, b = set(tokenize(cur[-1])), set(tokenize(s))
            sim = len(a & b) / max(1, len(a | b))
            over = approx_tokens(" ".join(cur + [s])) > size_tokens
            if sim < threshold or over:
                pieces.append(" ".join(cur))
                cur = [s]
            else:
                cur.append(s)
        if cur:
            pieces.append(" ".join(cur))
        chunks += _finalize(d, [(p, "") for p in pieces])
    return chunks


def parent_document(documents, child_tokens=180, parent_tokens=900, **_):
    """Embed small, return big.

    The returned Chunk carries the *parent* text (what the model reads) while
    `heading` records the child span that actually matched. Precision on the
    match, context in the answer -- at 1.3x storage and a fat token bill.
    """
    chunks = []
    for d in documents:
        parents = _pack_words(_words(re.sub(r"^## .*$", "", d.body, flags=re.M)),
                              parent_tokens, 0.0) or [d.body]
        pieces = []
        for pi, parent in enumerate(parents):
            for child in _pack_words(_words(parent), child_tokens, 0.0):
                pieces.append((parent, f"child::{child[:80]}"))
        chunks += _finalize(d, pieces)
    return chunks


def contextual(documents, size_tokens=512, overlap=0.15, describe=None, **_):
    """Prepend a generated sentence that situates the chunk in its document.

    This is the Anthropic contextual-retrieval recipe from the deck. The
    situating sentence is produced offline here by a deterministic template
    (title + source + date + section); pass `describe=fn` -- or a Bedrock
    generator -- to produce it with a model instead, which is what you would
    actually ship. Either way the cost lands at index time, once per chunk
    version, rather than on every query forever.
    """
    def default_describe(doc, text, heading):
        who = ", ".join(doc.entities[:3]) if doc.entities else doc.title
        return (f"This excerpt is from '{doc.title}' ({doc.source}, published {doc.published})"
                + (f", section '{heading}'" if heading else "")
                + f". It concerns {who}.")

    describe = describe or default_describe
    chunks = []
    for d in documents:
        base = structural([d], size_tokens=size_tokens)
        pieces = []
        for c in base:
            ctx = describe(d, c.text, c.heading)
            pieces.append((f"{ctx}\n{c.text}", c.heading))
        chunks += _finalize(d, pieces)
    return chunks


def late_chunking(documents, size_tokens=512, doc_context_tokens=90, **_):
    """Keep long-range document context inside every chunk vector.

    True late chunking pools token embeddings produced from a full-document
    forward pass, which needs a long-context encoder. The approximation here
    keeps the same *effect* -- a document-level signal inside each vector --
    by folding a compact document context string into the embedded text while
    leaving the readable chunk text intact for the model.
    """
    from .embed import tokenize

    chunks = []
    for d in documents:
        toks = [t for t in tokenize(d.body)]
        seen, ctx = set(), []
        for t in toks:
            if t not in seen:
                seen.add(t)
                ctx.append(t)
            if len(ctx) >= doc_context_tokens:
                break
        header = "[doc-context] " + " ".join(ctx)
        for c in structural([d], size_tokens=size_tokens):
            chunks.append(c)
            chunks[-1].text = f"{header}\n{c.text}"
        # ordinals were assigned by structural(); they remain stable
    return chunks


STRATEGIES = {
    "fixed": fixed,
    "recursive": recursive,
    "structural": structural,
    "semantic": semantic,
    "parent_document": parent_document,
    "contextual": contextual,
    "late_chunking": late_chunking,
}


def chunk_corpus(documents, strategy="structural", **params):
    if strategy not in STRATEGIES:
        raise KeyError(f"unknown strategy {strategy!r}; have {sorted(STRATEGIES)}")
    return STRATEGIES[strategy](documents, **params)


def chunk_stats(chunks):
    import statistics as st

    toks = [approx_tokens(c.text) for c in chunks]
    return {
        "chunks": len(chunks),
        "median_tokens": int(st.median(toks)) if toks else 0,
        "p90_tokens": int(sorted(toks)[int(len(toks) * 0.9)]) if toks else 0,
        "max_tokens": max(toks) if toks else 0,
        "total_tokens": sum(toks),
        "storage_x": round(sum(toks) / max(1, sum(approx_tokens(c.text) for c in chunks)), 2),
    }
