"""
raglab — a small, complete, runnable implementation of
Retrieval, RAG & Evals.

Nothing here needs the network, an API key, or a dataset download. Everything
here has a documented upgrade path to a real stack: swap the embedder for
Bedrock Titan, the reranker for Bedrock rerank, the store for a Knowledge Base,
the heuristic judge for a model judge -- the harness, the metrics and the eval
set do not change. That property is the lesson.

    from raglab.bootstrap import bootstrap
    env = bootstrap()

    from raglab import corpus, chunking, embed, store, retrieve, pipeline
    bundle = corpus.build_corpus()
"""
from . import (
    agent,
    bedrock,
    bootstrap,
    catalog,
    chunking,
    context,
    corpus,
    costs,
    embed,
    generate,
    judge,
    metrics,
    pipeline,
    retrieve,
    store,
    tables,
    trace,
    trees,
    viz,
)

__all__ = ["agent", "bedrock", "bootstrap", "catalog", "chunking", "context", "corpus", "costs",
           "embed", "generate", "judge", "metrics", "pipeline", "retrieve", "store", "tables",
           "trace", "trees", "viz", "quickstart"]

__version__ = "1.0.0"


#: The configuration notebook 04 arrives at by measurement rather than by
#: assumption: weighted fusion with the dense leg at 0.3, a learned
#: cross-encoder over the top 50, k=8 inside a 6,000-token evidence cap.
#: Notebooks 05 onward start from it; notebook 04 derives it in front of you.
TUNED = {"fusion": "weighted", "alpha": 0.2, "rerank": "cross", "k": 8, "n": 100}


def quickstart(strategy="structural", fusion="rrf", alpha=0.5, rerank="cross", k=8, n=100,
               dim=96, verbose=True):
    """Build a working RAG system in one call: corpus, index, pipeline.

    Every notebook after 01 opens with this, so a learner who jumps straight to
    section 6 still has a live system in front of them within a few seconds.

        bundle, idx, pipe = quickstart()
        trace = pipe.run("Which organization acquired Tessera Analytics?")
    """
    import time

    t0 = time.perf_counter()
    bundle = corpus.build_corpus()
    chunks = chunking.chunk_corpus(bundle.documents, strategy=strategy)

    # Fit the latent space on whole documents, then encode chunks into it --
    # see LsaEmbedder's docstring for why that is not an implementation detail.
    emb = embed.LsaEmbedder(dim=dim).fit([d.title + "\n" + d.body for d in bundle.documents])
    vecs = emb.encode_documents([c.text for c in chunks])

    idx = store.InMemoryIndex()
    idx.upsert(chunks, vecs, index_version="v1", embedder_tag=emb.info.tag)
    idx.set_alias("live", "v1")

    cfg = retrieve.RetrievalConfig(n_candidates=n, k=k, fusion=fusion, rerank=rerank,
                                   alpha=alpha)
    pipe = pipeline.RagPipeline(idx, emb, cfg, name=f"{strategy}/{fusion}/{rerank}/k={k}")
    pipe.chunks = chunks
    pipe.bundle = bundle

    if verbose:
        print(f"corpus     {len(bundle.documents)} documents · {len(chunks)} chunks "
              f"({strategy})")
        print(f"index      in-memory sqlite · FTS5 lexical + {emb.info.tag} vectors")
        print(f"eval set   {len(bundle.questions)} questions "
              f"({sum(1 for q in bundle.questions if q.slice == 'frozen')} frozen)")
        extra = f" (alpha={alpha})" if fusion == "weighted" else ""
        print(f"pipeline   N={n} · fusion={fusion}{extra} · rerank={rerank} · k={k}")
        print(f"ready in   {(time.perf_counter() - t0) * 1000:.0f} ms")
    return bundle, idx, pipe
