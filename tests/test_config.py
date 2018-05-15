from unittest.mock import Mock

import pytest

import forge._config
from forge._config import (
    get_run_validators,
    set_run_validators,
)


# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access


@pytest.mark.usefixtures('reset_run_validators')
class TestRunValidators:
    def test_get_run_validators(self):
        rvmock = Mock()
        forge._config._run_validators = rvmock
        assert get_run_validators() == rvmock

    @pytest.mark.parametrize(('val',), [(True,), (False,)])
    def test_set_run_validators(self, val):
        forge._config._run_validators = not val
        set_run_validators(val)
        assert forge._config._run_validators == val

    def test_set_run_validators_bad_param_raises(self):
        with pytest.raises(TypeError) as excinfo:
            set_run_validators(Mock())
        assert excinfo.value.args[0] == "'run' must be bool."
