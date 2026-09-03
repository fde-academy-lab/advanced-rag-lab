#!/usr/bin/env bash
# Everything slow, cacheable and learner-independent. Runs once per machine — and during a
# Codespaces prebuild, which is why it must not depend on anything the learner has done yet.
set -euo pipefail

echo "installing the toolkit and its dev extras..."
pip install --disable-pip-version-check --no-input -e ".[dev]"

echo "warming the corpus so the first graded unit is not the slow one..."
python - <<'PY'
# Import cost, not data: there is no dataset to download and nothing to cache on disk. This
# pays the interpreter's import and bytecode-compilation cost now instead of during somebody's
# first `labsim check`, which is the moment they decide whether this thing is fast.
import raglab                                            # noqa: F401
from raglab import corpus, chunking, embed               # noqa: F401
bundle = corpus.build_corpus()
print(f"  corpus ready: {len(bundle.documents)} documents, {len(bundle.questions)} questions")
PY

echo "checking the lab..."
cd lab-simulator && python -m labsim validate
