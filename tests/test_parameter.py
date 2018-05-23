import inspect
import types
from unittest.mock import Mock

import pytest

import forge._immutable as immutable
from forge._marker import empty
from forge._parameter import (
    Factory,
    FParameter,
    VarPositional,
    VarKeyword,
)
from forge._signature import CallArguments

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access

POSITIONAL_ONLY = FParameter.POSITIONAL_ONLY
POSITIONAL_OR_KEYWORD = FParameter.POSITIONAL_OR_KEYWORD
VAR_POSITIONAL = FParameter.VAR_POSITIONAL
KEYWORD_ONLY = FParameter.KEYWORD_ONLY
VAR_KEYWORD = FParameter.VAR_KEYWORD

dummy_func = lambda: None
dummy_converter = lambda ctx, name, value: (ctx, name, value)
dummy_validator = lambda ctx, name, value: None

FPARAM_DEFAULTS = dict(
    name=None,
    interface_name=None,
    default=empty,
    type=empty,
    converter=None,
    validator=None,
    bound=False,
    contextual=False,
    metadata=types.MappingProxyType({}),
)

FPARAM_POS_DEFAULTS = dict(  # type: ignore
    FPARAM_DEFAULTS,
    kind=POSITIONAL_ONLY,
)

FPARAM_POK_DEFAULTS = dict(  # type: ignore
    FPARAM_DEFAULTS,
    kind=POSITIONAL_OR_KEYWORD,
)

FPARAM_CTX_DEFAULTS = dict(  # type: ignore
    FPARAM_DEFAULTS,
    kind=POSITIONAL_OR_KEYWORD,
    contextual=True,
)

FPARAM_VPO_DEFAULTS = dict(  # type: ignore
    FPARAM_DEFAULTS,
    kind=VAR_POSITIONAL,
)

FPARAM_KWO_DEFAULTS = dict(  # type: ignore
    FPARAM_DEFAULTS,
    kind=KEYWORD_ONLY,
)

FPARAM_VKW_DEFAULTS = dict(  # type: ignore
    FPARAM_DEFAULTS,
    kind=VAR_KEYWORD,
)


class TestFactory:
    def test_cls(self):
        """
        Ensure factories are immutable
        """
        assert issubclass(Factory, immutable.Immutable)

    def test__repr__(self):
        """
        Ensure factories are pretty printable using the underlying callable's
        ``__qualname__``
        """
        def func():
            pass
        assert repr(Factory(func)) == '<Factory {}>'.format(func.__qualname__)

    def test__call__(self):
        """
        Ensure calls to the factory are transparently routed to the underlying
        callable
        """
        mock = Mock()
        factory = Factory(mock)
        factory()
        mock.assert_called_once_with()


