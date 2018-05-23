import pytest

import forge


@pytest.fixture
def reset_run_validators():
    """
    Helper fixture that resets the state of the ``run_validators`` to its value
    before the test was run.
    """
    # pylint: disable=W0212, protected-access
    prerun = forge._config._run_validators
    yield
    forge._config._run_validators = prerun