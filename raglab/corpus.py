"""
A MultiHop-RAG-shaped corpus that runs offline, plus the evaluation set that
scores against it.

Why synthesise instead of downloading MultiHop-RAG (Tang & Yang, COLM 2024)?
Three reasons, and they are the same reasons you build a domain eval set
rather than reaching for a public benchmark:

  1. One click. A notebook that needs a 200 MB download is not a notebook a
     cohort can run in a room with hotel wifi.
  2. Gold labels that are *true by construction*. Every question here is
     generated from a fact graph, so the evidence list is exact rather than
     annotated-and-hopefully-right. That lets us measure retrieval without an
     annotation-error floor underneath the numbers.
  3. Deliberate failure modes. A public benchmark contains whatever failures it
     happens to contain. This corpus is built so that every failure signature
     in the deck actually fires:

        lexical gap        support KB says "retry delay", the incident report
                           says "backoff interval" -- no shared term
        identifier miss    ERR_CONN_RESET appears literally in exactly one
                           document; dense-only retrieval slides past it
        missing hop        the second hop is phrased so it scores poorly
                           against the original question
        distractor         near-identical market-commentary articles that
        dominance          mention the same entities and decide nothing
        temporal           several similar events, distinguishable only by date
        null questions     plausible questions the corpus cannot answer
        ACL leakage        documents restricted to groups, with two personas

The schema mirrors MultiHop-RAG's record shape (query / answer / question_type
/ evidence_list) so everything you learn here transfers to the real dataset --
and `load_multihop_rag()` swaps it in if you have the file locally.
"""
from __future__ import annotations

import hashlib
import random
import re
from dataclasses import dataclass, field

SEED = 20260831

SOURCES = ("newswire", "filings", "techblog", "transcript", "support_kb", "incident")

# Access groups. Two personas in the notebooks map onto these.
G_PUBLIC = "public"
G_FINANCE = "finance"
G_SUPPORT = "support"
G_LEGAL = "legal"


# ------------------------------------------------------------------ types ----
@dataclass(frozen=True)
class Passage:
    heading: str
    text: str
    facts: tuple = ()
    anchor: str = ""          # distinctive substring; survives every chunking strategy


@dataclass
class Document:
    doc_id: str
    title: str
    source: str
    published: str
    passages: tuple
    acl: tuple = (G_PUBLIC,)
    tenant: str = "acme"
    entities: tuple = ()

    @property
    def body(self) -> str:
        return "\n\n".join(f"## {p.heading}\n{p.text}" for p in self.passages)

    @property
    def content_hash(self) -> str:
        return hashlib.sha1(self.body.encode()).hexdigest()[:12]


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    ordinal: int
    n_chunks: int
    text: str
    title: str
    source: str
    published: str
    acl: tuple
    tenant: str
    heading: str = ""
    content_hash: str = ""

    @property
    def label(self) -> str:
        return f"{self.doc_id}#{self.ordinal}"


@dataclass
class EvalQuestion:
    qid: str
    query: str
    answer: str
    question_type: str          # inference | comparison | temporal | null
    evidence_anchors: tuple     # distinctive strings that must be retrieved
    evidence_doc_ids: tuple
    hops: int
    difficulty: str = "medium"
    persona: str = "analyst"
    tenant: str = "acme"
    slice: str = "dev"          # dev | frozen
    note: str = ""

    def as_record(self) -> dict:
        """The MultiHop-RAG record shape, for schema compatibility."""
        return {
            "query": self.query,
            "answer": self.answer,
            "question_type": self.question_type,
            "evidence_list": list(self.evidence_anchors),
        }


@dataclass
class CorpusBundle:
    documents: list
    questions: list
    facts: dict
    personas: dict = field(default_factory=dict)

    def by_id(self, doc_id):
        return next(d for d in self.documents if d.doc_id == doc_id)

    def stats(self):
        from collections import Counter

        return {
            "documents": len(self.documents),
            "words": sum(len(d.body.split()) for d in self.documents),
            "sources": dict(Counter(d.source for d in self.documents)),
            "questions": len(self.questions),
            "question_types": dict(Counter(q.question_type for q in self.questions)),
            "hops": dict(Counter(q.hops for q in self.questions)),
            "public_docs": sum(1 for d in self.documents if G_PUBLIC in d.acl),
            "restricted_docs": sum(1 for d in self.documents if G_PUBLIC not in d.acl),
        }


# ------------------------------------------------------------- fact graph ----
# The corpus is generated from a fact graph rather than written by hand. Two
# reasons: gold evidence is then true by construction rather than annotated,
# and the corpus can be scaled to the size the lesson needs. N=100 candidates
# out of 200 chunks is not a first stage, it is a full scan wearing a costume --
# so the default corpus is large enough that retrieval has to actually retrieve.

ORG_SEED = [
    ("northwind", "Northwind Systems", "cloud infrastructure", "Dara Velasquez", "Seattle"),
    ("halcyon", "Halcyon Robotics", "warehouse robotics", "Peter Osei", "Rotterdam"),
    ("veridian", "Veridian Health", "clinical data", "Amara Lindqvist", "Uppsala"),
    ("cobalt", "Cobalt Grid", "grid software", "Jonas Mbeki", "Nairobi"),
    ("perihelion", "Perihelion Labs", "advanced materials", "Renata Sokolov", "Kraków"),
    ("tessera", "Tessera Analytics", "business intelligence", "Ivan Duarte", "Lisbon"),
    ("ardent", "Ardent Freight", "logistics", "Nadia Farrow", "Memphis"),
    ("meridian", "Meridian Foods", "packaged foods", "Sam Okonkwo", "Lagos"),
    ("solstice", "Solstice Energy", "renewable energy", "Yuki Tanaka", "Osaka"),
    ("basalt", "Basalt Semiconductors", "semiconductors", "Elias Brandt", "Dresden"),
    ("kestrel", "Kestrel Payments", "payments", "Priya Raghavan", "Singapore"),
    ("orrery", "Orrery Software", "developer tools", "Tomas Lindgren", "Tallinn"),
    ("beacon", "Beacon Telecom", "telecommunications", "Fatima Zahra", "Casablanca"),
    ("harrow", "Harrow Insurance", "insurance", "Colin Achebe", "Dublin"),
    ("lumen", "Lumen Diagnostics", "medical devices", "Sofia Marchetti", "Milan"),
    ("thicket", "Thicket Agriculture", "agritech", "Marcus Oyelaran", "Curitiba"),
    ("pallas", "Pallas Aerospace", "aerospace", "Iris Nakamura", "Toulouse"),
    ("cinder", "Cinder Security", "cybersecurity", "Anton Petrov", "Vilnius"),
    ("quill", "Quill Media", "digital media", "Rosa Delgado", "Bogotá"),
    ("verity", "Verity Legal Tech", "legal technology", "Nkechi Balogun", "Accra"),
    ("standwell", "Standwell Retail", "retail", "Henrik Sørensen", "Aarhus"),
    ("apex", "Apex Chemicals", "specialty chemicals", "Leila Farsi", "Basel"),
    ("windward", "Windward Shipping", "maritime", "Kostas Andreou", "Piraeus"),
    ("tallow", "Tallow Materials", "industrial materials", "Grace Mwangi", "Kigali"),
]
ORGS = ORG_SEED
ORG = {o[0]: dict(zip(("slug", "name", "sector", "ceo", "hq"), o)) for o in ORG_SEED}
SLUGS = [o[0] for o in ORG_SEED]

