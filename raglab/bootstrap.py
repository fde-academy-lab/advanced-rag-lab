"""
One-click environment bootstrap for the raglab notebooks.

Design goals
------------
1. A learner opens any notebook, hits "Run All", and it works. No manual pip,
   no API keys, no dataset download, no network required for the default path.
2. Optional heavy paths (AWS Bedrock, sentence-transformers) are *offered*,
   never required, and are detected rather than assumed.
3. Everything is deterministic. Two runs of the same notebook on the same
   machine produce the same numbers, so a measured delta is a real delta.

The third point matters more than it looks. Half of this curriculum is about
telling a real improvement from run-to-run noise; a harness that is itself
non-deterministic cannot teach that.
"""
from __future__ import annotations

import importlib
import os
import random
import subprocess
import sys
from dataclasses import dataclass, field

# Packages the notebooks need, mapped import-name -> pip-name.
REQUIRED = {"numpy": "numpy", "matplotlib": "matplotlib", "pandas": "pandas"}

# Packages that unlock optional paths. Absence is normal and never fatal.
OPTIONAL = {
    "boto3": "boto3",                             # AWS Bedrock / Bedrock Knowledge Bases
    "sentence_transformers": "sentence-transformers",  # local neural encoder
    "anthropic": "anthropic",                     # Claude API generator / judge
}

SEED = 20260831


@dataclass
class Environment:
    """What this machine can actually do, discovered rather than assumed."""

    python: str = field(default_factory=lambda: sys.version.split()[0])
    installed: dict = field(default_factory=dict)
    missing: list = field(default_factory=list)
    optional_available: list = field(default_factory=list)
    offline: bool = False

    def has(self, name: str) -> bool:
        return name in self.installed or name in self.optional_available

    def summary(self) -> str:
        lines = [f"Python {self.python}"]
        for name, ver in sorted(self.installed.items()):
            lines.append(f"  [ok]      {name:<24} {ver}")
        for name in sorted(OPTIONAL):
            mark = "[ok]     " if name in self.optional_available else "[absent] "
            note = "" if name in self.optional_available else "  (optional path disabled)"
            lines.append(f"  {mark} {name:<24}{note}")
        return "\n".join(lines)


def _try_import(name):
    try:
        mod = importlib.import_module(name)
        return getattr(mod, "__version__", "?")
    except Exception:
        return None


def _pip_install(pkgs) -> bool:
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", *pkgs]
    try:
        subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        return True
    except Exception:
        return False


def bootstrap(verbose: bool = True, allow_install: bool = True) -> Environment:
    """Ensure the notebook can run, then pin every source of randomness.

    Returns an Environment describing what is available, so notebook cells can
    branch on capability instead of crashing on an import.
    """
    env = Environment()

    for imp, pip_name in REQUIRED.items():
        ver = _try_import(imp)
        if ver is None:
            env.missing.append(pip_name)
        else:
            env.installed[imp] = ver

    if env.missing and allow_install:
        if verbose:
            print(f"Installing missing requirements: {', '.join(env.missing)} ...")
        ok = _pip_install(env.missing)
        env.offline = not ok
        for imp, pip_name in REQUIRED.items():
            if imp not in env.installed:
                ver = _try_import(imp)
                if ver is not None:
                    env.installed[imp] = ver
        env.missing = [p for i, p in REQUIRED.items() if i not in env.installed]

    for imp in OPTIONAL:
        if _try_import(imp) is not None:
            env.optional_available.append(imp)

    # Determinism. Every stochastic component in this toolkit draws from one of
    # these, so a re-run reproduces a result exactly.
    random.seed(SEED)
    os.environ.setdefault("PYTHONHASHSEED", str(SEED))
    if "numpy" in env.installed:
        import numpy as np

        np.random.seed(SEED)

    if "matplotlib" in env.installed:
        import matplotlib

        # Agg keeps figures reproducible and headless-safe; notebooks still
        # display them inline because IPython captures the figure object.
        if "ipykernel" not in sys.modules:
            matplotlib.use("Agg")
        from . import viz  # noqa: F401  (applies the the maintainers style)

        viz.apply_style()

    if verbose:
        print(env.summary())
        if env.missing:
            print(
                "\nStill missing: "
                + ", ".join(env.missing)
                + "\nInstall them with:  pip install "
                + " ".join(env.missing)
            )
        else:
            print(f"\nEnvironment ready. Deterministic seed = {SEED}")
    return env


def repo_root(start=None):
    """Locate the directory that holds the raglab package, from anywhere."""
    import pathlib

    here = pathlib.Path(start or os.getcwd()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "raglab" / "__init__.py").exists():
            return candidate
    return here
