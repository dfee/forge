import inspect
import types
import typing
from collections import OrderedDict
from unittest.mock import Mock

import pytest

import forge
import forge._immutable as immutable
import forge._signature
from forge._marker import empty
from forge._signature import (
    KEYWORD_ONLY,
    POSITIONAL_ONLY,
    POSITIONAL_OR_KEYWORD,
    VAR_KEYWORD,
    VAR_POSITIONAL,
    Factory,
    FParameter,
    FParameterSequence,
    FSignature,
    VarKeyword,
    VarPositional,
    finditer,
    fsignature,
    get_context_parameter,
    get_var_keyword_parameter,
    get_var_positional_parameter,
)
from forge._utils import CallArguments

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0621, redefined-outer-name


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
    FPARAM_POK_DEFAULTS,
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
    def test_cls_constants(self):
        """
        Ensure cls constants for ``FParameter``
        """
        for k, v in {
                'empty': empty,
                'POSITIONAL_ONLY': POSITIONAL_ONLY,
                'POSITIONAL_OR_KEYWORD': POSITIONAL_OR_KEYWORD,
                'VAR_POSITIONAL': VAR_POSITIONAL,
                'KEYWORD_ONLY': KEYWORD_ONLY,
                'VAR_KEYWORD': VAR_KEYWORD,
            }.items():
            assert getattr(FParameter, k) is v

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

    def test_native(self):
        """
        Ensure the ``native`` property produces an expected instance of
        ``inspect.Parameter``
        """
        kwargs = dict(
            kind=POSITIONAL_ONLY,
            name='a',
            interface_name='b',
            default=None,
            type=int,
        )
        param = FParameter(**kwargs).native
        assert param.kind == kwargs['kind']
        assert param.name == kwargs['name']
        assert param.default == kwargs['default']
        assert param.annotation == kwargs['type']

    def test_native_wo_names_raises(self):
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
            fparam.native
        assert excinfo.value.args[0] == 'Cannot generate an unnamed parameter'

    def test_defaults(self):
        """
        Ensure that FPARAM_DEFAULTS (used in this module's testing) is accurate.
        """
        fparam = FParameter(POSITIONAL_ONLY)
        assert fparam.kind == POSITIONAL_ONLY
        for k, v in FPARAM_DEFAULTS.items():
            assert getattr(fparam, k) == v

    @pytest.mark.parametrize(('annotation', 'default'), [
        pytest.param(int, 3, id='annotation_and_default'),
        pytest.param(empty.native, 3, id='empty_annotation'),
        pytest.param(int, empty.native, id='empty_default'),
    ])
    def test_from_native(self, annotation, default):
        """
        Ensure expected construction of an instance of ``FParameter`` from an
        instance of ``inspect.Parameter``
        """
        kwargs = dict(
            name='a',
            kind=POSITIONAL_ONLY,
            annotation=annotation,
            default=default,
        )
        param = inspect.Parameter(**kwargs)
        fparam = FParameter.from_native(param)
        for k, v in dict(
                FPARAM_DEFAULTS,
                kind=kwargs['kind'],
                name=kwargs['name'],
                interface_name=kwargs['name'],
                type=kwargs['annotation'] \
                    if kwargs['annotation'] is not empty.native \
                    else empty,
                default=kwargs['default'] \
                    if kwargs['default'] is not empty.native \
                    else empty,
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


class TestParameterConvenience:
    @pytest.mark.parametrize(('name', 'obj'), [
        ('pos', forge.FParameter.create_positional_only),
        ('pok', forge.FParameter.create_positional_or_keyword),
        ('arg', forge.FParameter.create_positional_or_keyword),
        ('ctx', forge.FParameter.create_contextual),
        ('vpo', forge.FParameter.create_var_positional),
        ('kwo', forge.FParameter.create_keyword_only),
        ('kwarg', forge.FParameter.create_keyword_only),
        ('vkw', forge.FParameter.create_var_keyword),
    ])
    def test_constructors(self, name, obj):
        """
        Assert constructor nicknames are what we exect them to be.
        """
        assert getattr(forge, name) == obj

    def test_self(self):
        """
        Assert ``forge.self`` is what we expect it to be.
        """
        assert forge.self == forge.FParameter(
            forge.FParameter.POSITIONAL_OR_KEYWORD,
            name='self',
            interface_name='self',
            contextual=True,
        )

    def test_cls(self):
        """
        Assert ``forge.cls`` is what we expect it to be.
        """
        assert forge.cls == forge.FParameter(
            forge.FParameter.POSITIONAL_OR_KEYWORD,
            name='cls',
            interface_name='cls',
            contextual=True,
        )

    def test_args(self):
        """
        Assert ``forge.args`` is what we expect it to be.
        """
        args = forge.args
        assert isinstance(args, forge._signature.VarPositional)
        assert args.name == 'args'
        assert args.converter is None
        assert args.validator is None

    def test_kwargs(self):
        """
        Assert ``forge.kwargs`` is what we expect it to be.
        """
        kwargs = forge.kwargs
        assert isinstance(kwargs, forge._signature.VarKeyword)
        assert kwargs.name == 'kwargs'
        assert kwargs.converter is None
        assert kwargs.validator is None


class TestFParameterSequence:
    # Begin collections.abc.Mapping Tests
    def test__getitem__str(self):
        """
        Ensure that ``__getitem__`` retrieves fparams by ``name``
        (an abstract collections.abc.Mapping method)
        """
        fparam = forge.arg('a')
        fpseq = FParameterSequence([fparam])
        assert fpseq['a'] is fparam

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
        fpseq = FParameterSequence(list(fparams.values()))
        assert fpseq[start:end] == [fparams[e] for e in expected]

    def test__len__(self):
        """
        Ensure that ``__len__`` retrieves a count of the fparams
        (an abstract collections.abc.Mapping method)
        """
        assert len(FParameterSequence([forge.arg('a')])) == 1

    def test__iter__(self):
        """
        Ensure that ``__iter__`` returns an iterator over all fparams
        (an abstract collections.abc.Mapping method)
        """
        fparam = forge.arg('a')
        fpseq = FParameterSequence([fparam])
        assert dict(fpseq) == {fparam.name: fparam}
    # End collections.abc.Mapping Tests

    @pytest.mark.parametrize(('params', 'expected'), [
        pytest.param(
            [forge.arg('a'), forge.arg('b')],
            '(a, b)',
            id='valid',
        ),
        pytest.param(
            [forge.arg('a'), forge.pos('b')],
            '(a, b, /)',
            id='invalid',
        ),
    ])
    def test__str__and__repr__(self, params, expected):
        seq = FParameterSequence(params, validate=False)
        assert str(seq) == expected
        assert repr(seq) == '<FParameterSequence {}>'.format(expected)

    def test_validate_non_fparameter_raises(self):
        """
        Ensure that non-fparams raise a TypeError by validating a
        ``inspect.Parameter``
        """
        param = inspect.Parameter('x', POSITIONAL_ONLY)
        with pytest.raises(TypeError) as excinfo:
            FParameterSequence([param])
        assert excinfo.value.args[0] == \
            "Received non-FParameter '{}'".format(param)

    def test_validate_unnamed_fparameter_raises(self):
        """
        Ensure that fparams must be named
        """
        arg = forge.arg()
        with pytest.raises(ValueError) as excinfo:
            FParameterSequence([arg])
        assert excinfo.value.args[0] == \
            "Received unnamed parameter: '{}'".format(arg)

    def test_validate_late_contextual_fparam_raises(self):
        """
        Ensure that non-first fparams cannot be contextual
        """
        with pytest.raises(TypeError) as excinfo:
            FParameterSequence([forge.arg('a'), forge.ctx('self')])
        assert excinfo.value.args[0] == \
            'Only the first parameter can be contextual'

    def test_validate_multiple_interface_name_raises(self):
        """
        Ensure that a ``interface_name`` between multiple fparams raises
        """
        with pytest.raises(ValueError) as excinfo:
            FParameterSequence([forge.arg('a1', 'b'), forge.arg('a2', 'b')])
        assert excinfo.value.args[0] == \
            "Received multiple parameters with interface_name 'b'"

    def test_validate_multiple_name_raises(self):
        """
        Ensure that a ``name`` between multiple fparams raises
        """
        with pytest.raises(ValueError) as excinfo:
            FParameterSequence([forge.arg('a', 'b1'), forge.arg('a', 'b2')])
        assert excinfo.value.args[0] == \
            "Received multiple parameters with name 'a'"

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
            FParameterSequence(params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-positional parameters'

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
            FParameterSequence(params)
        assert excinfo.value.args[0] == \
            'Received multiple variable-keyword parameters'

    def test_validate_out_of_order_fparameters_raises(self):
        """
        Ensure that fparams misordered (by ``kind``) raise
        """
        kwarg_ = forge.kwarg('kwarg')
        arg_ = forge.arg('arg')
        with pytest.raises(SyntaxError) as excinfo:
            FParameterSequence([kwarg_, arg_])
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
            FParameterSequence([default, nondefault])
        assert excinfo.value.args[0] == (
            'non-default parameter follows default parameter'
        )

    def test_validate_default_kw_only_follows_non_default_kw_only(self):
        """
        Ensure that ``keyword-only`` fparams with default values can come
        after fparams without default values (only true for ``keyword-only``!)
        """
        FParameterSequence([
            forge.kwarg('a', default=None),
            forge.kwarg('b'),
        ])


class TestFSignature:
    def test_fsignature(self):
        assert fsignature == FSignature.from_callable

    def test__str__and__repr__(self):
        """
        Ensure printing and repr of FSignature
        """
        sig = FSignature([forge.self])
        assert str(sig) == '(self)'
        assert repr(sig) == '<FSignature (self)>'

    @pytest.mark.parametrize(('bound',), [(True,), (False,)])
    def test_native(self, bound):
        """
        Ensure the generation of an ``inspect.Signature``
        """
        fsig = FSignature(
            [forge.arg('x', bound=bound, default=1)],
            return_annotation=int,
        )
        if bound:
            assert fsig.native == inspect.Signature(return_annotation=int)
            return

        assert fsig.native == inspect.Signature(
            [inspect.Parameter('x', POSITIONAL_OR_KEYWORD, default=1)],
            return_annotation=int,
        )

    @pytest.mark.parametrize(('return_annotation',), [
        pytest.param(empty.native, id='empty'),
        pytest.param(bool, id='bool'),
    ])
    def test_from_native(self, return_annotation):
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
        ], return_annotation=return_annotation)
        fsig = FSignature.from_native(sig)
        assert len(fsig.parameters) == 1
        assert fsig.parameters['a'] == FParameter(
            kind=POSITIONAL_OR_KEYWORD,
            name='a',
            interface_name='a',
            default=0,
            type=int,
        )
        assert fsig.return_annotation == return_annotation

    def test_from_callable(self):
        """
        Ensure a ``FSignature`` can be adequately generated from a callable
        """
        def func(a: int = 0):
            return a
        fsig = FSignature.from_callable(func)
        assert len(fsig.parameters) == 1
        assert fsig.parameters['a'] == FParameter(
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

    @pytest.mark.parametrize(('in_', 'kwargs', 'out_'), [
        pytest.param(
            FSignature(),
            dict(parameters=[forge.arg('arg')]),
            FSignature([forge.arg('arg')]),
            id='parameters',
        ),
        pytest.param(
            FSignature(),
            dict(
                parameters=[forge.arg('arg'), forge.pos('pos')],
                __validate_parameters__=False,
            ),
            FSignature([forge.arg('arg'), forge.pos('pos')]),
            id='parameters_invalid',
        ),
        pytest.param(
            FSignature(),
            dict(return_annotation=int),
            FSignature(return_annotation=int),
            id='return_annotation'
        ),
    ])
    def test_replace(self, in_, kwargs, out_):
        assert in_.replace(**kwargs) == out_


class TestSignatureConvenience:
    @pytest.mark.parametrize(('name', 'obj'), [
        ('fsignature', forge.FSignature.from_callable),
    ])
    def test_constructors(self, name, obj):
        """
        Assert constructor nicknames are what we exect them to be.
        """
        assert getattr(forge, name) == obj


@pytest.mark.parametrize(('selector', 'expected_name'), [
    # str
    pytest.param('b', 'b', id='find_by_str'),
    pytest.param('c', None, id='find_by_str_DNE'),
    # iter str
    pytest.param(('b', 'c'), 'b', id='find_by_iter_str'),
    pytest.param(('c', 'd'), None, id='find_by_iter_str_DNE'),
    # callable
    pytest.param(
        lambda param: param.kind is POSITIONAL_OR_KEYWORD,
        'b',
        id='find_by_callable',
    ),
    pytest.param(
        lambda param: param.kind is VAR_KEYWORD,
        None,
        id='find_by_callable_DNE',
    ),
])
@pytest.mark.parametrize('kls', (inspect.Parameter, FParameter))
def test_finditer(kls, selector, expected_name):
    """
    Ensure that finditer matches the correct ``inspect.Parameter`` or
    ``FParameter`` based on a selector of:
    - str
    - iterable of strings
    - callable
    """
    params = OrderedDict([
        ('a', kls(name='a', kind=POSITIONAL_ONLY)),
        ('b', kls(name='b', kind=POSITIONAL_OR_KEYWORD)),
    ])
    result = finditer(params.values(), selector)
    assert isinstance(result, typing.Iterator)
    if expected_name:
        assert list(result) == [params[expected_name]]
    else:
        assert not list(result)


@pytest.mark.parametrize(('params', 'expected'), [
    ((forge.ctx('a'),), forge.ctx('a')),
    ((forge.arg('a'),), None),
])
def test_get_context_parameter(params, expected):
    """
    Ensure the ``contextual`` param (or None) is returned
    """
    assert get_context_parameter(params) == expected


IPARAMS = OrderedDict([
    (param.name, param) for param in [
        inspect.Parameter('pos', POSITIONAL_ONLY),
        inspect.Parameter('arg', POSITIONAL_OR_KEYWORD),
        inspect.Parameter('args', VAR_POSITIONAL),
        inspect.Parameter('kwarg', KEYWORD_ONLY),
        inspect.Parameter('kwargs', VAR_KEYWORD),
    ]
])
FPARAMS = OrderedDict([
    (param.name, param) for param in [
        forge.pos('pos'),
        forge.arg('arg'),
        forge.vpo('args'),
        forge.kwarg('kwarg'),
        forge.vkw('kwargs'),
    ]
])


@pytest.mark.parametrize(('params', 'expected'), [
    (list(IPARAMS.values()), IPARAMS['args']),
    (list(FPARAMS.values()), FPARAMS['args']),
    ((), None),
])
def test_get_var_positional_parameter(params, expected):
    """
    Ensure the ``var-positional`` param (or None) is returned for:
    - ``inspect.Parameter``
    - ``forge.FParameter``
    """
    assert get_var_positional_parameter(params) is expected


@pytest.mark.parametrize(('params', 'expected'), [
    (list(IPARAMS.values()), IPARAMS['kwargs']),
    (list(FPARAMS.values()), FPARAMS['kwargs']),
    ((), None),
])
def test_get_var_keyword_parameter(params, expected):
    """
    Ensure the ``var-keyword`` param (or None) is returned for:
    - ``inspect.Parameter``
    - ``forge.FParameter``
    """
    assert get_var_keyword_parameter(params) is expected