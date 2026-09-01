"""Loading units from disk, and the pathway they form.

A unit is a directory. That is deliberate: adding one is `mkdir` plus five files, with no
central list to edit and therefore no merge conflict when two people add units in the same
week. The pathway is derived from prerequisites rather than declared, so it cannot drift from
what the units actually say.
"""
from __future__ import annotations

import functools
from pathlib import Path

from .model import Bar, Unit

ROOT = Path(__file__).resolve().parent.parent
UNITS_DIR = ROOT / "units"


def _load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise SystemExit("pyyaml is needed:  pip install -e \".[dev]\"") from exc
    return yaml.safe_load(path.read_text()) or {}


def _unit_from_dir(d: Path) -> Unit:
    meta = _load_yaml(d / "unit.yaml")
    bars = tuple(
        Bar(metric=b["metric"], threshold=float(b["threshold"]),
            direction=b.get("direction", "at_least"), note=b.get("note", ""))
        for b in meta.get("bars", []) or []
    )
    return Unit(
        uid=meta["id"], slug=meta.get("slug", d.name), title=meta["title"],
        track=meta["track"], difficulty=meta["difficulty"], minutes=int(meta.get("minutes", 20)),
        mode=meta.get("mode", "implement"), teaches=tuple(meta.get("teaches", []) or []),
        prereqs=tuple(meta.get("prereqs", []) or []), bars=bars,
        artefact=meta.get("artefact"), directory=d, summary=meta.get("summary", ""),
    )


@functools.lru_cache(maxsize=1)
def all_units() -> tuple[Unit, ...]:
    if not UNITS_DIR.exists():
        return ()
    units = [_unit_from_dir(d) for d in sorted(UNITS_DIR.iterdir())
             if d.is_dir() and (d / "unit.yaml").exists()]
    return tuple(units)


def by_id(uid: str) -> Unit | None:
    uid = uid.upper()
    return next((u for u in all_units() if u.uid.upper() == uid), None)


def validate_all() -> dict[str, list[str]]:
    """Every unit's structural problems, plus problems only visible across units."""
    found = {u.uid: u.validate() for u in all_units()}
    ids = {u.uid for u in all_units()}

    seen: dict[str, str] = {}
    for u in all_units():
        if u.uid in seen:
            found[u.uid].append(f"duplicate id, also used by {seen[u.uid]}")
        seen[u.uid] = str(u.directory.name)
        for p in u.prereqs:
            if p not in ids:
                found[u.uid].append(f"prereq {p} does not exist")

    for cycle in _cycles():
        for uid in cycle:
            found[uid].append(f"prerequisite cycle: {' -> '.join(cycle)}")

    # A unit is not finished when its checks run. It is finished when the checks have been
    # shown to accept a correct answer and reject a plausible wrong one. See selftest.py.
    from .selftest import structural_gaps
    for u in all_units():
        found[u.uid].extend(structural_gaps(u))

    return {k: v for k, v in found.items() if v}


def _cycles() -> list[list[str]]:
    """Prerequisite cycles. A cycle means nobody can start, and nothing else reports it."""
    graph = {u.uid: list(u.prereqs) for u in all_units()}
    seen: set[str] = set()
    stack: list[str] = []
    out: list[list[str]] = []

    def walk(node: str) -> None:
        if node in stack:
            out.append(stack[stack.index(node):] + [node])
            return
        if node in seen:
            return
        seen.add(node)
        stack.append(node)
        for nxt in graph.get(node, []):
            walk(nxt)
        stack.pop()

    for uid in graph:
        walk(uid)
    return out


def unlocked(done: set[str]) -> list[Unit]:
    """Units whose prerequisites are all complete."""
    return [u for u in all_units() if u.uid not in done and set(u.prereqs) <= done]


def pathway() -> list[list[Unit]]:
    """Units grouped into waves: everything in wave n depends only on waves before it.

    The wave, rather than a flat ordering, is the honest shape — several units are genuinely
    parallel and presenting them as a queue invents a sequence that does not exist.
    """
    remaining = list(all_units())
    done: set[str] = set()
    waves: list[list[Unit]] = []
    while remaining:
        wave = [u for u in remaining if set(u.prereqs) <= done]
        if not wave:                      # a cycle; validate_all() reports it properly
            waves.append(sorted(remaining, key=lambda u: u.uid))
            break
        waves.append(sorted(wave, key=lambda u: u.uid))
        done |= {u.uid for u in wave}
        remaining = [u for u in remaining if u.uid not in done]
    return waves
