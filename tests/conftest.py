import pytest

import forge


@pytest.fixture
def reset_run_validators():
    # pylint: disable=W0212, protected-access
    prerun = forge._config._run_validators
    yield
    forge._config._run_validators = prerun