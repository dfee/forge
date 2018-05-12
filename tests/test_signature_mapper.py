import inspect

import pytest

from forge._marker import (
    void,
    void_to_empty,
)
from forge._signature import (
    CallArguments,
    make_transform,
    pk_strings,
)

POSITIONAL_ONLY = inspect.Parameter.POSITIONAL_ONLY  # type: ignore
POSITIONAL_OR_KEYWORD = inspect.Parameter.POSITIONAL_OR_KEYWORD  # type: ignore
VAR_POSITIONAL = inspect.Parameter.VAR_POSITIONAL
KEYWORD_ONLY = inspect.Parameter.KEYWORD_ONLY
VAR_KEYWORD = inspect.Parameter.VAR_KEYWORD


class TestMakeTransform:
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
    @pytest.mark.parametrize(('has_keymap_hints',), [(True,), (False,)])
    @pytest.mark.parametrize(('from_default', 'to_default'), [
        pytest.param('from_def', void, id='from_default'),
        pytest.param(void, 'to_def', id='to_default'),
        pytest.param('from_def', 'to_def', id='default_from_and_default_to'),
    ])
    @pytest.mark.parametrize(('input_',), [
        pytest.param(CallArguments(), id='input_missing'),
        pytest.param(CallArguments(1), id='input_args'),
        pytest.param(CallArguments(a=1), id='input_kwargs'),
    ])
    def test_to_non_var_parameter(
            self,
            from_name,
            from_kind,
            from_default,
            to_name,
            to_kind,
            to_default,
            has_keymap_hints,
            input_,
        ):
        # pylint: disable=R0913, too-many-arguments
        from_param = self.make_param(from_name, from_kind, from_default)
        from_sig = inspect.Signature([from_param] if from_param else None)
        to_param = self.make_param(to_name, to_kind, to_default)
        to_sig = inspect.Signature([to_param])
        keymap_hints = {from_param.name: to_param.name} \
            if from_param and has_keymap_hints \
            else None

        # Idenitfy make_transform errors
        make_transform_exc = None
        if not from_param:
            if to_param.default is inspect.Parameter.empty:
                make_transform_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
                        to_name=to_param.name,
                    )
                )
        elif from_param.name != to_param.name and not has_keymap_hints:
            if to_param.default is inspect.Parameter.empty:
                make_transform_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
                        to_name=to_param.name,
                    )
                )
            else:
                make_transform_exc = TypeError(
                    'Missing requisite mapping from parameters (a)'
                )

        if make_transform_exc:
            with pytest.raises(type(make_transform_exc)) as excinfo:
                make_transform(from_sig, to_sig, keymap_hints)
            assert excinfo.value.args[0] == make_transform_exc.args[0]
            return
        transform = make_transform(from_sig, to_sig, keymap_hints)

        # Idenitfy transform errors
        transform_exc = None
        if not input_.args and not input_.kwargs:
            if not from_param:
                pass
            elif from_param.default is inspect.Parameter.empty:
                transform_exc = TypeError("missing a required argument: 'a'")
        elif not input_.args:
            if not from_param:
                transform_exc = TypeError(
                    "got an unexpected keyword argument 'a'"
                )
            elif from_param.kind is POSITIONAL_ONLY:
                transform_exc = TypeError(
                    "'a' parameter is positional only, but was passed as a "
                    "keyword"
                )
        elif not input_.kwargs:
            if not from_param:
                transform_exc = TypeError("too many positional arguments")

        if transform_exc:
            with pytest.raises(type(transform_exc)) as excinfo:
                transform(input_)
            assert excinfo.value.args[0] == transform_exc.args[0]
            return
        result = transform(input_)

        # Build expected result
        if to_param.kind is KEYWORD_ONLY:
            assert not result.args
            assert result.kwargs == {to_name: 1} \
                if input_.args or input_.kwargs \
                else {to_name: from_default}
        else:
            assert result.args == (1,) \
                if input_.args or input_.kwargs \
                else (from_default,)
            assert not result.kwargs

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
        to_param = self.make_param('args', VAR_POSITIONAL)
        to_sig = inspect.Signature([to_param])
        input_ = CallArguments(1)

        if from_param.kind is VAR_POSITIONAL:
            transform = make_transform(from_sig, to_sig)
            assert transform(input_) == input_
            return

        with pytest.raises(TypeError) as excinfo:
            make_transform(from_sig, to_sig)

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
        to_param = self.make_param('kwargs', VAR_KEYWORD)
        to_sig = inspect.Signature([to_param])

        make_transform_exc = None
        if from_param.kind is VAR_POSITIONAL:
            make_transform_exc = TypeError(
                "Missing requisite mapping from variable-positional "
                "parameter 'a'"
            )

        if make_transform_exc:
            with pytest.raises(type(make_transform_exc)) as excinfo:
                make_transform(from_sig, to_sig)
            assert excinfo.value.args[0] == make_transform_exc.args[0]
            return
        transform = make_transform(from_sig, to_sig)

        input_ = CallArguments(1) \
            if from_param.kind is POSITIONAL_ONLY \
            else CallArguments(a=1)
        result = transform(input_)
        assert result == CallArguments(a=1)

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
        to_sig = inspect.Signature()

        with pytest.raises(TypeError) as excinfo:
            make_transform(from_sig, to_sig)
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
        to_param = self.make_param('a', to_kind, default=1)
        to_sig = inspect.Signature([to_param])
        transform = make_transform(from_sig, to_sig)

        result = transform(CallArguments())
        if to_param.kind is KEYWORD_ONLY:
            assert result == CallArguments(a=1)
        else:
            assert result == CallArguments(1)