class TestFParameter:
    # pylint: disable=R0904, too-many-public-methods
    @pytest.mark.parametrize(('default', 'factory', 'result'), [
        pytest.param(1, empty, 1, id='default'),
        pytest.param(empty, dummy_func, Factory(dummy_func), id='factory'),
        pytest.param(empty, empty, empty, id='neither'),
        pytest.param(1, dummy_func, None, id='both'),
    ])
    def test__init__default_or_factory(self, default, factory, result):
        """
        Ensure that ``default`` and ``factory`` calls to ``FParameter`` produce
        expected ``default`` ivar result (or raise).
        """
        kwargs = dict(kind=POSITIONAL_ONLY, default=default, factory=factory)

        if result is not None:
            assert FParameter(**kwargs).default == result
            return

        with pytest.raises(TypeError) as excinfo:
            FParameter(**kwargs)
        assert excinfo.value.args[0] == \
            'expected either "default" or "factory", received both'

    @pytest.mark.parametrize(('extras', 'raises'), [
        pytest.param({'default': 1}, False, id='default'),
        pytest.param({'factory': lambda: 1}, False, id='factory'),
        pytest.param({}, True, id='no_default_or_factory'),
    ])
    def test__init__bound_and_default(self, extras, raises):
        """
        Ensure that ``FParameter`` requires a ``default`` or ``factory`` value
        if ``bound=True``
        """
        kwargs = dict(
            kind=POSITIONAL_ONLY,
            bound=True,
            **extras,
        )

        if not raises:
            assert FParameter(**kwargs).bound
            return

        with pytest.raises(TypeError) as excinfo:
            FParameter(**kwargs)
        assert excinfo.value.args[0] == \
            'bound arguments must have a default value'

    @pytest.mark.parametrize(('kwargs', 'expected'), [
        pytest.param(
            {
                'kind': POSITIONAL_ONLY,
                'name': None,
                'interface_name': None,
            },
            '<missing>',
            id='name_missing',
        ),
        pytest.param(
            {
                'kind': POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
            },
            'a',
            id='named',
        ),
        pytest.param(
            {
                'kind': POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
                'default': None,
            },
            'a=None',
            id='named_default',
        ),
        pytest.param(
            {
                'kind': POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
                'type': int,
            },
            'a:int',
            id='named_type',
        ),
        pytest.param(
            {
                'kind': POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'b',
            },
            'a->b',
            id='named_mapping',
        ),
        pytest.param(
            {
                'kind': POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'b',
                'default': None,
                'type': int,
            },
            'a->b:int=None',
            id='named_mapping_anotation_default',
        ),
        pytest.param(
            {
                'kind': VAR_POSITIONAL,
                'name': 'a',
                'interface_name': 'a',
            },
            '*a',
            id='var_positional',
        ),
        pytest.param(
            {
                'kind': VAR_KEYWORD,
                'name': 'a',
                'interface_name': 'a',
            },
            '**a',
            id='var_keyword',
        ),
    ])
    def test__str__and__repr__(self, kwargs, expected):
        """
        Ensure pretty printing for ``FParameter``
        """
        fparam = FParameter(**kwargs)
        assert str(fparam) == expected
        assert repr(fparam) == '<FParameter "{}">'.format(expected)

    @pytest.mark.parametrize(('in_val', 'out_val'), [
        pytest.param(empty, 'default', id='empty'),
        pytest.param(*[object()] * 2, id='non_factory'), # (obj, obj)
        pytest.param(Factory(lambda: 'value'), 'value', id='factory'),
    ])
    def test_apply_default(self, in_val, out_val):
        """
        Ensure that ``apply_default`` returns:
        1) the non-empty value (if a ``Factory`` ins is supplied)
        2) the factory-default value (if a ``Factory`` ins is supplied)
        3) the default value (if ``empty`` is supplied)
        """
        fparam = FParameter(
            POSITIONAL_ONLY,
            default='default',
        )
        assert fparam.apply_default(in_val) == out_val

    @pytest.mark.parametrize(('converter', 'ctx', 'name', 'value', 'to_out'), [
        pytest.param(
            lambda ctx, name, value: (ctx, name, value),
            object(),
            'myparam',
            object(),
            lambda ctx, name, value: (ctx, name, value),
            id='unit',
        ),
        pytest.param(
            [lambda ctx, name, value: (ctx, name, value) for i in range(2)],
            object(),
            'myparam',
            object(),
            lambda ctx, name, value: (ctx, name, (ctx, name, value)),
            id='list',
        ),
        pytest.param(
            None,
            object(),
            'myparam',
            object(),
            lambda ctx, name, value: value,
            id='none',
        ),
    ])
    def test_apply_conversion(self, converter, ctx, name, value, to_out):
        """
        Ensure conversion works on an individual converter or iterable
        """
        fparam = FParameter(
            POSITIONAL_ONLY,
            name=name,
            converter=converter,
        )
        assert fparam.apply_conversion(ctx, value) == to_out(ctx, name, value)

    @pytest.mark.parametrize(('has_validation',), [(True,), (False,)])
    def test_apply_validation(self, has_validation):
        """
        Ensure validation works on an individual validator
        """
        called_with = None
        def validator(*args, **kwargs):
            nonlocal called_with
            called_with = CallArguments(*args, **kwargs)

        ctx, name, value = object(), 'myparam', object()

        fparam = FParameter(
            POSITIONAL_ONLY,
            name=name,
            validator=validator if has_validation else None,
        )
        fparam.apply_validation(ctx, value)
        if has_validation:
            assert called_with.args == (ctx, name, value)
        else:
            assert called_with is None

    def test_apply_validation_multiple(self):
        """
        Ensure validation works on an iterable of validators
        """
        called_with = []
        def validator(*args, **kwargs):
            nonlocal called_with
            called_with.append(CallArguments(*args, **kwargs))

        ctx, name, value = object(), 'myparam', object()

        fparam = FParameter(
            POSITIONAL_ONLY,
            name=name,
            validator=[validator, validator],
        )

        fparam.apply_validation(ctx, value)

        assert len(called_with) == 2
        assert called_with[0] == called_with[1] == \
            CallArguments(ctx, name, value)

    @pytest.mark.parametrize(('is_factory',), [
        pytest.param(False, id='non_factory'),
        pytest.param(True, id='factory'),
    ])
    def test__call__(self, is_factory):
        """
        Ensure that calling an ``FParameter`` calls into:
        1) ``apply_default`` ->
        2) ``apply_converter`` ->
        3) ``apply_validator`` ->
        and returns the expected value
        """
        mock = Mock()
        ctx, name = object(), 'myparam'
        value = Factory(mock) if is_factory else mock
        converter, validator = Mock(), Mock()
        fparam = FParameter(
            POSITIONAL_ONLY,
            name=name,
            converter=converter,
            validator=validator,
        )

        assert fparam(ctx, value) == converter.return_value
        validator.assert_called_once_with(ctx, name, converter.return_value)

        if is_factory:
            converter.assert_called_once_with(ctx, name, mock.return_value)
            mock.assert_called_once_with()
        else:
            converter.assert_called_once_with(ctx, name, mock)
            mock.assert_not_called()


    @pytest.mark.parametrize(('rkey', 'rval'), [
        pytest.param('kind', KEYWORD_ONLY, id='kind'),
        pytest.param('default', 1, id='default'),
        pytest.param('factory', dummy_func, id='factory'),
        pytest.param('type', int, id='type'),
        pytest.param('name', 'b', id='name'),
        pytest.param('interface_name', 'b', id='interface_name'),
        pytest.param('converter', dummy_converter, id='converter'),
        pytest.param('validator', dummy_validator, id='validator'),
        pytest.param('bound', True, id='bound'),
        pytest.param('contextual', True, id='contextual'),
        pytest.param('metadata', {'new': 'meta'}, id='metadata'),
    ])
    def test_replace(self, rkey, rval):
        """
        Ensure that ``replace`` creates an evolved instance
        """
        fparam = FParameter(
            kind=POSITIONAL_ONLY,
            name=None,
            interface_name=None,
            default=None,
        )
        # pylint: disable=E1101, no-member
        fparam2 = fparam.replace(**{rkey: rval})
        for k, v in immutable.asdict(fparam2).items():
            if k in ('name', 'interface_name') and \
                rkey in ('name', 'interface_name'):
                v = rval
            elif k == 'default' and rkey == 'factory':
                v = Factory(dummy_func)
            assert getattr(fparam2, k) == v

    def test_parameter(self):
        """
        Ensure the ``parameter`` factory produces an expected instance of
        ``inspect.Parameter``
        """
        kwargs = dict(
            kind=POSITIONAL_ONLY,
            name='a',
            interface_name='b',
            default=None,
            type=int,
        )
        param = FParameter(**kwargs).parameter
        assert param.kind == kwargs['kind']
        assert param.name == kwargs['name']
        assert param.default == kwargs['default']
        assert param.annotation == kwargs['type']

    def test_parameter_wo_names_raises(self):
        """
        Ensure that attempting to produce an instance of ``inspect.Parameter``
        without an ``FParameter`` ``name`` or ``interface_name`` raises.
        """
        fparam = FParameter(
            kind=POSITIONAL_ONLY,
            name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            fparam.parameter
        assert excinfo.value.args[0] == 'Cannot generate an unnamed parameter'

    def test_defaults(self):
        """
        Ensure that FPARAM_DEFAULTS (used in this module's testing) is accurate.
        """
        fparam = FParameter(POSITIONAL_ONLY)
        assert fparam.kind == POSITIONAL_ONLY
        for k, v in FPARAM_DEFAULTS.items():
            assert getattr(fparam, k) == v

    def test_from_parameter(self):
        """
        Ensure expected construction of an instance of ``FParameter`` from an
        instance of ``inspect.Parameter``
        """
        kwargs = dict(
            name='a',
            kind=POSITIONAL_ONLY,
            annotation=int,
            default=3,
        )
        param = inspect.Parameter(**kwargs)
        fparam = FParameter.from_parameter(param)
        for k, v in dict(
                FPARAM_DEFAULTS,
                kind=kwargs['kind'],
                name=kwargs['name'],
                interface_name=kwargs['name'],
                type=kwargs['annotation'],
                default=kwargs['default'],
            ).items():
            assert getattr(fparam, k) == v

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='name',
        ),
        pytest.param(
            {'name': 'a', 'interface_name': 'b'},
            {'name': 'a', 'interface_name': 'b'},
            id='name_and_interface_name',
        ),
        pytest.param(
            {'default': 1},
            {'default': 1},
            id='default',
        ),
        pytest.param(
            {'factory': dummy_func},
            {'default': Factory(dummy_func)},
            id='factory',
        ),
    ])
    def test_create_positional_only(self, extra_in, extra_out):
        """
        Ensure the expected construction of a ``positional-only`` ``FParameter``
        """
        kwargs = dict(
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        fparam = FParameter.create_positional_only(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_POS_DEFAULTS, **kwargs, **extra_out}

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='name',
        ),
        pytest.param(
            {'name': 'a', 'interface_name': 'b'},
            {'name': 'a', 'interface_name': 'b'},
            id='name_and_interface_name',
        ),
        pytest.param(
            {'default': 1},
            {'default': 1},
            id='default',
        ),
        pytest.param(
            {'factory': dummy_func},
            {'default': Factory(dummy_func)},
            id='factory',
        ),
    ])
    def test_create_positional_or_keyword(self, extra_in, extra_out):
        """
        Ensure the expected construction of a ``positional-or-keyword``
        ``FParameter``
        """
        kwargs = dict(
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        fparam = FParameter.create_positional_or_keyword(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_POK_DEFAULTS, **kwargs, **extra_out}

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='name',
        ),
        pytest.param(
            {'name': 'a', 'interface_name': 'b'},
            {'name': 'a', 'interface_name': 'b'},
            id='name_and_interface_name',
        ),
    ])
    def test_create_contextual(self, extra_in, extra_out):
        """
        Ensure the expected construction of a ``contextual``
        ``positional-or-keyword`` ``FParameter``
        """
        kwargs = dict(
            type=int,
            metadata={'meta': 'data'},
        )
        fparam = FParameter.create_contextual(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_CTX_DEFAULTS, **kwargs, **extra_out}

    def test_create_var_positional(self):
        """
        Ensure the expected construction of a ``var-positional`` ``FParameter``
        """
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        fparam = FParameter.create_var_positional(**kwargs)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VPO_DEFAULTS,
            **kwargs,
            interface_name=kwargs['name'],
        )

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {'default': 1},
            {'default': 1},
            id='default',
        ),
        pytest.param(
            {'factory': dummy_func},
            {'default': Factory(dummy_func)},
            id='factory',
        ),
    ])
    def test_create_keyword_only(self, extra_in, extra_out):
        """
        Ensure the expected construction of a ``keyword-only`` ``FParameter``
        """
        kwargs = dict(
            interface_name='a',
            name='b',
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        fparam = FParameter.create_positional_or_keyword(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_POK_DEFAULTS, **kwargs, **extra_out}

    def test_create_var_keyword(self):
        """
        Ensure the expected construction of a ``var-keyword`` ``FParameter``
        """
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        fparam = FParameter.create_var_keyword(**kwargs)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VKW_DEFAULTS,
            **kwargs,
            interface_name=kwargs['name'],
        )