QUARTERS = ["Q3 2023", "Q4 2023", "Q1 2024", "Q2 2024", "Q3 2024", "Q4 2024"]
QUARTER_DATE = {"Q3 2023": "2023-10-", "Q4 2023": "2024-02-", "Q1 2024": "2024-04-",
                "Q2 2024": "2024-07-", "Q3 2024": "2024-10-", "Q4 2024": "2025-02-"}

ACQUISITIONS = [
    ("northwind", "tessera", "2023-08-14", "$1.4 billion",
     "to fold analytics into its cloud console"),
    ("basalt", "perihelion", "2024-03-05", "$620 million",
     "to secure a substrate supply chain"),
    ("ardent", "meridian", "2024-06-20", "$310 million", "to acquire cold-chain capacity"),
    ("solstice", "cobalt", "2024-09-11", "$880 million",
     "to pair generation assets with grid software"),
    ("kestrel", "verity", "2023-11-28", "$240 million",
     "to add contract automation to its merchant tooling"),
    ("cinder", "orrery", "2024-01-16", "$455 million",
     "to move security checks earlier in the developer workflow"),
    ("beacon", "quill", "2024-05-07", "$1.1 billion",
     "to bundle media distribution with connectivity"),
    ("apex", "tallow", "2024-11-19", "$390 million",
     "to internalise a raw-materials dependency"),
]

EXEC_CHANGES = [
    ("northwind", "Dara Velasquez", "2022-11-02", "Hollis Bergman"),
    ("basalt", "Elias Brandt", "2023-02-15", "Wilhelmina Roth"),
    ("ardent", "Nadia Farrow", "2023-05-30", "Clay Ruthven"),
    ("solstice", "Yuki Tanaka", "2021-07-19", "Hideo Kurosawa"),
    ("veridian", "Amara Lindqvist", "2024-01-08", "Gustav Palme"),
    ("kestrel", "Priya Raghavan", "2023-09-04", "Wei-Lin Chua"),
    ("cinder", "Anton Petrov", "2024-02-26", "Dagmar Ellis"),
    ("beacon", "Fatima Zahra", "2022-06-13", "Youssef Kably"),
    ("apex", "Leila Farsi", "2023-12-11", "Bertrand Michel"),
    ("harrow", "Colin Achebe", "2024-03-18", "Sinead Gallagher"),
    ("pallas", "Iris Nakamura", "2023-04-24", "Étienne Roux"),
    ("lumen", "Sofia Marchetti", "2024-07-15", "Paolo Ventura"),
]

INCIDENTS = [
    ("northwind", "Meridian Object Store", "2024-03-19", "ERR_CONN_RESET",
     "a connection pool exhausted during a regional failover",
     "raise the backoff interval and cap concurrent sessions"),
    ("cobalt", "Grid Sentinel 2", "2024-01-27", "ERR_QUOTA_EXCEEDED",
     "a telemetry burst exceeded the per-tenant ingest quota",
     "request a quota increase and shard the telemetry writer"),
    ("veridian", "Cohort Explorer", "2024-06-02", "ERR_TLS_HANDSHAKE",
     "an expired intermediate certificate on the ingest gateway",
     "rotate the certificate chain and pin the intermediate"),
    ("northwind", "Northwind Query Router", "2024-11-12", "ERR_ROUTE_STALE",
     "a routing table that was not invalidated after a region drain",
     "force a routing refresh and shorten the table's lease"),
    ("ardent", "Coldline Tracker", "2024-12-04", "ERR_PAYLOAD_TOO_LARGE",
     "a firmware update that doubled the telemetry frame size",
     "cap the frame size and enable client-side batching"),
    ("basalt", "Anvil 5 substrate", "2024-08-30", "ERR_BATCH_REJECTED",
     "a lot-tracking mismatch between the fab and the ERP feed",
     "reconcile lot identifiers before submission and retry the batch"),
    ("kestrel", "Kestrel Settlement API", "2024-04-09", "ERR_IDEMPOTENCY_CONFLICT",
     "a client retrying with a reused idempotency key after a timeout",
     "generate a fresh key per attempt and widen the retry delay"),
    ("cinder", "Cinder Policy Engine", "2024-09-23", "ERR_POLICY_TIMEOUT",
     "a regular expression in a customer policy that backtracked catastrophically",
     "bound policy evaluation time and reject pathological patterns at upload"),
    ("beacon", "Beacon Edge Cache", "2024-02-05", "ERR_ORIGIN_UNREACHABLE",
     "a BGP withdrawal that isolated two origin regions",
     "add a third origin region and shorten health-check intervals"),
    ("lumen", "Lumen Reader Cloud", "2024-10-17", "ERR_CALIBRATION_DRIFT",
     "a firmware release that shipped an uncalibrated reference curve",
     "roll back the firmware and re-run the calibration sweep"),
]

LAUNCHES = [
    ("northwind", "Meridian Object Store", "2024-02-12", "storage"),
    ("northwind", "Northwind Query Router", "2024-09-17", "cloud infrastructure"),
    ("halcyon", "Kestrel Picking Arm", "2024-04-18", "robotics"),
    ("veridian", "Cohort Explorer", "2024-05-09", "analytics"),
    ("basalt", "Anvil 5 substrate", "2024-07-03", "materials"),
    ("cobalt", "Grid Sentinel 2", "2023-11-14", "monitoring"),
    ("solstice", "Helios Forecast", "2024-08-21", "forecasting"),
    ("tessera", "Lattice Semantic Layer", "2023-09-27", "analytics"),
    ("ardent", "Coldline Tracker", "2024-10-08", "logistics"),
    ("perihelion", "Substrate Bond Kit", "2023-07-19", "materials"),
    ("kestrel", "Kestrel Settlement API", "2023-12-06", "payments"),
    ("orrery", "Orrery Build Cache", "2024-03-26", "developer tools"),
    ("cinder", "Cinder Policy Engine", "2024-01-30", "cybersecurity"),
    ("beacon", "Beacon Edge Cache", "2023-10-11", "telecommunications"),
    ("lumen", "Lumen Reader Cloud", "2024-06-25", "medical devices"),
    ("harrow", "Harrow Claims Copilot", "2024-11-05", "insurance"),
    ("pallas", "Pallas Flight Deck", "2024-05-21", "aerospace"),
    ("thicket", "Thicket Yield Model", "2024-08-07", "agritech"),
    ("verity", "Verity Clause Library", "2023-08-29", "legal technology"),
    ("apex", "Apex Reactor Monitor", "2024-12-10", "specialty chemicals"),
]

FUNDING = [
    ("halcyon", "Series D", "$240 million", "2024-05-22", "Ostrava Ventures"),
    ("perihelion", "Series C", "$95 million", "2023-06-13", "Kaleidos Capital"),
    ("cobalt", "Series B", "$61 million", "2023-03-28", "Ostrava Ventures"),
    ("veridian", "Series E", "$180 million", "2024-02-20", "Northbank Growth"),
    ("tessera", "Series C", "$74 million", "2023-01-17", "Kaleidos Capital"),
    ("orrery", "Series B", "$48 million", "2023-05-09", "Fenwick Lane Partners"),
    ("cinder", "Series D", "$210 million", "2024-04-03", "Northbank Growth"),
    ("verity", "Series A", "$22 million", "2023-02-14", "Fenwick Lane Partners"),
    ("thicket", "Series C", "$118 million", "2024-07-11", "Ostrava Ventures"),
    ("lumen", "Series D", "$155 million", "2024-09-05", "Kaleidos Capital"),
    ("quill", "Series B", "$37 million", "2023-04-20", "Fenwick Lane Partners"),
    ("windward", "Series B", "$66 million", "2024-10-29", "Northbank Growth"),
]

