#!/usr/bin/env python3
"""Checks for C1 · Find the five characters that cost two thirds of the bill.

The simulator is the unit. It replays 200 requests through a cache that reuses the longest
byte-identical prefix, and reports two numbers that only both clear when the volatile fields are
after the barrier and the stable ones are before it:

    cache_hit_rate         >= 0.6500    deleting the timestamp also clears this
    prefix_tokens_billed   <=  260      deleting the timestamp does not clear this

That pair is the whole design. One bar can be satisfied by a workaround; two cannot, and the
second one is what makes "did you fix the cause" a graded question rather than a code-review
opinion.
"""
from __future__ import annotations

import datetime as dt
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from labsim.checkkit import Checker, emit, load_solution, run  # noqa: E402

# The cache is partitioned by tenant. `tenant_id` is therefore stable *within* any one cache,
# which is the distinction hint 4 is about and the reason moving it is a mistake.
CACHE_KEY_INCLUDES = ("tenant_id",)

TENANTS = ("acme-eu", "acme-us")
ROLES = ("analyst", "counsel", "sre")
QUESTIONS = [
    "Which region did the ingest lag originate in?",
    "Who approved the rollback for PagerDuty-4471?",
    "What was the resolution time for the shard rebalance incident?",
    "Did the backpressure alert fire before or after the deploy?",
]
CHUNK_POOL = [
    "The ingest workers in ap-southeast-2 reported kafka-lag above threshold at 04:12 UTC.",
    "Rollback RB-118 was executed by the on-call SRE; the approver field was left blank.",
    "Shard rebalance completed after 41 minutes, with backpressure clearing at 05:03 UTC.",
    "The deploy that preceded the incident shipped at 03:58 UTC on the ingest service.",
    "Halden Systems acquired Tessera Analytics in March; data migration is still in progress.",
]


def approx_tokens(text: str) -> int:
    return max(1, round(len(text.split()) * 1.3))


def trace(n: int = 200, seed: int = 17):
    rng = random.Random(seed)
    base = dt.datetime(2026, 9, 1, 9, 0, 0)
    for i in range(n):
        yield {
            "question": rng.choice(QUESTIONS),
            "chunks": rng.sample(CHUNK_POOL, 3),
            "now": base + dt.timedelta(seconds=17 * i),
            "tenant_id": rng.choice(TENANTS),
            "user_role": rng.choice(ROLES),
        }


def common_prefix(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def simulate(assemble) -> dict:
    """Replay the trace through a per-tenant cache of byte-identical prefixes.

    `cache_hit_rate` is the share of each prompt's tokens served from cache, averaged over the
    trace — not the share of requests that hit something. A request whose first forty tokens
    match and whose next four hundred do not is a "hit" under the second definition and is
    almost entirely unbilled savings under it, which is how a cache dashboard reads 90% while
    the invoice does not move.
    """
    seen: dict[str, list[str]] = {t: [] for t in TENANTS}
    cached_share, billed = [], []
    for req in trace():
        prompt = assemble(req["question"], req["chunks"], now=req["now"],
                          tenant_id=req["tenant_id"], user_role=req["user_role"])
        partition = seen[req["tenant_id"]]
        best = max((common_prefix(prompt, old) for old in partition), default=0)
        total = approx_tokens(prompt)
        hit = approx_tokens(prompt[:best]) if best else 0
        cached_share.append(hit / total)
        billed.append(total - hit)
        partition.append(prompt)
        if len(partition) > 24:
            partition.pop(0)
    return {"cache_hit_rate": sum(cached_share) / len(cached_share),
            "prefix_tokens_billed": sum(billed) / len(billed)}


def main(attempt: str) -> int:
    mod = load_solution(attempt, required=("assemble", "DIAGNOSIS"))
    c = Checker()

    sample = {"question": "Which region did the ingest lag originate in?",
              "chunks": CHUNK_POOL[:3], "now": dt.datetime(2026, 9, 1, 9, 0, 0),
              "tenant_id": "acme-eu", "user_role": "analyst"}
    try:
        prompt = mod.assemble(sample["question"], sample["chunks"], now=sample["now"],
                              tenant_id=sample["tenant_id"], user_role=sample["user_role"])
    except Exception as exc:  # noqa: BLE001
        c("assemble runs", False, f"{type(exc).__name__}: {exc}")
        return emit({}, c)

    if not c("assemble returns a string", isinstance(prompt, str)):
        return emit({}, c)

    # --------------------------------------------------------------- nothing deleted
    c("the evidence is still in the prompt", all(ch in prompt for ch in sample["chunks"]))
    c("the question is still in the prompt", sample["question"] in prompt)
    c("the system prompt survives", "incident assistant" in prompt)
    c("the instructions survive", "supporting citations" in prompt)
    c("the few-shot examples survive", "ap-southeast-2. [2]" in prompt)
    c("the 'as of when' feature was not deleted to fix a cost bug",
      "2026-09-01T09:00:00" in prompt,
      "the timestamp is gone. Users ask 'as of when?' — that feature exists for a reason, and "
      "removing it makes the cache hit and the product worse")
    c("the requester role was not deleted either", "analyst" in prompt)
    c("the tenant is still scoped", "acme-eu" in prompt)

    # --------------------------------------------------------------- the diagnosis
    text = str(getattr(mod, "DIAGNOSIS", "") or "")
    if not c("DIAGNOSIS is written", len(text.split()) >= 25,
             f"{len(text.split())} words. Name the block, the field, and the mechanism"):
        return emit({}, c)
    low = text.lower()
    # Deliberately not a bare `now`: "the bill should now match" is prose, and a check that
    # accepts it is a check that accepts the symptom restated.
    c("the diagnosis names the field, not the symptom",
      bool(re.search(r"timestamp|current time|isoformat|\bclock\b"
                     r"|\btime\b[^.]{0,24}(field|block|line|prompt)"
                     r"|(field|block|line)[^.]{0,24}\btime\b", low)),
      "'the cache is not hitting' is the observation you started with. Which field, in which "
      "block?")
    c("the diagnosis explains why position matters",
      bool(re.search(r"prefix|byte|everything after|invalidat|before|position|order|first",
                     low)),
      "a volatile field does not make its own block uncacheable — it makes everything after "
      "it uncacheable. That is the sentence")
    c("the diagnosis accounts for the tenant field",
      bool(re.search(r"tenant", low)),
      "tenant_id changes across the trace and is stable within its own cache partition. A "
      "diagnosis that does not mention it has not been checked against CACHE_KEY_INCLUDES")

    # --------------------------------------------------------------- the measurement
    c.note("Replaying 200 requests through the cache...")
    result = simulate(mod.assemble)
    c.note(f"cache_hit_rate {result['cache_hit_rate']:.4f} · "
           f"prefix_tokens_billed {result['prefix_tokens_billed']:.1f}")
    c("the simulation completes", True)
    return emit(result, c)


if __name__ == "__main__":
    sys.exit(run(main))