class TestVarPositional:
    @staticmethod
    def assert_iterable_and_get_fparam(varp):
        """
        Helper function to iterate on the ``VarPostional`` instance and get the
        underlying ``FParameter``
        """
        varplist = list(varp)
        assert len(varplist) == 1
        return varplist[0]

    def test_defaults(self):
        """
        Ensure standard defaults for ``VarPositional`` instances.
        """
        varp = VarPositional()
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert fparam.name == 'args'
        assert not fparam.converter
        assert not fparam.validator
        assert not fparam.metadata

    def test_new(self):
        """
        Ensure that arguments to ``VarPositional`` result in an expected
        underlying implementation of ``FParameter``.
        """
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        varp = VarPositional(**kwargs)
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VPO_DEFAULTS,
            **kwargs,
            interface_name=kwargs['name'],
        )

    def test__call__(self):
        """
        Ensure that ``VarPositional.__call__`` is a factory method
        """
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        varp = VarPositional()(**kwargs)
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VPO_DEFAULTS,
            **kwargs,
            interface_name=kwargs['name'],
        )

class TestVarKeyword:
    @staticmethod
    def assert_mapping_and_get_fparam(vark):
        """
        Helper function to iterate on the ``VarKeyword`` instance and get the
        underlying ``FParameter``
        """
        varklist = list(vark.items())
        assert len(varklist) == 1
        return varklist[0]

    def test_defaults(self):
        """
        Ensure standard defaults for ``VarKeyword`` instances.
        """
        vark = VarKeyword()
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert name == 'kwargs'
        assert not fparam.converter
        assert not fparam.validator
        assert not fparam.metadata

    def test_new(self):
        """
        Ensure that arguments to ``VarKeyword`` result in an expected underlying
        implementation of ``FParameter``.
        """
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        vark = VarKeyword(**kwargs)
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert isinstance(fparam, FParameter)
        assert name == kwargs['name']
        assert immutable.asdict(fparam) == dict(
            FPARAM_VKW_DEFAULTS,
            **kwargs,
            interface_name=kwargs['name'],
        )

    def test__call__(self):
        """
        Ensure that ``VarKeyword.__call__`` is a factory method
        """
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
            metadata={'meta': 'data'},
        )
        vark = VarKeyword()(**kwargs)
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert isinstance(fparam, FParameter)
        assert name == kwargs['name']
        assert immutable.asdict(fparam) == dict(
            FPARAM_VKW_DEFAULTS,
            **kwargs,
            interface_name=kwargs['name'],
        )

    def test_mapping(self):
        """
        Ensure that mapping produced by ``VarKeyword`` maps the instance
        ``name`` to the generated ``FParameter`` (for appropriate usage with
        ``FSignature``)
        """
        vark = VarKeyword()
        assert vark.name in vark
        assert '{}_'.format(vark.name) not in vark
        assert len(vark) == 1
        assert list(vark) == [vark.name]