REGULATORY = [
    ("northwind", "the competition authority", "2023-10-03",
     "cleared the transaction subject to a data-portability undertaking"),
    ("basalt", "the export control office", "2024-04-22",
     "granted a licence covering substrate shipments to two named jurisdictions"),
    ("beacon", "the telecommunications regulator", "2024-06-14",
     "approved the media transaction with a spectrum-divestment condition"),
    ("kestrel", "the financial conduct authority", "2024-01-09",
     "confirmed no change of control notification was required"),
    ("veridian", "the data protection authority", "2024-08-19",
     "accepted the revised cross-border transfer mechanism"),
    ("apex", "the environment agency", "2025-01-23",
     "issued an amended discharge permit covering the acquired site"),
    ("ardent", "the surface transportation board", "2024-09-30",
     "recorded the transaction as exempt from formal review"),
    ("solstice", "the energy market authority", "2024-12-12",
     "cleared the transaction after a market-power screen"),
]


def _earnings_rows():
    """Six quarters for the first sixteen organisations, generated deterministically.

    A trend plus bounded noise per organisation. Real enough that comparison
    and temporal questions have a defensible answer, synthetic enough that the
    label is exactly computable.
    """
    rng = random.Random(SEED + 7)
    rows = []
    for i, slug in enumerate(SLUGS[:16]):
        base = 180 + (i * 173) % 4200
        trend = 1.5 + ((i * 7) % 13) * 0.55        # growth level per org
        for qi, quarter in enumerate(QUARTERS):
            growth = round(max(0.4, trend + rng.uniform(-1.6, 1.9) + qi * 0.35), 1)
            base = int(base * (1 + growth / 100 * 3))
            day = 24 + (i + qi) % 5
            rows.append((slug, quarter, base, growth, QUARTER_DATE[quarter] + f"{day:02d}"))
    return rows


EARNINGS = _earnings_rows()

# --------------------------------------------------------- prose rendering ----
def _rng():
    return random.Random(SEED)



# ---------------------------------------------------------- prose padding ----
# Real documents are mostly not the sentence that answers your question. A news
# article carries background, context, caveats and boilerplate around one or two
# decisive claims, and that ratio is what makes chunking a decision at all -- on
# a corpus of 70-word documents every strategy degenerates to "return the
# document" and the whole section teaches nothing.
#
# These fillers are deliberately on-topic and deliberately undecisive. They are
# the in-document distractors a retriever has to rank past.
FILLER = [
    ("Background", "The {sector} sector has seen sustained activity over the past eighteen "
                   "months, with buyers reporting longer evaluation cycles and closer "
                   "scrutiny of vendor roadmaps. {name} has featured in several of those "
                   "evaluations, usually alongside two or three alternatives drawn from the "
                   "same shortlist. Industry observers caution that announcement volume is a "
                   "poor proxy for completed activity, and that reported figures are "
                   "frequently revised in later filings. Procurement leads interviewed for "
                   "this piece described the market as active but undisciplined, with pricing "
                   "that varies more by negotiating position than by product."),
    ("Market context", "Comparable businesses in {sector} have traded within a narrow band, "
                       "and procurement teams increasingly ask for reference customers in "
                       "their own jurisdiction before committing to a multi-year agreement. "
                       "Several buyers said they expect consolidation to continue through the "
                       "next two renewal cycles, though none would be named. {name} declined "
                       "to comment on speculation about future activity. Analysts note that "
                       "the same three or four names appear in most competitive processes, "
                       "and that displacement is rare once an incumbent is embedded in a "
                       "customer's operational workflow."),
    ("What is not known", "Neither party has published a detailed integration timeline, and "
                          "the treatment of overlapping product lines has not been described "
                          "in any public document. Questions about headcount, data residency "
                          "and customer-contract novation remain open at the time of writing, "
                          "and the parties have not committed to a date by which they will be "
                          "answered. Any figure quoted for these at this stage should be "
                          "treated as an estimate rather than a disclosure. Two people "
                          "familiar with the process said internal planning had not yet "
                          "reached the level of detail that would settle them."),
    ("Operating notes", "{name} operates from {hq} and serves customers across several "
                        "regions, with delivery capacity concentrated in a small number of "
                        "sites. Service levels, support hours and escalation paths are "
                        "documented in the customer agreement rather than in public material, "
                        "and vary by tier. Regional coverage is not uniform across product "
                        "lines, and customers in smaller markets have reported longer "
                        "response times during regional business hours. The company has said "
                        "it intends to expand coverage but has not published a schedule."),
    ("Analyst commentary", "Coverage of {sector} has been mixed. One view holds that scale "
                           "advantages accrue quickly in this market, so early share "
                           "translates into durable margin; another holds that switching "
                           "costs are low enough that share is contestable at each renewal, "
                           "and that reported growth reflects budget cycles rather than "
                           "competitive position. Both views have been argued about {name} "
                           "without resolution, and neither side has produced evidence the "
                           "other accepts. The disagreement is not narrowing."),
    ("Boilerplate", "This material is provided for information only and does not constitute "
                    "advice of any kind. Figures are as reported by the parties and have not "
                    "been independently verified. Forward-looking statements involve known "
                    "and unknown risks and uncertainties, and actual outcomes may differ "
                    "materially from those described. Readers should not place undue reliance "
                    "on any statement that describes future intentions, and should consult "
                    "the underlying filings where those are available. No part of this "
                    "material is directed at any person in a jurisdiction where publication "
                    "would be unlawful."),
]


def _pad(doc: Document, rng, n=3) -> Document:
    """Surround the decisive passages with realistic, undecisive prose.

    Fillers carry no facts, so they can never be gold evidence -- but they are
    topically close enough to compete for a slot, which is exactly their job.
    """
    org = None
    for slug, meta in ORG.items():
        if meta["name"] in doc.entities or meta["name"] in doc.title:
            org = meta
            break
    org = org or {"name": doc.title[:40], "sector": "the sector", "hq": "its home market"}
    picks = rng.sample(FILLER, min(n, len(FILLER)))
    extra = tuple(Passage(head, body.format(name=org["name"], sector=org["sector"],
                                            hq=org["hq"]), (), "")
                  for head, body in picks)
    # Decisive passages first, then filler -- but not always, so position is not a
    # free signal a retriever can exploit.
    passages = doc.passages + extra if rng.random() < 0.6 else extra[:1] + doc.passages + extra[1:]
    return Document(doc.doc_id, doc.title, doc.source, doc.published, passages,
                    doc.acl, doc.tenant, doc.entities)


