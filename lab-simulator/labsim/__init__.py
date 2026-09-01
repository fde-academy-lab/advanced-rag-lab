"""L.A.B. Simulator — a graded, progressive hands-on lab.

    python -m labsim next          what to do now
    python -m labsim brief R2      read the brief
    python -m labsim start R2      scaffold an attempt
    python -m labsim check R2      grade it

The design in one line: a unit makes you **decide** before you build, and grades the
**measurement**, not only the tests.
"""
from .model import Bar, Unit  # noqa: F401
from .registry import all_units, by_id, pathway, unlocked, validate_all  # noqa: F401

__all__ = ["Bar", "Unit", "all_units", "by_id", "pathway", "unlocked", "validate_all"]
