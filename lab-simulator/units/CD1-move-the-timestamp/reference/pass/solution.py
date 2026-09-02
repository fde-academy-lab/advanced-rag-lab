from __future__ import annotations

SYSTEM = ("You are Client Zero's incident assistant. Answer only from the evidence provided "
          "and cite every claim with the marker of the passage it came from.")
INSTRUCTIONS = ("Format: a one-line answer, then the citations, then any caveat. Prefer the "
                "most recent postmortem when two passages disagree, and say that you did.")


def assemble(question: str, evidence: list[str], now: str) -> str:
    parts = [
        SYSTEM,
        INSTRUCTIONS,
        "Evidence:\n" + "\n\n".join(evidence),
        f"Current time: {now}\nQuestion: {question}",
    ]
    return "\n\n".join(parts)
