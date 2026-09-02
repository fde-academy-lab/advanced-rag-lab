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


# ──────────────────────────────────────────────────────── template label names ──
TEMPLATE_DIRS = (".github/ISSUE_TEMPLATE", ".github/DISCUSSION_TEMPLATE")


def _template_files():
    for d in TEMPLATE_DIRS:
        yield from sorted((ROOT / d).glob("*.yml"))


@pytest.mark.parametrize("path", list(_template_files()), ids=lambda p: p.name)
def test_every_template_label_is_one_the_repository_creates(path):
    """A template naming a label that does not exist applies nothing, silently.

    All four discussion templates did this: `question`, `design-review`, `show-and-tell` and
    `lab-simulator`. None was ever in `LABELS`, and `question` is one of GitHub's defaults that
    `create_labels` explicitly deletes — so the one template that named a real label named one
    the provisioner removes on every run.
    """
    import seed_content
    defined = ({name for name, *_ in seed_content.LABELS}
               | {name for name, *_ in seed_content.DISCUSSION_LABELS})
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    for label in spec.get("labels") or []:
        assert label in defined, (
            f"{path.name} applies {label!r}, which nothing in seed_content.LABELS creates")


def test_no_template_names_a_label_the_provisioner_deletes():
    """`create_labels` removes GitHub's defaults to keep the list legible. Nothing may use one."""
    source = (ROOT / "scripts" / "setup_github.py").read_text(encoding="utf-8")
    junk = re.search(r'for junk in \(([^)]*)\)', source)
    assert junk, "create_labels no longer deletes GitHub's defaults; this test names that loop"
    deleted = set(re.findall(r'"([^"]+)"', junk.group(1)))
    for path in _template_files():
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        for label in spec.get("labels") or []:
            assert label not in deleted, f"{path.name} applies {label!r}, which is deleted"


def test_every_discussion_template_matches_a_category_slug():
    """GitHub keys a discussion form on the category slug and silently ignores it otherwise.

    There is no error, no warning and no place the mistake shows up — the category simply
    opens with an empty box, which looks exactly like a category that has no template.
    """
    import seed_content

    def slug(name):
        return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")

    # GitHub's six defaults plus the eight this repository adds.
    known = {slug(n) for n in ("Announcements", "General", "Ideas", "Polls", "Q&A",
                               "Show and tell")}
    known |= {slug(name) for name, *_ in seed_content.CATEGORIES}

    for path in sorted((ROOT / ".github" / "DISCUSSION_TEMPLATE").glob("*.yml")):
        assert path.stem in known, (
            f"{path.name} names no category slug — known slugs are {sorted(known)}")


def test_the_provision_summary_names_the_right_categories_as_answerable():
    """The summary is the manual-setup instruction, and it said "the first four".

    The first four in its own list were Design Reviews, Reading Club, Interview Prep and LAB
    Simulator — two of which `CATEGORIES` declares open-ended. Following it produced two
    categories that cannot carry an accepted answer and two that carry one nobody wanted.
    """
    import seed_content
    text = (WORKFLOWS / "provision.yml").read_text(encoding="utf-8")
    for name, _emoji, _desc, fmt in seed_content.CATEGORIES:
        row = re.search(rf"^\s*echo \"\s*\|\s*{re.escape(name)}\s*\|\s*(.+?)\s*\|\"",
                        text, re.M)
        assert row, f"the provision summary does not list {name!r}"
        says_qa = "Q&A" in row.group(1)
        assert says_qa == (fmt == "ANSWER"), (
            f"{name}: CATEGORIES says {fmt}, the summary says {row.group(1)!r}")
    assert "the first four" not in text, "the positional instruction is back"


def test_the_simulator_form_lists_every_unit():
    """The unit dropdown is hand-maintained YAML. A unit missing from it cannot be posted.

    The parser reads the id off the option text, so the format is part of the contract too:
    the id first, then a dash.
    """
    import sys
    sys.path.insert(0, str(ROOT / "lab-simulator"))
    from labsim.registry import all_units

    form = yaml.safe_load((ROOT / ".github" / "DISCUSSION_TEMPLATE" / "lab-simulator.yml")
                          .read_text(encoding="utf-8"))
    unit_field = next(f for f in form["body"] if f.get("id") == "unit")
    options = unit_field["attributes"]["options"]
    listed = {o.split(" ", 1)[0] for o in options}
    have = {u.uid for u in all_units()}
    assert have <= listed, f"units missing from the form dropdown: {sorted(have - listed)}"
    assert listed <= have, f"the form lists units that do not exist: {sorted(listed - have)}"
    for o in options:
        assert re.match(r"^[A-Z]{1,2}\d{1,2} — ", o), f"option does not start with an id: {o!r}"


def test_the_codespaces_pick_list_offers_every_unit():
    """Mirror of the `Engine tests` job's devcontainer step, so it fails here before it fails in CI.

    `.vscode/tasks.json` hard-codes the unit menu. Nine drills were added and the merge was
    refused because this check — which only CI ran — went red. Now pytest runs it too.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "check_devcontainer", ROOT / "scripts" / "lint" / "check_devcontainer.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0, "the Codespaces surface has drifted — run scripts/lint/check_devcontainer.py"