def _acq_docs(rng):
    docs = []
    for i, (acq, tgt, date, amount, why) in enumerate(ACQUISITIONS):
        A, T = ORG[acq], ORG[tgt]
        fid = f"acq:{acq}:{tgt}"
        year = date[:4]

        # Newswire: uses the word "acquisition". Names both parties in one sentence.
        anchor_nw = f"{A['name']} completed its acquisition of {T['name']}"
        docs.append(Document(
            doc_id=f"nw-{8800 + i}",
            title=f"{A['name']} completes acquisition of {T['name']}",
            source="newswire", published=date,
            entities=(A["name"], T["name"]),
            passages=(
                Passage("Transaction", (
                    f"{anchor_nw} on {date}, ending a process the two companies opened earlier "
                    f"in {year}. The consideration was reported at {amount}. "
                    f"{A['name']} said the deal was struck {why}."), (fid,), anchor_nw),
                Passage("Context", (
                    f"{T['name']} operates in {T['sector']} and is headquartered in {T['hq']}. "
                    f"{A['name']}, based in {A['hq']}, said the target would continue to operate "
                    f"under its own brand through the end of {year}."), (fid,)),
                Passage("Reaction", (
                    f"Analysts covering {A['sector']} described the price as full but defensible. "
                    f"Two competitors declined to comment on the transaction."), ()),
            )))

        # Filing: never says "acquisition" -- says "purchase" and "the transaction".
        anchor_fl = f"{T['name']} was the subject of the purchase agreement"
        docs.append(Document(
            doc_id=f"fl-{2200 + i}",
            title=f"{T['name']} — notice of purchase agreement",
            source="filings",
            published=(date[:-2] + f"{int(date[-2:]) + 1:02d}"),
            entities=(T["name"], A["name"]),
            acl=(G_PUBLIC, G_FINANCE),
            passages=(
                Passage("Notice", (
                    f"{anchor_fl} disclosed on the preceding day. The purchaser is identified in "
                    f"the agreement as the counterparty of record. Consideration of {amount} was "
                    f"payable in cash and stock."), (fid,), anchor_fl),
                Passage("Undertakings", (
                    "The parties undertook to maintain separate customer data stores until "
                    "integration review concludes. No employee-retention payments above the "
                    "disclosure threshold were recorded."), ()),
            )))
    return docs


def _exec_docs(rng):
    docs = []
    for i, (org, person, date, prev) in enumerate(EXEC_CHANGES):
        O = ORG[org]
        role = "chief executive"
        fid = f"ceo:{org}"
        # Deliberately does NOT repeat the acquisition vocabulary: this is the
        # second hop that a query about an acquisition will not surface directly.
        anchor = f"{person} was appointed {role} of {O['name']}"
        docs.append(Document(
            doc_id=f"nw-{8900 + i}",
            title=f"{O['name']} names {person} as {role}",
            source="newswire", published=date,
            entities=(O["name"], person),
            passages=(
                Passage("Appointment", (
                    f"{anchor} with effect from {date}, succeeding {prev}. "
                    f"{person} had led the {O['sector']} division for the previous four years."),
                    (fid,), anchor),
                Passage("Board comment", (
                    f"The board said the appointment reflected continuity rather than a change of "
                    f"strategy. {O['name']} is headquartered in {O['hq']}."), ()),
            )))
    return docs


def _earnings_docs(rng):
    docs = []
    for i, (org, quarter, rev, growth, date) in enumerate(EARNINGS):
        O = ORG[org]
        fid = f"earn:{org}:{quarter}"
        anchor = f"{O['name']} reported revenue of ${rev} million for {quarter}"
        docs.append(Document(
            doc_id=f"fl-{2300 + i}",
            title=f"{O['name']} {quarter} results",
            source="filings", published=date,
            entities=(O["name"],), acl=(G_PUBLIC, G_FINANCE),
            passages=(
                Passage("Results", (
                    f"{anchor}, an increase of {growth:.1f}% against the same quarter a year "
                    f"earlier. Gross margin was broadly unchanged."), (fid,), anchor),
                Passage("Outlook", (
                    f"Management reiterated full-year guidance and pointed to demand in "
                    f"{O['sector']} as the main driver. No change was made to capital "
                    f"expenditure plans."), ()),
            )))
        # A transcript that paraphrases the same number without the word "revenue".
        anchor_t = f"top-line expansion of {growth:.1f}% in the quarter"
        docs.append(Document(
            doc_id=f"tr-{4400 + i}",
            title=f"{O['name']} {quarter} earnings call — prepared remarks",
            source="transcript",
            published=(date[:-2] + f"{min(28, int(date[-2:]) + 1):02d}"),
            entities=(O["name"], O["ceo"]),
            passages=(
                Passage("Prepared remarks", (
                    f"{O['ceo']}: we delivered {anchor_t}, which is ahead of the plan we set out "
                    f"in January. Demand in {O['sector']} remained the strongest contributor."),
                    (fid,), anchor_t),
                Passage("Q&A", (
                    f"Asked about pricing, {O['ceo']} said the company had not changed list prices "
                    f"and did not intend to before the next review."), ()),
            )))
    return docs


def _launch_docs(rng):
    docs = []
    for i, (org, product, date, cat) in enumerate(LAUNCHES):
        O = ORG[org]
        fid = f"launch:{org}:{product}"
        anchor = f"{O['name']} released {product} on {date}"
        docs.append(Document(
            doc_id=f"tb-{6600 + i}",
            title=f"Hands on with {product}",
            source="techblog", published=date,
            entities=(O["name"], product),
            passages=(
                Passage("Availability", (
                    f"{anchor}, making it generally available in three regions. The {cat} product "
                    f"replaces an internal tool the company had run since 2021."), (fid,), anchor),
                Passage("What is new", (
                    "The release adds per-tenant quotas, a documented rate limit, and an audit "
                    "log. Configuration is declarative and versioned."), ()),
                Passage("Caveats", (
                    "Regional coverage is incomplete at launch and the migration tool does not "
                    "preserve historical access logs."), ()),
            )))
    return docs


def _incident_docs(rng):
    """The lexical-gap and identifier-miss engine.

    The incident report carries the error code and the phrase 'backoff interval'.
    The support article carries the customer-facing phrase 'retry delay' and the
    remediation steps, and never mentions the code. Answering the obvious
    question needs both, and no single retrieval method finds both well.
    """
    docs = []
    for i, (org, product, date, code, cause, fix) in enumerate(INCIDENTS):
        O = ORG[org]
        fid = f"inc:{org}:{code}"
        anchor_i = f"clients received {code} for approximately"
        docs.append(Document(
            doc_id=f"in-{7700 + i}",
            title=f"Incident report — {product} availability event",
            source="incident", published=date,
            entities=(O["name"], product, code),
            acl=(G_SUPPORT,),
            passages=(
                Passage("Summary", (
                    f"On {date}, {anchor_i} 74 minutes while connecting to {product}. "
                    f"The trigger was {cause}."), (fid,), anchor_i),
                Passage("Timeline", (
                    "Detection came from synthetic probes rather than customer reports. "
                    "Mitigation began 11 minutes after detection; full recovery followed "
                    "a staged restart of the affected fleet."), ()),
                Passage("Corrective actions", (
                    f"Engineering will {fix}. The backoff interval used by the client library "
                    f"was found to be too aggressive under failover and has been widened."),
                    (f"{fid}:fix",), "The backoff interval used by the client library"),
            )))
        anchor_kb = "increase the retry delay in your client configuration"
        docs.append(Document(
            doc_id=f"kb-{5500 + i}",
            title=f"Connection failures when using {product}",
            source="support_kb",
            published=(date[:-2] + f"{min(28, int(date[-2:]) + 3):02d}"),
            entities=(O["name"], product),
            acl=(G_PUBLIC, G_SUPPORT),
            passages=(
                Passage("Symptom", (
                    "Client applications drop long-lived sessions during a regional event and "
                    "reconnect in a tight loop, which the service treats as abusive traffic."), ()),
                Passage("Resolution", (
                    f"To resolve this, {anchor_kb} and cap the number of concurrent sessions per "
                    f"process. Customers on the managed client should upgrade to the current "
                    f"release, which sets a safer default."), (f"{fid}:fix",), anchor_kb),
            )))
    return docs


