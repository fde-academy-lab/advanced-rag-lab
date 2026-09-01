"""The invariant that keeps `main` mergeable.

A required status check that does not run on every pull request is not a gate — it is a
deadlock. GitHub shows the missing context as "Expected" indefinitely, and the pull request can
only be merged by an administrator bypassing branch protection. That is exactly what shipped
here: `links` and `Mermaid renders on GitHub` were required, and their workflow was filtered to
`paths: ["**/*.md"]`, so no pull request touching only Python could ever merge. It went
unnoticed for a day because every merge until then had been an admin bypass.

The rule is one sentence and this file is it: **every context in `REQUIRED_CHECKS` must be
produced by a job in a workflow whose `pull_request` trigger has no `paths` filter.**
"""
from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
sys.path.insert(0, str(ROOT / "scripts"))

yaml = pytest.importorskip("yaml")

from setup_github import REQUIRED_CHECKS  # noqa: E402


def workflows() -> dict[Path, dict]:
    return {p: yaml.safe_load(p.read_text()) for p in sorted(WORKFLOWS.glob("*.yml"))}


MATRIX_REF = re.compile(r"\$\{\{\s*matrix\.([A-Za-z_][\w-]*)\s*\}\}")


def job_names(doc: dict) -> set[str]:
    """Every name a job can report a check run under.

    Two rules, and getting them wrong is how a required context is misspelled in branch
    protection and nobody notices until a merge is refused:

      * a `name:` containing `${{ matrix.x }}` has the expression **substituted**, one check
        per combination — `Tests (py${{ matrix.python }})` becomes `Tests (py3.11)`
      * a name with no expression, on a job that has a matrix, gets the combination
        **appended** in parentheses
    """
    out = set()
    for key, job in (doc.get("jobs") or {}).items():
        name = job.get("name", key)
        out.add(name)
        out.add(key)

        matrix = {k: v for k, v in ((job.get("strategy") or {}).get("matrix") or {}).items()
                  if isinstance(v, list) and k not in ("include", "exclude")}
        if not matrix:
            continue
        keys = sorted(matrix)
        for combo in itertools.product(*(matrix[k] for k in keys)):
            values = dict(zip(keys, combo))
            if MATRIX_REF.search(name):
                out.add(MATRIX_REF.sub(
                    lambda m, v=values: str(v.get(m.group(1), m.group(0))), name))
            else:
                out.add(f"{name} ({', '.join(str(v) for v in combo)})")
    return out


def pull_request_trigger(doc: dict):
    """The `on: pull_request:` value, or None when the workflow has no such trigger.

    PyYAML parses a bare `on:` key as the boolean True, so both spellings are checked.
    """
    on = doc.get("on", doc.get(True))
    if isinstance(on, str):
        return {} if on == "pull_request" else None
    if isinstance(on, list):
        return {} if "pull_request" in on else None
    if isinstance(on, dict) and "pull_request" in on:
        return on["pull_request"] or {}
    return None


def providers(context: str) -> list[tuple[Path, dict]]:
    return [(path, doc) for path, doc in workflows().items() if context in job_names(doc)]


@pytest.mark.parametrize("context", REQUIRED_CHECKS)
def test_every_required_check_is_produced_by_a_workflow(context):
    found = providers(context)
    assert found, (
        f"branch protection requires {context!r} and no workflow job reports it. "
        "The context would sit 'Expected' forever and nothing could merge.")


@pytest.mark.parametrize("context", REQUIRED_CHECKS)
def test_every_required_check_runs_on_every_pull_request(context):
    for path, doc in providers(context):
        trigger = pull_request_trigger(doc)
        assert trigger is not None, (
            f"{path.name} produces the required check {context!r} but has no `pull_request` "
            "trigger, so it never reports on a pull request.")
        assert "paths" not in trigger and "paths-ignore" not in trigger, (
            f"{path.name} produces the required check {context!r} and filters its "
            f"`pull_request` trigger on {trigger.get('paths', trigger.get('paths-ignore'))!r}. "
            "A pull request outside those paths never gets the check, GitHub leaves it "
            "'Expected', and the branch cannot be merged without an admin bypass.")


def test_the_matrix_context_we_require_actually_exists():
    """`Tests (py3.11)` is a matrix combination, not a job name. Renaming the matrix breaks it."""
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text())
    assert "Tests (py3.11)" in job_names(ci)


def test_workflows_have_no_duplicate_keys():
    """PyYAML silently keeps the last of a duplicated key, which is how an `env:` block vanishes."""
    class Strict(yaml.SafeLoader):
        pass

    def no_dupes(loader, node, deep=False):
        seen = []
        for key, _ in node.value:
            k = loader.construct_object(key, deep=deep)
            assert k not in seen, f"duplicate key {k!r}"
            seen.append(k)
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_dupes)
    for path in WORKFLOWS.glob("*.yml"):
        yaml.load(path.read_text(), Strict)
