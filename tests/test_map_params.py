import inspect

import pytest

from forge._marker import (
    void,
    void_to_empty,
)
from forge._signature import (
    FSignature,
    map_parameters,
    pk_strings,
)

POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY  # type: ignore
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD  # type: ignore
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


class TestMapParameters:
    @staticmethod
    def make_param(name, kind, default=void):
        return inspect.Parameter(name, kind, default=void_to_empty(default)) \
            if kind is not None \
            else None

    @pytest.mark.parametrize(('from_name', 'to_name'), [
        pytest.param('a', 'a', id='same_name'),
        pytest.param('a', 'b', id='diff_name'),
    ])
    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(None, id='no_parameter'), # i.e. map: sig() -> sig(a=1)
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('from_default', 'to_default'), [
        pytest.param('from_def', void, id='from_default'),
        pytest.param(void, 'to_def', id='to_default'),
        pytest.param('from_def', 'to_def', id='default_from_and_default_to'),
    ])
    def test_to_non_var_parameter(
            self,
            from_name,
            from_kind,
            from_default,
            to_name,
            to_kind,
            to_default,
        ):
        # pylint: disable=R0913, too-many-arguments
        from_param = self.make_param(from_name, from_kind, from_default)
        from_sig = inspect.Signature([from_param] if from_param else None)
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param(to_name, to_kind, to_default)
        to_sig = inspect.Signature([to_param])

        # Idenitfy map_parameters errors
        expected_exc = None
        if not from_param:
            if to_param.default is inspect.Parameter.empty:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
                        to_name=to_param.name,
                    )
                )
        elif from_param.name != to_param.name:
            if to_param.default is inspect.Parameter.empty:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
                        to_name=to_param.name,
                    )
                )
            else:
                expected_exc = TypeError(
                    'Missing requisite mapping from parameters (a)'
                )

        if expected_exc:
            with pytest.raises(type(expected_exc)) as excinfo:
                map_parameters(fsig, to_sig)
            assert excinfo.value.args[0] == expected_exc.args[0]
            return

        pmap = map_parameters(fsig, to_sig)
        expected_pmap = {from_param.name: to_param.name} if from_param else {}
        assert pmap == expected_pmap

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_to_var_positional(self, from_kind):
        from_param = self.make_param('from_', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param('args', VAR_POSITIONAL)
        to_sig = inspect.Signature([to_param])

        if from_param.kind is VAR_POSITIONAL:
            pmap = map_parameters(fsig, to_sig)
            assert pmap == {from_param.name: to_param.name}
            return

        with pytest.raises(TypeError) as excinfo:
            map_parameters(fsig, to_sig)

        if from_param.kind is VAR_KEYWORD:
            assert excinfo.value.args[0] == (
                "Missing requisite mapping from variable-keyword parameter "
                "'from_'"
            )
        else:
            assert excinfo.value.args[0] == \
                "Missing requisite mapping from parameters (from_)"

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_to_var_keyword(self, from_kind):
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param('kwargs', VAR_KEYWORD)
        to_sig = inspect.Signature([to_param])

        expected_exc = None
        if from_param.kind is VAR_POSITIONAL:
            expected_exc = TypeError(
                "Missing requisite mapping from variable-positional "
                "parameter 'a'"
            )

        if expected_exc:
            with pytest.raises(type(expected_exc)) as excinfo:
                map_parameters(fsig, to_sig)
            assert excinfo.value.args[0] == expected_exc.args[0]
            return
        pmap = map_parameters(fsig, to_sig)
        assert pmap == {from_param.name: to_param.name}

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_to_empty(self, from_kind):
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_sig = inspect.Signature()

        with pytest.raises(TypeError) as excinfo:
            map_parameters(fsig, to_sig)
        if from_param.kind in (VAR_KEYWORD, VAR_POSITIONAL):
            assert excinfo.value.args[0] == (
                "Missing requisite mapping from {from_kind} parameter 'a'".\
                    format(from_kind=pk_strings[from_kind])
            )
        else:
            assert excinfo.value.args[0] == \
                "Missing requisite mapping from parameters (a)"

    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    def test_from_hidden(self, to_kind):
        from_sig = inspect.Signature()
        fsig = FSignature()
        to_param = self.make_param('a', to_kind, default=1)
        to_sig = inspect.Signature([to_param])

        assert map_parameters(fsig, to_sig) == {}