def _funding_docs(rng):
    docs = []
    for i, (org, rnd, amount, date, lead) in enumerate(FUNDING):
        O = ORG[org]
        fid = f"fund:{org}"
        anchor = f"{O['name']} raised {amount} in a {rnd} round led by {lead}"
        docs.append(Document(
            doc_id=f"nw-{9000 + i}", title=f"{O['name']} raises {amount}",
            source="newswire", published=date, entities=(O["name"], lead),
            passages=(
                Passage("Round", (
                    f"{anchor}, closing on {date}. The company said proceeds would fund "
                    f"manufacturing capacity rather than headcount."), (fid,), anchor),
                Passage("Investors", (
                    f"{lead} has now backed two companies in {O['sector']} and adjacent markets. "
                    f"Existing investors participated pro rata."), ()),
            )))
    return docs


def _regulatory_docs(rng):
    docs = []
    for i, (org, agency, date, outcome) in enumerate(REGULATORY):
        O = ORG[org]
        fid = f"reg:{org}"
        anchor = f"{agency} {outcome}"
        docs.append(Document(
            doc_id=f"fl-{2400 + i}", title=f"{O['name']} — regulatory determination",
            source="filings", published=date, entities=(O["name"],),
            acl=(G_PUBLIC, G_LEGAL),
            passages=(
                Passage("Determination", (
                    f"On {date}, {anchor}. The determination applies to {O['name']} and its "
                    f"controlled subsidiaries."), (fid,), anchor),
                Passage("Conditions", (
                    "Compliance reporting is required quarterly for two years. Failure to report "
                    "is itself a breach, independent of the underlying conduct."), ()),
            )))
    return docs


