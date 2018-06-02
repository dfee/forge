from collections import OrderedDict
import inspect

import pytest

import forge
import forge._signature
from forge._marker import empty
from forge._parameter import FParameter
from forge._signature import (
    CallArguments,
    FSignature,
    Mapper,
    pk_strings,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access
# pylint: disable=W0621, redefined-outer-name
# pylint: disable=R0904, too-many-public-methods

POSITIONAL_ONLY = FParameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = FParameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = FParameter.VAR_POSITIONAL
KEYWORD_ONLY = FParameter.KEYWORD_ONLY
VAR_KEYWORD = FParameter.VAR_KEYWORD


class TestFSignature:
    def test_validate_non_fparameter_raises(self):
        """
        Ensure that non-fparams raise a TypeError by validating a
        ``inspect.Parameter``
        """
        param = inspect.Parameter('x', POSITIONAL_ONLY)
        with pytest.raises(TypeError) as excinfo:
            FSignature([param])
        assert excinfo.value.args[0] == \
            "Received non-FParameter '{}'".format(param)

    def test_validate_unnamed_fparameter_raises(self):
        """
        Ensure that fparams must be named
        """
        arg = forge.arg()
        with pytest.raises(ValueError) as excinfo:
            FSignature([arg])
        assert excinfo.value.args[0] == \
            "Received unnamed FParameter: '{}'".format(arg)

    def test_validate_late_contextual_fparam_raises(self):
        """
        Ensure that non-first fparams cannot be contextual
        """
        with pytest.raises(TypeError) as excinfo:
            FSignature([forge.arg('a'), forge.ctx('self')])
        assert excinfo.value.args[0] == \
            'Only the first FParameter can be contextual'

    def test_validate_multiple_interface_name_raises(self):
        """
        Ensure that a ``interface_name`` between multiple fparams raises
        """
        with pytest.raises(ValueError) as excinfo:
            FSignature([forge.arg('a1', 'b'), forge.arg('a2', 'b')])
        assert excinfo.value.args[0] == \
            "Received multiple FParameters with interface_name 'b'"

    def test_validate_multiple_name_raises(self):
        """
        Ensure that a ``name`` between multiple fparams raises
        """
        with pytest.raises(ValueError) as excinfo:
            FSignature([forge.arg('a', 'b1'), forge.arg('a', 'b2')])
        assert excinfo.value.args[0] == \
            "Received multiple FParameters with name 'a'"

    def test_validate_multiple_var_positional_fparameters_raises(self):
        """
        Ensure that mulitple `var-positional` fparams raise
        """
        params = [
            FParameter(
                kind=inspect.Parameter.VAR_POSITIONAL,
                name='args{}'.format(i),
                interface_name='args{}'.format(i),
                default=empty.native,
                type=empty.native,
            ) for i in range(2)
        ]
        with pytest.raises(TypeError) as excinfo:
            FSignature(params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-positional FParameters'

    def test_validate_multiple_var_keyword_fparameters_raises(self):
        """
        Ensure that mulitple `var-keyword` fparams raise
        """
        params = [
            FParameter(
                kind=inspect.Parameter.VAR_KEYWORD,
                name='kwargs{}'.format(i),
                interface_name='kwargs{}'.format(i),
                default=empty.native,
                type=empty.native,
            ) for i in range(2)
        ]
        with pytest.raises(TypeError) as excinfo:
            FSignature(params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-keyword FParameters'

    def test_validate_out_of_order_fparameters_raises(self):
        """
        Ensure that fparams misordered (by ``kind``) raise
        """
        kwarg_ = forge.kwarg('kwarg')
        arg_ = forge.arg('arg')
        with pytest.raises(SyntaxError) as excinfo:
            FSignature([kwarg_, arg_])
        assert excinfo.value.args[0] == (
            "{arg_} of kind '{arg_kind}' follows "
            "{kwarg_} of kind '{kwarg_kind}'".format(
                arg_=arg_,
                arg_kind=arg_.kind.name,
                kwarg_=kwarg_,
                kwarg_kind=kwarg_.kind.name,
            )
        )

    @pytest.mark.parametrize(('constructor',), [(forge.pos,), (forge.arg,)])
    def test_validate_non_default_follows_default_raises(self, constructor):
        """
        Ensure that ``positional-only`` and ``positional-or-keyword`` fparams
        with default values come after fparams without default values
        """
        default = constructor('d', default=None)
        nondefault = constructor('nd')
        with pytest.raises(SyntaxError) as excinfo:
            FSignature([default, nondefault])
        assert excinfo.value.args[0] == (
            'non-default FParameter follows default FParameter'
        )

    def test_validate_default_kw_only_follows_non_default_kw_only(self):
        """
        Ensure that ``keyword-only`` fparams with default values can come after
        fparams without default values (only true for ``keyword-only``!)
        """
        FSignature([
            forge.kwarg('a', default=None),
            forge.kwarg('b'),
        ])

    def test__repr__(self):
        """
        Ensure pretty printing of FSignature (includes fparams)
        """
        assert repr(FSignature([forge.self])) == '<FSignature (self)>'

    # Begin collections.abc.Mapping Tests
    def test__getitem__str(self):
        """
        Ensure that ``__getitem__`` retrieves fparams by ``name``
        (an abstract collections.abc.Mapping method)
        """
        fparam = forge.arg('a')
        fsig = FSignature([fparam])
        assert fsig['a'] is fparam

    @pytest.mark.parametrize(('start', 'end', 'expected'), [
        pytest.param('c', None, 'cd', id='start'),
        pytest.param(None, 'c', 'abc', id='end'),
        pytest.param('b', 'c', 'bc', id='start_and_end'),
        pytest.param(None, None, 'abcd', id='no_start_no_end'),
        pytest.param('x', None, '', id='unknown_start'),
        pytest.param(None, 'x', 'abcd', id='unknown_end'),
    ])
    def test__getitem__slice(self, start, end, expected):
        """
        Ensure that ``__getitem__`` retrives from slice.start forward
        """
        fparams = OrderedDict([(name, forge.arg(name)) for name in 'abcd'])
        fsig = FSignature(list(fparams.values()))
        assert fsig[start:end] == [fparams[e] for e in expected]

    def test__len__(self):
        """
        Ensure that ``__len__`` retrieves a count of the fparams
        (an abstract collections.abc.Mapping method)
        """
        assert len(FSignature([forge.arg('a')])) == 1

    def test__iter__(self):
        """
        Ensure that ``__iter__`` returns an iterator over all fparams
        (an abstract collections.abc.Mapping method)
        """
        fparam = forge.arg('a')
        fsig = FSignature([fparam])
        assert dict(fsig) == {fparam.name: fparam}
    # End collections.abc.Mapping Tests

    def test_from_signature(self):
        """
        Ensure a ``FSignature`` can be adequately generated from an
        ``inspect.Signature``
        """
        sig = inspect.Signature([
            inspect.Parameter(
                'a',
                POSITIONAL_OR_KEYWORD,
                default=0,
                annotation=int,
            ),
        ])
        fsig = FSignature.from_signature(sig)
        assert len(fsig) == 1
        assert fsig['a'] == FParameter(
            kind=POSITIONAL_OR_KEYWORD,
            name='a',
            interface_name='a',
            default=0,
            type=int,
        )

    def test_from_callable(self):
        """
        Ensure a ``FSignature`` can be adequately generated from a callable
        """
        def func(a: int = 0):
            return a
        fsig = FSignature.from_callable(func)
        assert len(fsig) == 1
        assert fsig['a'] == FParameter(
            kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
            name='a',
            interface_name='a',
            default=0,
            type=int,
        )

    @pytest.mark.parametrize(('has_param',), [(True,), (False,)])
    def test_var_positional(self, has_param):
        """
        Ensure that the ``var-positional`` fparam is returned (or None)
        """
        fparam = FParameter(VAR_POSITIONAL, 'args')
        fsig = FSignature([fparam] if has_param else [])
        assert fsig.var_positional == (fparam if has_param else None)

    @pytest.mark.parametrize(('has_param',), [(True,), (False,)])
    def test_var_keyword(self, has_param):
        """
        Ensure that the ``var-keyword`` fparam is returned (or None)
        """
        fparam = FParameter(VAR_KEYWORD, 'args')
        fsig = FSignature([fparam] if has_param else [])
        assert fsig.var_keyword == (fparam if has_param else None)

    @pytest.mark.parametrize(('has_param',), [(True,), (False,)])
    def test_context(self, has_param):
        """
        Ensure that the ``context`` fparam is returned (or None)
        """
        fparam = FParameter(POSITIONAL_OR_KEYWORD, 'args', contextual=True)
        fsig = FSignature([fparam] if has_param else [])
        assert fsig.context == (fparam if has_param else None)


class TestMapper:
    @staticmethod
    def make_param(name, kind, default=empty):
        """
        Helper factory that generates an ``inspect.Parameter`` based on
        ``name`` , ``kind`` and ``default``
        """
        return inspect.Parameter(
            name,
            kind,
            default=empty.ccoerce_native(default)
        ) if kind is not None else None

    def test__init__signature_with_bound_params(self):
        """
        Ensure the mapper doesn't produce include bound fparams in public sig
        """
        fsig = FSignature([forge.arg('bound', default=1, bound=True)])
        func = lambda bound: None
        mapper = Mapper(fsig, func)
        assert not mapper.public_signature.parameters

    def test__repr__(self):
        """
        Ensure the mapper is pretty printable with ``FSignature`` and
        ``inspect.Signature``
        """
        fsig = FSignature([forge.pos('a', 'b')])
        callable_ = lambda *, b: None
        mapper = Mapper(fsig, callable_)
        assert repr(mapper) == '<Mapper (a, /) -> (*, b)>'

    @pytest.mark.parametrize(('has_context',), [(True,), (False,)])
    def test_get_context(self, has_context):
        """
        Ensure the mapper retrieves the context value from arguments
        """
        fparam = forge.ctx('param') \
            if has_context \
            else forge.arg('param')
        fsig = FSignature([fparam])
        mapper = Mapper(fsig, lambda param: None)

        kwargs = {'param': object()}
        ctx = mapper.get_context(kwargs)
        assert ctx == (kwargs['param'] if has_context else None)

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='from_positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='from_positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='from_keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='to_positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='to_positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='to_keyword_only'),
        pytest.param(VAR_KEYWORD, id='to_var_keyword'),
    ])
    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__params_mapped(self, from_kind, to_kind, vary_name):
        """
        Ensure that call arguments are mapped from parameters of type:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY

        to their interface counterparts as:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY
        - VAR_KEYWORD

        with and without names being varied.
        """
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature([FParameter(from_kind, from_name, to_name)])
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, to_kind)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(**{from_name: 1}) \
            if from_kind in (KEYWORD_ONLY, VAR_KEYWORD) \
            else CallArguments(1)
        expected = CallArguments(**{to_name: 1}) \
            if to_kind in (KEYWORD_ONLY, VAR_KEYWORD) \
            else CallArguments(1)
        result = mapper(*call_args.args, **call_args.kwargs)
        assert result == expected

    def test__call__bound_injected(self):
        """
        Ensure ``bound`` fparams are injected into the mapping.
        """
        fsig = FSignature([forge.arg('bound', default=1, bound=True)])
        func = lambda bound: bound
        mapper = Mapper(fsig, func)
        assert mapper() == CallArguments(1)

    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__vpo_param_mapped(self, vary_name):
        """
        Ensure ``var-positional`` params are directly mapped
        (w/ and w/o varied name)
        """
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature([FParameter(VAR_POSITIONAL, from_name, to_name)])
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, VAR_POSITIONAL)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(1, 2, 3)
        assert mapper(*call_args.args) == call_args

    @pytest.mark.parametrize(('vary_name',), [
        pytest.param(True, id='varied_name'),
        pytest.param(False, id='same_name'),
    ])
    def test__call__vkw_param_mapped(self, vary_name):
        """
        Ensure ``var-keyword`` params are directly mapped
        (w/ and w/o varied name)
        """
        from_name, to_name = ('p1', 'p1') if not vary_name else ('p1', 'p2')
        fsig = FSignature([FParameter(VAR_KEYWORD, from_name, to_name)])
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter(to_name, VAR_KEYWORD)])
        mapper = Mapper(fsig, func)

        call_args = CallArguments(a=1, b=2, c=3)
        assert mapper(**call_args.kwargs) == call_args

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    def test__call__defaults_applied(self, from_kind):
        """
        Ensure that defaults are applied to the underlying params
        (i.e. args passed):
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY
        """
        from_param = self.make_param('a', from_kind, default=1)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        func = lambda: None
        func.__signature__ = \
            inspect.Signature([inspect.Parameter('kwargs', VAR_KEYWORD)])
        mapper = Mapper(fsig, func)

        assert mapper() == CallArguments(a=1)

    def test__call__binding_error_raises_named(self):
        """
        Ensure that a lack of required (non-default) arguments raises a
        TypeError that mirrors the one raised when calling the callable directly
        """
        fsig = FSignature([forge.arg('a')])
        def func(a):
            # pylint: disable=W0613, unused-argument
            pass
        mapper = Mapper(fsig, func)
        with pytest.raises(TypeError) as excinfo:
            mapper()
        assert excinfo.value.args[0] == \
            "func() missing a required argument: 'a'"

    @pytest.mark.parametrize(('from_name', 'to_name'), [
        pytest.param('a', 'a', id='same_name'),
        pytest.param('a', 'b', id='diff_name'),
    ])
    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(None, id='no_parameter'), # i.e. map: sig() -> sig(a=1)
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('to_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
    ])
    @pytest.mark.parametrize(('from_default', 'to_default'), [
        pytest.param('from_def', empty, id='from_default'),
        pytest.param(empty, 'to_def', id='to_default'),
        pytest.param('from_def', 'to_def', id='default_from_and_default_to'),
    ])
    def test_map_parameters_to_non_var_parameter(
            self,
            from_name,
            from_kind,
            from_default,
            to_name,
            to_kind,
            to_default,
        ):
        """
        Ensure the mapping **strategy** produced with input fparams of ``kind``:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY

        to callable params of ``kind``:
        - POSITIONAL_ONLY
        - POSITIONAL_OR_KEYWORD
        - KEYWORD_ONLY

        with varrying ``name`` and ``default``
        """
        # pylint: disable=R0913, too-many-arguments
        # pylint: disable=R0914, too-many-locals
        from_param = self.make_param(from_name, from_kind, from_default)
        from_sig = inspect.Signature([from_param] if from_param else None)
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param(to_name, to_kind, to_default)
        to_sig = inspect.Signature([to_param])

        # Idenitfy map_parameters errors
        expected_exc = None
        if not from_param:
            if to_param.default is empty.native:
                expected_exc = TypeError(
                    "Missing requisite mapping to non-default "
                    "{to_kind} parameter '{to_name}'".format(
                        to_kind=pk_strings[to_param.kind],
                        to_name=to_param.name,
                    )
                )
        elif from_param.name != to_param.name:
            if to_param.default is empty.native:
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
                Mapper.map_parameters(fsig, to_sig)
            assert excinfo.value.args[0] == expected_exc.args[0]
            return

        pmap = Mapper.map_parameters(fsig, to_sig)
        expected_pmap = {from_param.name: to_param.name} if from_param else {}
        assert pmap == expected_pmap

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_map_parameters_to_var_positional(self, from_kind):
        """
        Ensure the mapping **strategy** produced mapping *to* ``var-positional``
        - POSITIONAL_ONLY -> VAR_POSITIONAL (raises)
        - POSTIIONAL_OR_KEYWORD -> VAR_POSITIONAL (raises)
        - VAR_POSTIIONAL -> VAR_POSITIONAL (success)
        - KEYWORD_ONLY -> VAR_POSITIONAL (raises)
        - VAR_KEYWROD -> VAR_POSITIONAL (raises)
        """
        from_param = self.make_param('from_', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_param = self.make_param('args', VAR_POSITIONAL)
        to_sig = inspect.Signature([to_param])

        if from_param.kind is VAR_POSITIONAL:
            pmap = Mapper.map_parameters(fsig, to_sig)
            assert pmap == {from_param.name: to_param.name}
            return

        with pytest.raises(TypeError) as excinfo:
            Mapper.map_parameters(fsig, to_sig)

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
    def test_map_parameters_to_var_keyword(self, from_kind):
        """
        Ensure the mapping **strategy** produced mapping *to* ``var-keyword``
        - POSITIONAL_ONLY -> VAR_POSITIONAL (success)
        - POSTIIONAL_OR_KEYWORD -> VAR_POSITIONAL (success)
        - VAR_POSTIIONAL -> VAR_POSITIONAL (raises)
        - KEYWORD_ONLY -> VAR_POSITIONAL (success)
        - VAR_KEYWROD -> VAR_POSITIONAL (success)
        """
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
                Mapper.map_parameters(fsig, to_sig)
            assert excinfo.value.args[0] == expected_exc.args[0]
            return
        pmap = Mapper.map_parameters(fsig, to_sig)
        assert pmap == {from_param.name: to_param.name}

    @pytest.mark.parametrize(('from_kind',), [
        pytest.param(POSITIONAL_ONLY, id='positional_only'),
        pytest.param(POSITIONAL_OR_KEYWORD, id='positional_or_keyword'),
        pytest.param(VAR_POSITIONAL, id='var_positional'),
        pytest.param(KEYWORD_ONLY, id='keyword_only'),
        pytest.param(VAR_KEYWORD, id='var_keyword'),
    ])
    def test_map_parameters_to_empty(self, from_kind):
        """
        Ensure mapping **strategy** failure when no interface param available.
        """
        from_param = self.make_param('a', from_kind)
        from_sig = inspect.Signature([from_param])
        fsig = FSignature.from_signature(from_sig)
        to_sig = inspect.Signature()

        with pytest.raises(TypeError) as excinfo:
            Mapper.map_parameters(fsig, to_sig)
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
    def test_map_parameters_from_hidden(self, to_kind):
        """
        Ensure mapping **strategy** success when no fparam provided.
        """
        fsig = FSignature()
        to_param = self.make_param('a', to_kind, default=1)
        to_sig = inspect.Signature([to_param])

        assert Mapper.map_parameters(fsig, to_sig) == {}