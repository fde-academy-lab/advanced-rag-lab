"""Shared helpers for a unit's check.py.

Every unit needs the same three things — load the learner's file, report pass/fail lines, emit
the machine-readable result — and getting one of them subtly wrong in forty places is how a
grader stops being trustworthy.

The loader in particular has a trap. A module using `from __future__ import annotations` and
`@dataclasses.dataclass` must be present in `sys.modules` *before* it is executed, because
dataclasses resolves string annotations by looking its own module up by name. Without that
registration the failure is `AttributeError: 'NoneType' object has no attribute '__dict__'`,
which tells a learner nothing about their code and is not their fault.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


class SolutionError(RuntimeError):
    """Raised with a message meant for the learner, not a stack trace."""


def load_solution(attempt_dir: str | Path, *, required: tuple[str, ...] = (),
                  filename: str = "solution.py"):
    """Import the learner's file and confirm it defines what the unit needs."""
    attempt = Path(attempt_dir)
    path = attempt / filename
    if not path.exists():
        raise SolutionError(f"No {filename} at {path}. Run `labsim start <id>` first.")

    name = f"labsim_attempt_{attempt.name}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SolutionError(f"{path} could not be loaded as a Python module.")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod          # before exec_module — see the module docstring
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:         # noqa: BLE001 - a learner's file; report it readably
        raise SolutionError(f"{filename} raised while importing: "
                            f"{type(exc).__name__}: {exc}") from exc

    missing = [n for n in required if not hasattr(mod, n)]
    if missing:
        raise SolutionError(f"{filename} does not define: {', '.join(missing)}")
    return mod


def load_answer(attempt_dir: str | Path, *, required: tuple[str, ...] = (),
                filename: str = "answer.yaml") -> dict:
    """Read the learner's answer.yaml for an `answer` unit and confirm the keys it needs.

    An answer unit grades a commitment rather than code — a number, a ranking, a set of
    choices — so the file is small and the failure modes are all about it being missing,
    unparsable, or still holding the template's placeholders. Each of those is reported as a
    sentence, not a traceback, for the same reason `load_solution` does it.
    """
    import yaml

    path = Path(attempt_dir) / filename
    if not path.exists():
        raise SolutionError(f"No {filename} at {path}. Run `labsim start <id>` and fill it in.")
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as exc:
        raise SolutionError(f"{filename} does not parse as YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise SolutionError(f"{filename} must be a mapping of field: value")
    missing = [k for k in required if k not in data or data[k] in (None, "")]
    if missing:
        raise SolutionError(f"{filename} leaves these blank: {', '.join(missing)}")
    placeholders = [k for k in required
                    if isinstance(data.get(k), str) and data[k].strip().startswith("<")]
    if placeholders:
        raise SolutionError(f"{filename} still holds the template placeholder for: "
                            f"{', '.join(placeholders)}")
    return data


class Checker:
    """Collects pass/fail lines and knows whether the unit passed."""

    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes: list[str] = []

    def __call__(self, name: str, ok: bool, detail: str = "") -> bool:
        if ok:
            self.passes.append(name)
            print(f"  pass  {name}")
        else:
            self.failures.append(name)
            print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""))
        return bool(ok)

    def note(self, text: str) -> None:
        print(f"        {text}")

    @property
    def ok(self) -> bool:
        return not self.failures


def emit(metrics: dict | None = None, checker: Checker | None = None,
         *, failures: list[str] | None = None) -> int:
    """Print the line the grader parses, and return the process exit code.

    `failures` is for the case where no check ran at all — the solution would not load, so
    there is nothing to check. That has to exit **non-zero**: a unit with no metric bar has
    nothing else left to fail on, and `emit({})` used to return 0, so a missing or unparsable
    solution.py was graded as a pass on four of the seven shipped units.
    """
    payload = {"metrics": metrics or {}}
    if checker is not None:
        payload["failures"] = checker.failures
        payload["passes"] = len(checker.passes)
    if failures:
        payload["failures"] = list(failures) + list(payload.get("failures") or [])
        payload.setdefault("passes", 0)
    print("LABSIM_RESULT:" + json.dumps(payload))
    if failures:
        return 1
    return 0 if (checker is None or checker.ok) else 1


def run(main_fn) -> int:
    """Wrap a unit's main() so a SolutionError becomes a readable message, not a traceback."""
    try:
        return main_fn(sys.argv[1] if len(sys.argv) > 1 else ".")
    except SolutionError as exc:
        print(f"  {exc}")
        return emit({}, failures=[str(exc)])
