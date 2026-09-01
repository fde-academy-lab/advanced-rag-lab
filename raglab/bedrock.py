"""
AWS Bedrock: the production path these notebooks are a rehearsal for.

Nothing here runs by default and nothing here is required. The notebooks are
built so that the *same* code paths work against either the in-memory index or
a managed Bedrock Knowledge Base -- you change the retriever, not the harness,
not the metrics, and not the eval set. That is the point: if swapping the
retrieval backend forces you to rewrite your measurement, your measurement was
coupled to your implementation and it will not survive the next change either.

Configuration comes from environment variables so no key ever lands in a
notebook cell:

    AWS_REGION                    e.g. us-east-1
    BEDROCK_KB_ID                 the Knowledge Base id
    BEDROCK_MODEL_ID              generation / judge model
    BEDROCK_EMBED_MODEL_ID        e.g. amazon.titan-embed-text-v2:0
    BEDROCK_RERANK_MODEL_ARN      optional rerank model

Credentials themselves come from the ordinary boto3 chain: environment,
~/.aws/credentials, SSO, or an instance role.

    from raglab.bedrock import BedrockConfig, preflight
    cfg = BedrockConfig.from_env()
    preflight(cfg)                       # says what is configured, calls nothing

    kb = BedrockKnowledgeBaseRetriever(cfg)
    hits = kb.search("Which organization acquired Tessera Analytics?", n=10)

The returned objects are the same `Hit` records the in-memory store produces,
so `metrics.py`, `pipeline.evaluate`, the judge and the trace store all work
unchanged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .store import Hit


@dataclass
class BedrockConfig:
    region: str = ""
    knowledge_base_id: str = ""
    model_id: str = "anthropic.claude-sonnet-4-5-20250929-v1:0"
    embed_model_id: str = "amazon.titan-embed-text-v2:0"
    rerank_model_arn: str = ""
    number_of_results: int = 25
    search_type: str = "HYBRID"          # HYBRID | SEMANTIC
    guardrail_id: str = ""
    guardrail_version: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            region=os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION", ""),
            knowledge_base_id=os.getenv("BEDROCK_KB_ID", ""),
            model_id=os.getenv("BEDROCK_MODEL_ID", cls.model_id),
            embed_model_id=os.getenv("BEDROCK_EMBED_MODEL_ID", cls.embed_model_id),
            rerank_model_arn=os.getenv("BEDROCK_RERANK_MODEL_ARN", ""),
            guardrail_id=os.getenv("BEDROCK_GUARDRAIL_ID", ""),
            guardrail_version=os.getenv("BEDROCK_GUARDRAIL_VERSION", ""),
        )

    @property
    def ready(self):
        return bool(self.region and self.knowledge_base_id)


def preflight(cfg: BedrockConfig = None, verbose=True):
    """Report what is configured. Makes no AWS calls and costs nothing.

    Deliberately read-only: a notebook that silently starts billing an account
    because someone hit Run All is a bad notebook.
    """
    cfg = cfg or BedrockConfig.from_env()
    try:
        import boto3  # noqa: F401

        has_boto = True
    except Exception:
        has_boto = False

    creds = False
    if has_boto:
        try:
            import boto3

            creds = boto3.Session().get_credentials() is not None
        except Exception:
            creds = False

    status = {
        "boto3 installed": has_boto,
        "credentials resolvable": creds,
        "AWS_REGION": cfg.region or "(unset)",
        "BEDROCK_KB_ID": cfg.knowledge_base_id or "(unset)",
        "BEDROCK_MODEL_ID": cfg.model_id,
        "BEDROCK_EMBED_MODEL_ID": cfg.embed_model_id,
        "rerank model": cfg.rerank_model_arn or "(unset)",
        "guardrail": cfg.guardrail_id or "(unset)",
        "ready for live calls": bool(has_boto and creds and cfg.ready),
    }
    if verbose:
        width = max(len(k) for k in status)
        print("AWS Bedrock preflight — no calls made, nothing billed\n")
        for k, v in status.items():
            mark = "ok " if v not in (False, "(unset)") else "-- "
            print(f"  [{mark}] {k:<{width}}  {v}")
        if not status["ready for live calls"]:
            print("\n  Offline path is active. Everything in these notebooks still runs;\n"
                  "  set AWS_REGION and BEDROCK_KB_ID to switch the retriever to a live KB.")
    return status


class BedrockKnowledgeBaseRetriever:
    """A managed Knowledge Base behind the same interface as the local index.

    Two modes, and the difference matters architecturally:

      retrieve()            you get chunks back and keep control of packing,
                            ordering, the prompt contract and the citations.
                            Everything in notebooks 05 and 06 still applies.

      retrieve_and_generate() AWS packs and generates for you. Faster to ship,
                            and you give up the context-assembly stage --
                            which is the stage the deck spends a whole section
                            on. Use it for a pilot; expect to outgrow it the
                            first time a client asks why a citation is wrong.
    """

    method = "bedrock-kb"

    def __init__(self, cfg: BedrockConfig = None, client=None, agent_client=None):
        import boto3

        self.cfg = cfg or BedrockConfig.from_env()
        if not self.cfg.ready:
            raise RuntimeError(
                "BedrockConfig is not ready: set AWS_REGION and BEDROCK_KB_ID. "
                "Run raglab.bedrock.preflight() to see what is missing.")
        self.client = agent_client or boto3.client("bedrock-agent-runtime",
                                                   region_name=self.cfg.region)
        self.runtime = client or boto3.client("bedrock-runtime", region_name=self.cfg.region)

    def _vector_config(self, n, filters=None):
        vc = {"numberOfResults": n, "overrideSearchType": self.cfg.search_type}
        if filters:
            vc["filter"] = filters
        if self.cfg.rerank_model_arn:
            vc["rerankingConfiguration"] = {
                "type": "BEDROCK_RERANKING_MODEL",
                "bedrockRerankingConfiguration": {
                    "modelConfiguration": {"modelArn": self.cfg.rerank_model_arn},
                    "numberOfRerankedResults": min(n, 25)}}
        return vc

    def search(self, query, n=None, cfg=None, filters=None):
        """Retrieve chunks. `filters` uses the KB metadata filter grammar, e.g.

            {"equals": {"key": "source", "value": "filings"}}
            {"andAll": [{"equals": {"key": "tenant", "value": "acme"}},
                        {"greaterThan": {"key": "published_ts", "value": 1704067200}}]}

        Push the ACL predicate in here, not into a post-filter on the results --
        the whole permission-aware retrieval argument applies to a managed KB
        exactly as it does to your own index.
        """
        n = n or self.cfg.number_of_results
        resp = self.client.retrieve(
            knowledgeBaseId=self.cfg.knowledge_base_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={"vectorSearchConfiguration":
                                    self._vector_config(n, filters)})
        hits = []
        for i, r in enumerate(resp.get("retrievalResults", []), 1):
            meta = r.get("metadata", {}) or {}
            loc = r.get("location", {}) or {}
            uri = (loc.get("s3Location", {}) or {}).get("uri", "") or str(loc)
            hits.append(Hit(
                chunk_id=meta.get("x-amz-bedrock-kb-chunk-id", f"{uri}#{i}"),
                score=float(r.get("score", 0.0)), rank=i, method=self.method,
                doc_id=meta.get("x-amz-bedrock-kb-source-uri", uri),
                text=(r.get("content", {}) or {}).get("text", ""),
                title=str(meta.get("title", uri.rsplit("/", 1)[-1])),
                source=str(meta.get("source", "bedrock-kb")),
                published=str(meta.get("published", "")),
                heading=str(meta.get("heading", "")), ordinal=i - 1,
                acl=tuple(meta.get("acl", ()) or ())))
        return hits

    def retrieve_and_generate(self, query, prompt_template=None, filters=None):
        """The managed end-to-end path. Returns text plus its citations."""
        kb = {
            "knowledgeBaseId": self.cfg.knowledge_base_id,
            "modelArn": self.cfg.model_id,
            "retrievalConfiguration": {"vectorSearchConfiguration":
                                       self._vector_config(self.cfg.number_of_results, filters)},
        }
        if prompt_template:
            kb["generationConfiguration"] = {
                "promptTemplate": {"textPromptTemplate": prompt_template}}
        if self.cfg.guardrail_id:
            kb.setdefault("generationConfiguration", {})["guardrailConfiguration"] = {
                "guardrailId": self.cfg.guardrail_id,
                "guardrailVersion": self.cfg.guardrail_version or "DRAFT"}
        resp = self.client.retrieve_and_generate(
            input={"text": query},
            retrieveAndGenerateConfiguration={"type": "KNOWLEDGE_BASE",
                                              "knowledgeBaseConfiguration": kb})
        cites = []
        for c in resp.get("citations", []):
            for ref in c.get("retrievedReferences", []):
                cites.append({
                    "text": (ref.get("content", {}) or {}).get("text", "")[:200],
                    "uri": ((ref.get("location", {}) or {})
                            .get("s3Location", {}) or {}).get("uri", ""),
                    "metadata": ref.get("metadata", {})})
        return {"answer": resp["output"]["text"], "citations": cites,
                "session_id": resp.get("sessionId")}


# The mapping a learner needs when they move this off a laptop.
LOCAL_TO_AWS = [
    ("Chunking (raglab.chunking)", "Knowledge Base chunking strategy",
     "FIXED_SIZE / HIERARCHICAL / SEMANTIC / NONE, set on the data source",
     "HIERARCHICAL is parent-document retrieval; NONE means you chunk upstream"),
    ("SQLite FTS5 lexical index", "OpenSearch Serverless / Aurora pgvector",
     "the KB's vector store also carries the lexical leg when search type is HYBRID",
     "you no longer tune BM25 directly — measure before assuming it is equivalent"),
    ("InMemoryIndex vector table", "Knowledge Base vector store",
     "OpenSearch Serverless, Aurora PostgreSQL, Pinecone, Redis, MongoDB Atlas",
     "the choice is mostly an ops and residency decision, as the deck's matrix says"),
    ("LsaEmbedder", "amazon.titan-embed-text-v2:0 or cohere.embed-*",
     "set on the KB at creation", "changing it is a full re-ingest, exactly as the deck warns"),
    ("ProxyCrossEncoder", "Bedrock rerank (amazon.rerank-v1:0, cohere.rerank-v3-5:0)",
     "rerankingConfiguration on the retrieve call", "priced per document reranked"),
    ("build_prompt + ExtractiveGenerator",
     "retrieve_and_generate, or Converse with your own prompt",
     "promptTemplate overrides the default packing",
     "keep your own packing if citations matter — you cannot debug what you did not assemble"),
    ("ACL pre-filter (acl_groups)", "retrievalConfiguration filter",
     "metadata filters evaluated inside the search",
     "same rule: pre-filter, never post-filter"),
    ("HeuristicJudge", "Converse with a judge model, or Bedrock Evaluations",
     "pin the model and rubric version", "self-preference: do not judge with the generator"),
    ("TraceStore", "CloudWatch / model invocation logging + your own store",
     "enable invocation logging on the account",
     "retrieved text in traces inherits the corpus's compliance boundary"),
]
