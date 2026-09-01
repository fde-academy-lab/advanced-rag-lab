"""Where a learner is on the pathway.

Progress is a file in the repository, not a hidden dotfile, and that is deliberate: on this
pathway a completed unit is a commit, so progress belongs in the same place as the work. It is
also what makes the GitHub Action able to grade a pull request.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from .registry import ROOT

FILE = ROOT / "attempts" / "progress.json"


def load() -> dict:
    if FILE.exists():
        try:
            return json.loads(FILE.read_text())
        except json.JSONDecodeError:
            return {"units": {}}
    return {"units": {}}


def save(data: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def record(uid: str, passed: bool, seconds: float) -> dict:
    data = load()
    entry = data["units"].setdefault(uid, {"attempts": 0, "passed": False, "seconds": []})
    entry["attempts"] += 1
    entry["seconds"].append(round(seconds, 1))
    if passed:
        entry["passed"] = True
        entry.setdefault("passed_at", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    save(data)
    return data


def completed() -> set[str]:
    return {uid for uid, e in load().get("units", {}).items() if e.get("passed")}
