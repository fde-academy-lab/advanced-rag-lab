import pytest

import raglab
from raglab.bootstrap import bootstrap

bootstrap(verbose=False, allow_install=False)


@pytest.fixture(scope="session")
def system():
    """One built system shared by the whole test session."""
    bundle, index, pipe = raglab.quickstart(**raglab.TUNED, verbose=False)
    return bundle, index, pipe