def _distractor_docs(rng, n=180):
    """Market commentary: high lexical and semantic overlap, zero decisive facts.

    These exist so that "distractor dominance" is a thing you can measure here
    rather than a thing you have to take on faith. They are also the bulk of
    the corpus, which is realistic -- in most client corpora the documents that
    answer questions are a minority of the documents that look like they might.
    """
    shapes = [
        ("Consolidation continues across {sector}", "buyers"),
        ("What the latest wave of acquisitions means for {sector} buyers", "buyers"),
        ("{sector} vendors face a demanding year", "outlook"),
        ("Funding holds up in {sector} while other sectors cool", "funding"),
        ("Quarterly results across {sector}: a mixed picture", "results"),
        ("Availability incidents and what {sector} vendors owe customers", "incidents"),
        ("Buyers are asking harder questions about data residency in {sector}", "compliance"),
        ("Margins under pressure across {sector} into the second half", "outlook"),
        ("Leadership changes ripple through {sector}", "people"),
        ("Procurement patterns are shifting in {sector}", "buyers"),
    ]
    sectors = sorted({o[2] for o in ORG_SEED})
    docs = []
    for i in range(n):
        shape, theme = shapes[i % len(shapes)]
        sector = sectors[(i // len(shapes)) % len(sectors)]
        picks = [SLUGS[(i * 3 + j * 5) % len(SLUGS)] for j in range(3)]
        names = [ORG[s]["name"] for s in dict.fromkeys(picks)]
        month = (i % 12) + 1
        year = 2023 + (i % 2)
        docs.append(Document(
            doc_id=f"tb-{6700 + i}", title=shape.format(sector=sector), source="techblog",
            published=f"{year}-{month:02d}-{(i * 3) % 27 + 1:02d}",
            entities=tuple(names),
            passages=(
                Passage("Overview", (
                    f"Activity in {sector} has continued at a pace few expected. "
                    f"{names[0]}" + (f" and {' and '.join(names[1:])}" if len(names) > 1 else "")
                    + " are mentioned regularly in buyer conversations, though the details of "
                    "any transaction are rarely confirmed at the time of writing."), ()),
                Passage("What buyers say", (
                    f"Procurement teams report that revenue growth, acquisition rumours and "
                    f"executive changes all factor into vendor selection in {sector}. None of "
                    f"these reports has been independently verified, and the {theme} picture "
                    f"remains unsettled."), ()),
                Passage("Outlook", (
                    f"Expect further announcements. Anyone quoting a specific figure for a "
                    f"transaction involving {names[0]} at this stage is speculating."), ()),
            )))
    return docs


def _glossary_docs(rng):
    """Glossaries and FAQs -- the documents that make dense retrieval possible.

    A dense encoder can only bridge two phrasings if something in the corpus
    connects them. Real corpora are full of these connectors: glossaries,
    onboarding FAQs, style guides, the paragraph in an analyst note that says
    "also known as". They are why embeddings work on enterprise text at all,
    and their absence is why a dense leg sometimes underperforms BM25 on a
    corpus nobody has curated.

    They also set up the honest version of the lexical-gap demonstration. A
    query phrased in the customer's register retrieves the glossary lexically
    and the *answer* only semantically -- so BM25 finds a definition and dense
    finds the fix.
    """
    specs = [
        ("gl-9000", "Support glossary — connection behaviour", "support",
         "The pause between reconnection attempts is governed by the retry delay setting, "
         "which engineering documentation and incident reports call the backoff interval. "
         "Lengthening that wait reduces load on a recovering service, and shortening it "
         "increases the chance a client is treated as abusive traffic."),
        ("gl-9001", "Support glossary — session limits", "support",
         "Concurrent sessions per process, connection pool size and the parallelism cap all "
         "describe the same limit. Raising it increases throughput and increases the blast "
         "radius of a failover."),
        ("gl-9002", "Support glossary — service disruption vocabulary", "support",
         "An outage, an availability event, a service disruption and an incident all refer to "
         "the same class of event. Customer communications prefer disruption; internal "
         "reports prefer incident."),
        ("gl-9003", "Editorial glossary — corporate actions", "corporate",
         "A takeover, a buyout and an acquisition describe the same transaction. Regulatory "
         "filings use the phrase purchase agreement, and newswire copy usually says completed "
         "its acquisition. Buyer, acquirer and purchaser are interchangeable."),
        ("gl-9004", "Editorial glossary — company references", "corporate",
         "Coverage refers to a business either by its registered name or by a description of "
         "what it does and where it is based, for example the cloud infrastructure company "
         "headquartered in Seattle. Both refer to the same organization."),
        ("gl-9005", "Finance glossary — growth measures", "finance",
         "Revenue growth, top-line expansion and sales increase all describe the same "
         "year-on-year measure. Faster growth and higher growth rate mean the same thing; "
         "expanded more quickly is the phrase used on earnings calls."),
        ("gl-9006", "Finance glossary — reporting vocabulary", "finance",
         "Reported revenue, sales, turnover and the top line are the same number. Brought in "
         "and generated are informal equivalents used in commentary."),
        ("gl-9007", "Editorial glossary — leadership", "corporate",
         "Chief executive, CEO, top executive and the person who runs the business all refer "
         "to the same role. An appointment, a naming and a succession describe the same event."),
        ("gl-9008", "Editorial glossary — funding rounds", "corporate",
         "The investor that led a round is also described as the lead backer or the investor "
         "that headed the financing. Round, financing and raise are interchangeable."),
        ("gl-9009", "Editorial glossary — product availability", "corporate",
         "Released, shipped, launched and became generally available describe the same event. "
         "General availability is often abbreviated to GA."),
        ("gl-9010", "Support glossary — remediation vocabulary", "support",
         "A recommended fix, a remediation, a corrective action and a resolution are the same "
         "thing. Widen, raise, lengthen and increase are used interchangeably about interval "
         "settings."),
        ("gl-9011", "Editorial glossary — timing language", "corporate",
         "Came first, preceded and happened earlier all describe ordering. Already generally "
         "available means the release date precedes the event being asked about."),
    ]
    docs = []
    for doc_id, title, kind, text in specs:
        docs.append(Document(
            doc_id=doc_id, title=title, source="support_kb" if kind == "support" else "techblog",
            published="2023-01-05", entities=(),
            passages=(
                Passage("Definitions", text, (), text[:60]),
                Passage("Usage", (
                    "Use the customer-facing term in support replies and the engineering term "
                    "in incident reports. Search should return the same documents for either."),
                    ()),
            )))
    return docs


def _restricted_docs(rng):
    """Documents only some personas may see -- the ACL demonstration set.

    Sized so the effect is visible rather than theoretical. Roughly a fifth of
    the corpus is restricted once the internal incident reports are counted,
    which is a conservative estimate of what an enterprise corpus looks like.
    """
    docs = []
    legal = [
        ("lg-3300", "Board memorandum — integration risk", "2024-03-28", "northwind",
         "The integration review identified an unresolved data-residency exposure in two "
         "regions and recommended delaying the customer-data merge."),
        ("lg-3301", "Privileged note — indemnity position", "2024-04-04", "basalt",
         "Counsel advised that the indemnity cap negotiated in the purchase agreement is "
         "materially below the exposure modelled by the finance team."),
        ("lg-3302", "Privileged note — export licence conditions", "2024-05-16", "basalt",
         "The licence conditions restrict onward transfer of substrate inventory to two "
         "named jurisdictions and require quarterly attestation."),
        ("lg-3303", "Board memorandum — cold-chain liability", "2024-07-02", "ardent",
         "Counsel flagged an unquantified liability arising from cold-chain custody transfer "
         "in the acquired contracts."),
        ("lg-3304", "Privileged note — grid software warranties", "2024-09-25", "solstice",
         "The warranty schedule inherited from the target excludes availability incidents, "
         "which counsel considers a material gap."),
    ]
    finance = [
        ("fi-3310", "Internal forecast — downside case", "2024-08-09", "solstice",
         "The downside case assumes a 6-point deterioration in attach rate and shows the "
         "company missing its full-year revenue plan by roughly 4%."),
        ("fi-3311", "Internal forecast — integration synergies", "2024-04-11", "northwind",
         "Modelled synergies from the analytics integration are 40% below the figure quoted "
         "at announcement, with most of the shortfall in cross-sell."),
        ("fi-3312", "Internal memo — pricing sensitivity", "2024-06-18", "basalt",
         "A 3% list price reduction would remove approximately half of the projected margin "
         "expansion for the following year."),
        ("fi-3313", "Internal memo — capital allocation review", "2024-10-14", "ardent",
         "The review recommends deferring two cold-chain depots until utilisation recovers "
         "above the plan threshold."),
        ("fi-3314", "Internal forecast — clinical data attach", "2024-11-20", "veridian",
         "Attach rate for the analytics module is tracking ahead of plan, which offsets a "
         "slower ramp in the core clinical product."),
    ]
    supportint = [
        ("sp-3320", "Internal runbook — failover drill findings", "2024-04-02", "northwind",
         "The drill showed client libraries reconnecting with an aggressive backoff interval, "
         "which amplified load during the recovery window."),
        ("sp-3321", "Internal runbook — telemetry shedding policy", "2024-02-14", "cobalt",
         "Under sustained burst the ingest tier sheds low-priority telemetry first; operators "
         "must confirm the shed order before raising a tenant quota."),
    ]
    for group, specs in ((G_LEGAL, legal), (G_FINANCE, finance), (G_SUPPORT, supportint)):
        for doc_id, title, date, org, text in specs:
            O = ORG[org]
            anchor = text.split(".")[0][:60]
            docs.append(Document(
                doc_id=doc_id, title=f"{O['name']} — {title}",
                source="filings" if group != G_SUPPORT else "incident",
                published=date, entities=(O["name"],), acl=(group,),
                passages=(
                    Passage("Restricted", text, (f"restricted:{doc_id}",), anchor),
                    Passage("Handling", (
                        "This document is restricted. It must not influence any customer-facing "
                        "answer produced for a user outside the named group."), ()),
                )))
    return docs


# ---------------------------------------------------------------- corpus -----
def build_corpus() -> CorpusBundle:
    rng = _rng()
    docs = []
    docs += _acq_docs(rng)
    docs += _exec_docs(rng)
    docs += _earnings_docs(rng)
    docs += _launch_docs(rng)
    docs += _incident_docs(rng)
    docs += _funding_docs(rng)
    docs += _regulatory_docs(rng)
    docs += _distractor_docs(rng)
    docs += _glossary_docs(rng)
    docs += _restricted_docs(rng)

    # Pad every document to a realistic length before anything is indexed.
    pad_rng = random.Random(SEED + 5)
    docs = [_pad(d, pad_rng, n=3 if d.source != "techblog" else 2) for d in docs]

    facts = {}
    for d in docs:
        for p in d.passages:
            for f in p.facts:
                facts.setdefault(f, []).append((d.doc_id, p.anchor or p.text[:60]))

    questions = build_eval_set(docs, facts)
    personas = {
        "analyst": (G_PUBLIC,),
        "support_engineer": (G_PUBLIC, G_SUPPORT),
        "finance_partner": (G_PUBLIC, G_FINANCE),
        "counsel": (G_PUBLIC, G_FINANCE, G_LEGAL, G_SUPPORT),
    }
    return CorpusBundle(documents=docs, questions=questions, facts=facts, personas=personas)


def _ev(facts, *fact_ids):
    """Gold evidence = the anchor strings of every passage carrying these facts."""
    anchors, doc_ids = [], []
    for f in fact_ids:
        for doc_id, anchor in facts.get(f, []):
            anchors.append(anchor)
            doc_ids.append(doc_id)
    return tuple(anchors), tuple(dict.fromkeys(doc_ids))


# Surface forms. A question that repeats the document's own wording is a
# question BM25 answers by accident, and a corpus made only of those teaches
# that lexical retrieval is all you need. Real users paraphrase, refer to
# entities by description, and use the vocabulary of their job rather than the
# vocabulary of the source. These templates put that gap back in on purpose --
# while leaving the identifier questions exact, because those are the ones
# where lexical retrieval genuinely wins.
SAY_ACQUIRER = [
    "Which organization acquired {t}?",
    "Who took over {t}?",
    "Which business ended up owning {t}?",
    "{t} was bought by which company?",
]
SAY_ACQ_CEO = [
    "Who is the chief executive of the company that acquired {t}?",
    "Who runs the business that took over {t}?",
    "Name the person leading the buyer of {t}.",
]
SAY_ACQ_TERMS = [
    "How much was paid for {t}, and where is it based?",
    "What was the consideration for {t}, and in which city does it operate?",
    "What price did the buyer of {t} pay, and where are its offices?",
]
SAY_REVENUE = [
    "What revenue did {o} report for {q}?",
    "How much did {o} bring in during {q}?",
    "What were {o}'s sales in {q}?",
    "What was the top line at {o} in {q}?",
]
SAY_GROWTH = [
    "What growth rate did {o} report for {q}?",
    "How fast did {o} expand in {q}?",
    "By what percentage did {o} improve year on year in {q}?",
]
SAY_FASTER = [
    "In {q}, which grew faster: {a} or {b}?",
    "Between {a} and {b}, who expanded more quickly in {q}?",
    "Which of {a} and {b} improved at a higher rate in {q}?",
]
SAY_BIGGER = [
    "Which reported higher revenue in {q}, {a} or {b}?",
    "Who was larger by sales in {q}, {a} or {b}?",
    "Between {a} and {b}, which had the bigger top line in {q}?",
]
SAY_FUND = [
    "Who led {o}'s {r} round?",
    "Which investor headed the {r} financing at {o}?",
    "Name the lead backer of {o}'s {r}.",
]
SAY_LAUNCH = [
    "Which product did {o} release in {m} {y}?",
    "What did {o} ship in {m} {y}?",
    "Name the {o} product that became available in {m} {y}.",
]


def _org_ref(slug, rng, allow_descriptor=True):
    """Refer to an organisation by name, or by a description that identifies it.

    A description shares no tokens with the entity name the document uses, so
    it can only be resolved semantically -- exactly the case a lexical-only
    retriever cannot handle and a dense leg can. Each organisation's sector and
    headquarters are unique in the fact graph, so the description is unambiguous.
    """
    O = ORG[slug]
    if allow_descriptor and rng.random() < 0.32:
        return rng.choice([
            f"the {O['sector']} company headquartered in {O['hq']}",
            f"the {O['hq']}-based {O['sector']} business",
        ])
    return O["name"]


def build_eval_set(docs, facts) -> list:
    """Questions generated from the fact graph, so the labels cannot be wrong.

    Types follow the deck's question-type matrix: inference (chain across
    documents), comparison (balanced evidence for two entities), temporal
    (ordering or a date window), and null (the corpus cannot answer it).
    """
    qs = []
    n = [0]
    rng = random.Random(SEED + 11)

    def say(templates, **kw):
        return templates[rng.randrange(len(templates))].format(**kw)

    def add(query, answer, qtype, fact_ids, hops, **kw):
        n[0] += 1
        anchors, doc_ids = _ev(facts, *fact_ids)
        qs.append(EvalQuestion(
            qid=f"q{n[0]:03d}", query=query, answer=answer, question_type=qtype,
            evidence_anchors=anchors, evidence_doc_ids=doc_ids, hops=hops, **kw))

    # -- inference: chain an event to an attribute named only in another doc ---
    for acq, tgt, date, amount, _ in ACQUISITIONS:
        A, T = ORG[acq], ORG[tgt]
        add(say(SAY_ACQUIRER, t=_org_ref(tgt, rng)), A["name"], "inference",
            [f"acq:{acq}:{tgt}"], 1, difficulty="easy")
        if any(e[0] == acq for e in EXEC_CHANGES):
            add(say(SAY_ACQ_CEO, t=_org_ref(tgt, rng)), A["ceo"], "inference",
                [f"acq:{acq}:{tgt}", f"ceo:{acq}"], 2, difficulty="hard",
                note="Hop 2 shares almost no vocabulary with the question.")
        add(say(SAY_ACQ_TERMS, t=T["name"]), f"{amount}; {T['hq']}", "inference",
            [f"acq:{acq}:{tgt}"], 1)

    for org, quarter, rev, growth, _ in EARNINGS:
        add(say(SAY_REVENUE, o=_org_ref(org, rng), q=quarter), f"${rev} million", "inference",
            [f"earn:{org}:{quarter}"], 1, difficulty="easy")

    # Identifier questions stay exact on purpose: this is where lexical wins.
    for org, product, date, code, cause, fix in INCIDENTS:
        O = ORG[org]
        add(f"What is the recommended fix for {code}?",
            "Widen the backoff / retry delay and cap concurrent sessions.",
            "inference", [f"inc:{org}:{code}", f"inc:{org}:{code}:fix"], 2, difficulty="hard",
            persona="support_engineer",
            note="Identifier lives in the incident report; the remediation prose lives in the "
                 "support article and never repeats the code. Lexical finds one, dense the "
                 "other, and only a hybrid finds both.")
        add(f"Which product was affected by {code} and what caused it?",
            f"{product}; {cause}", "inference", [f"inc:{org}:{code}"], 1,
            persona="support_engineer")
        add(f"After a {O['sector']} availability event, how should the pause between "
            f"reconnection attempts be lengthened?",
            "Increase the retry delay and cap concurrent sessions.", "inference",
            [f"inc:{org}:{code}:fix"], 1, persona="support_engineer", difficulty="hard",
            note="Pure lexical gap. The question says pause / reconnection attempts / "
                 "lengthened; the answer passage says retry delay / concurrent sessions / "
                 "increase. No shared term. BM25 can only reach the glossary that connects "
                 "them; the dense leg reaches the fix itself.")

    for org, rnd, amount, date, lead in FUNDING:
        add(say(SAY_FUND, o=_org_ref(org, rng), r=rnd), lead, "inference", [f"fund:{org}"], 1,
            difficulty="easy")

    # -- comparison: needs balanced evidence from two documents ---------------
    by_q = {}
    for org, quarter, rev, growth, _ in EARNINGS:
        by_q.setdefault(quarter, []).append((org, rev, growth))
    for quarter, entries in sorted(by_q.items()):
        entries = sorted(entries)
        for i in range(0, len(entries) - 1, 2):
            a, ra, ga = entries[i]
            bb, rb, gb = entries[i + 1]
            faster = ORG[a]["name"] if ga > gb else ORG[bb]["name"]
            add(say(SAY_FASTER, q=quarter, a=_org_ref(a, rng), b=_org_ref(bb, rng)), faster,
                "comparison", [f"earn:{a}:{quarter}", f"earn:{bb}:{quarter}"], 2,
                difficulty="hard",
                note="Both sides must survive packing; one entity commonly starves the other.")
            bigger = ORG[a]["name"] if ra > rb else ORG[bb]["name"]
            add(say(SAY_BIGGER, q=quarter, a=ORG[a]["name"], b=ORG[bb]["name"]), bigger,
                "comparison", [f"earn:{a}:{quarter}", f"earn:{bb}:{quarter}"], 2)

    # -- temporal: ordering, or a date window --------------------------------
    for i in range(len(ACQUISITIONS) - 1):
        a1, t1, d1, _, _ = ACQUISITIONS[i]
        a2, t2, d2, _, _ = ACQUISITIONS[i + 1]
        first = ((ORG[a1]["name"], ORG[t1]["name"], d1) if d1 < d2
                 else (ORG[a2]["name"], ORG[t2]["name"], d2))
        add(f"Which came first: {ORG[a1]['name']} taking over {ORG[t1]['name']}, or "
            f"{ORG[a2]['name']} taking over {ORG[t2]['name']}?",
            f"{first[0]}'s acquisition of {first[1]} ({first[2]}).", "temporal",
            [f"acq:{a1}:{t1}", f"acq:{a2}:{t2}"], 2, difficulty="hard")

    for org, product, date, code, cause, fix in INCIDENTS:
        launch = next((l for l in LAUNCHES if l[0] == org and l[1] == product), None)
        if not launch:
            continue
        add(f"Was {product} already generally available when the {code} outage happened?",
            f"Yes — it shipped on {launch[2]} and the incident was on {date}.",
            "temporal", [f"launch:{org}:{product}", f"inc:{org}:{code}"], 2,
            difficulty="hard", persona="support_engineer")

    for slug in SLUGS[:16]:
        rows = [e for e in EARNINGS if e[0] == slug]
        for a, bq in zip(rows, rows[1:]):
            direction = "accelerated" if bq[3] > a[3] else "slowed"
            add(f"Did growth at {_org_ref(slug, rng)} speed up or slow down between {a[1]} "
                f"and {bq[1]}?", direction, "temporal",
                [f"earn:{slug}:{a[1]}", f"earn:{slug}:{bq[1]}"], 2, difficulty="hard")

    add("Did Northwind Systems finish taking over Tessera Analytics before or after Tessera "
        "published its Q2 2024 numbers?",
        "Before — the acquisition completed on 2023-08-14; the results are from 2024.",
        "temporal", ["acq:northwind:tessera", "earn:tessera:Q2 2024"], 2, difficulty="hard")

    months = {"01": "January", "02": "February", "03": "March", "04": "April", "05": "May",
              "06": "June", "07": "July", "08": "August", "09": "September", "10": "October",
              "11": "November", "12": "December"}
    for org, product, date, cat in LAUNCHES:
        add(say(SAY_LAUNCH, o=_org_ref(org, rng), m=months[date[5:7]], y=date[:4]), product,
            "temporal", [f"launch:{org}:{product}"], 1)
    for org, quarter, rev, growth, _ in EARNINGS:
        add(say(SAY_GROWTH, o=_org_ref(org, rng), q=quarter), f"{growth:.1f}%", "temporal",
            [f"earn:{org}:{quarter}"], 1, difficulty="easy")

    # -- null: plausible, unanswerable. The cheapest thing you can add. -------
    nulls = []
    acquired = {t for _, t, _, _, _ in ACQUISITIONS}
    acquirers = {a for a, _, _, _, _ in ACQUISITIONS}
    reported = {o for o, *_ in EARNINGS}
    funded = {o for o, *_ in FUNDING}
    led = {o for o, *_ in EXEC_CHANGES}
    for slug in SLUGS:
        O = ORG[slug]
        if slug not in acquired and slug not in acquirers:
            nulls.append((f"Which organization acquired {O['name']}?",
                          f"No acquisition of {O['name']} is recorded in this corpus."))
        if slug not in reported:
            nulls.append((f"What revenue did {O['name']} report for Q2 2024?",
                          f"{O['name']} reports no results in this corpus."))
        if slug not in funded:
            nulls.append((f"Which investor led {O['name']}'s Series B?",
                          f"No {O['name']} funding round is recorded in this corpus."))
        if slug not in led:
            nulls.append((f"Who is the chief executive of {O['name']}?",
                          f"No leadership information for {O['name']} is recorded."))
    for code in ("ERR_RATE_LIMITED", "ERR_DISK_FULL", "ERR_SCHEMA_MISMATCH", "ERR_CLOCK_SKEW",
                 "ERR_LEASE_EXPIRED", "ERR_SHARD_MISSING"):
        nulls.append((f"What is the recommended fix for {code}?",
                      f"{code} does not appear in this corpus."))
    for q, a in nulls:
        add(q, a, "null", [], 0, difficulty="hard",
            note="Answering this at all is the failure; abstention is the correct behaviour.")

    # -- restricted: same question, different personas ------------------------
    add("What risk did the integration review identify for Northwind Systems?",
        "An unresolved data-residency exposure in two regions.", "inference",
        ["restricted:lg-3300"], 1, persona="counsel", difficulty="hard",
        note="Only the counsel persona may see the evidence. An analyst must abstain.")
    add("How far below the announced figure are the modelled integration synergies?",
        "About 40% below, mostly in cross-sell.", "inference",
        ["restricted:fi-3311"], 1, persona="finance_partner", difficulty="hard",
        note="Finance-only evidence. Pre-filtering must keep it out of an analyst's candidates.")
    add("What did the failover drill find about client reconnection behaviour?",
        "Client libraries reconnected with an aggressive backoff interval, amplifying load.",
        "inference", ["restricted:sp-3320"], 1, persona="support_engineer", difficulty="hard",
        note="Internal runbook. An analyst persona must abstain rather than answer from the "
             "public KB article alone.")

    # -- stratify down to a balanced, workable set ---------------------------
    # A generated set inherits its generator's proportions: this one can emit
    # 180 comparison questions simply because it has six quarters and sixteen
    # companies. Left alone, the report would average away the types that
    # actually fail. Sampling by type is the same discipline as the deck's
    # "sample documents stratified by source, age, and format".
    target = {"inference": 62, "comparison": 46, "temporal": 56, "null": 36}
    srng = random.Random(SEED + 3)
    keep, by_type = [], {}
    for q in qs:
        if q.persona != "analyst":          # persona / ACL cases are always kept
            keep.append(q)
        else:
            by_type.setdefault(q.question_type, []).append(q)
    for qtype, pool in by_type.items():
        pool = sorted(pool, key=lambda q: q.qid)
        srng.shuffle(pool)
        hard = [q for q in pool if q.hops >= 2][: target.get(qtype, 40)]
        hard_ids = {q.qid for q in hard}
        rest = [q for q in pool if q.qid not in hard_ids]
        keep.extend(hard + rest[: max(0, target.get(qtype, 40) - len(hard))])
    keep.sort(key=lambda q: q.qid)

    # -- freeze a slice that no tuning run is allowed to see ------------------
    frng = random.Random(SEED + 1)
    idx = list(range(len(keep)))
    frng.shuffle(idx)
    for i in idx[: max(1, int(0.15 * len(keep)))]:
        keep[i].slice = "frozen"
    return keep


# ----------------------------------------------------------- real dataset ----
def load_multihop_rag(corpus_path=None, questions_path=None, limit=None):
    """Swap the synthetic corpus for the real MultiHop-RAG files if present.

    The dataset ships as `corpus.json` (documents with title/body/published_at/
    source) and `MultiHopRAG.json` (query/answer/question_type/evidence_list).
    Everything downstream in these notebooks reads the same Document /
    EvalQuestion shapes, so nothing else has to change:

        bundle = load_multihop_rag("data/corpus.json", "data/MultiHopRAG.json")

    Returns None when the files are absent, which is the normal offline case.
    """
    import json
    import os

    if not corpus_path or not os.path.exists(corpus_path):
        return None
    raw_docs = json.load(open(corpus_path))
    docs = []
    for i, d in enumerate(raw_docs[: limit or len(raw_docs)]):
        body = d.get("body") or d.get("text") or ""
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()] or [body]
        docs.append(Document(
            doc_id=f"mh-{i:05d}", title=d.get("title", f"doc {i}"),
            source=d.get("source", "newswire"),
            published=(d.get("published_at") or "2023-01-01")[:10],
            entities=(),
            passages=tuple(Passage(f"part {j + 1}", p, (), p[:60])
                           for j, p in enumerate(paras))))
    questions = []
    if questions_path and os.path.exists(questions_path):
        raw_q = json.load(open(questions_path))
        for i, q in enumerate(raw_q[: limit or len(raw_q)]):
            ev = [e.get("fact", e) if isinstance(e, dict) else e
                  for e in q.get("evidence_list", [])]
            questions.append(EvalQuestion(
                qid=f"mq{i:05d}", query=q["query"], answer=str(q.get("answer", "")),
                question_type=q.get("question_type", "inference"),
                evidence_anchors=tuple(str(e)[:60] for e in ev),
                evidence_doc_ids=(), hops=max(1, len(ev))))
    return CorpusBundle(documents=docs, questions=questions, facts={})
