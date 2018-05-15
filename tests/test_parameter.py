import inspect

import pytest

import forge._parameter
from forge._parameter import (
    FParameter,
    VarPositional,
    VarKeyword,
    cls_,
    self_,
)

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access

empty = inspect.Parameter.empty

dummy_converter = lambda ctx, name, value: (ctx, name, value)
dummy_validator = lambda ctx, name, value: None

FPARAM_DEFAULTS = dict(
    default=inspect.Parameter.empty,
    type=inspect.Parameter.empty,
    converter=None,
    validator=None,
    is_contextual=False
)

FPARAM_POS_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_ONLY,
    is_contextual=False,
)

FPARAM_POK_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    is_contextual=False,
)

FPARAM_CTX_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    is_contextual=True,
    default=empty,
    converter=None,
    validator=None,
)

FPARAM_VPO_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.VAR_POSITIONAL,
    is_contextual=False,
    default=empty,
    type=empty,
)

FPARAM_KWO_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.KEYWORD_ONLY,
    is_contextual=False,
)

FPARAM_VKW_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.VAR_KEYWORD,
    is_contextual=False,
    default=empty,
    type=empty,
)


class TestFParameter:
    # pylint: disable=E1101, no-member
    @pytest.mark.parametrize(('kwargs', 'expected'), [
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': None,
                'interface_name': None,
            },
            '<missing>',
            id='name_missing',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
            },
            'a',
            id='named',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
                'default': None,
            },
            'a=None',
            id='named_default',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
                'type': int,
            },
            'a:int',
            id='named_type',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'b',
            },
            'a->b',
            id='named_mapping',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
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
                'kind': inspect.Parameter.VAR_POSITIONAL,
                'name': 'a',
                'interface_name': 'a',
            },
            '*a',
            id='var_positional',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.VAR_KEYWORD,
                'name': 'a',
                'interface_name': 'a',
            },
            '**a',
            id='var_keyword',
        ),
    ])
    def test__str__and__repr__(self, kwargs, expected):
        fparam = FParameter(**kwargs)
        assert str(fparam) == expected
        assert repr(fparam) == '<FParameter "{}">'.format(expected)

    @pytest.mark.parametrize(('rkey', 'rval'), [
        pytest.param('kind', inspect.Parameter.KEYWORD_ONLY, id='kind'),
        pytest.param('default', 1, id='default'),
        pytest.param('type', int, id='type'),
        pytest.param('name', 'b', id='name'),
        pytest.param('interface_name', 'b', id='interface_name'),
        pytest.param('converter', dummy_converter, id='converter'),
        pytest.param('validator', dummy_validator, id='validator'),
    ])
    def test_replace(self, rkey, rval):
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=None,
            interface_name=None,
        )
        fparam2 = fparam.replace(**{rkey: rval}) # pylint: disable=E1101, no-member
        for k, v in dict(fparam._asdict(), **{rkey: rval}).items():
            if k in ('name', 'interface_name') and \
                rkey in ('name', 'interface_name'):
                v = rval
            assert getattr(fparam2, k) == v

    def test_parameter(self):
        kwargs = dict(
            kind=inspect.Parameter.POSITIONAL_ONLY,
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
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            fparam.parameter
        assert excinfo.value.args[0] == 'Cannot generate an unnamed parameter'

    def test_interface_parameter(self):
        kwargs = dict(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name='a',
            interface_name='b',
            default=None,
            type=int,
        )
        param = FParameter(**kwargs).interface_parameter
        assert param.kind == kwargs['kind']
        assert param.name == kwargs['interface_name']
        assert param.default == kwargs['default']
        assert param.annotation == kwargs['type']

    def test_interface_parameter_wo_names_raises(self):
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            fparam.interface_parameter
        assert excinfo.value.args[0] == 'Cannot generate an unnamed parameter'

    def test_defaults(self):
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name='dummy',
            interface_name='dummy',
        )
        assert fparam.kind == inspect.Parameter.POSITIONAL_ONLY
        for k, v in FPARAM_DEFAULTS.items():
            assert getattr(fparam, k) == v

    def test_from_parameter(self):
        kwargs = dict(
            name='a',
            kind=inspect.Parameter.POSITIONAL_ONLY,
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
    ])
    def test_create_positional_only(self, extra_in, extra_out):
        kwargs = dict(
            default=None,
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_positional_only(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == {**FPARAM_POS_DEFAULTS, **kwargs, **extra_out}

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
    def test_create_positional_or_keyword(self, extra_in, extra_out):
        kwargs = dict(
            default=None,
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_positional_or_keyword(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == {**FPARAM_POK_DEFAULTS, **kwargs, **extra_out}

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
        kwargs = dict(type=int)
        fparam = FParameter.create_contextual(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == {**FPARAM_CTX_DEFAULTS, **kwargs, **extra_out}

    def test_create_var_positional(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_var_positional(**kwargs)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == dict(
            FPARAM_VPO_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test_create_keyword_only(self):
        kwargs = dict(
            interface_name='a',
            name='b',
            default=None,
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_keyword_only(**kwargs)
        assert isinstance(fparam, FParameter)
        for k, v in dict(FPARAM_KWO_DEFAULTS, **kwargs).items():
            assert getattr(fparam, k) == v

    def test_create_var_keyword(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_var_keyword(**kwargs)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == dict(
            FPARAM_VKW_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )


class TestVarPositional:
    @staticmethod
    def assert_iterable_and_get_fparam(varp):
        varplist = list(varp)
        assert len(varplist) == 1
        return varplist[0]

    def test_new(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        varp = VarPositional()(**kwargs)
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == dict(
            FPARAM_VPO_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test__call__(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        varp = VarPositional(**kwargs)
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert isinstance(fparam, FParameter)
        assert fparam._asdict() == dict(
            FPARAM_VPO_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

class TestVarKeyword:
    @staticmethod
    def assert_mapping_and_get_fparam(vark):
        varklist = list(vark.items())
        assert len(varklist) == 1
        return varklist[0]

    def test_new(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        vark = VarKeyword(**kwargs)
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert isinstance(fparam, FParameter)
        assert name == kwargs['name']
        assert fparam._asdict() == dict(
            FPARAM_VKW_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test__call__(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        vark = VarKeyword()(**kwargs)
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert isinstance(fparam, FParameter)
        assert name == kwargs['name']
        assert fparam._asdict() == dict(
            FPARAM_VKW_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test_mapping(self):
        vark = VarKeyword()
        assert vark.name in vark
        assert '{}_'.format(vark.name) not in vark
        assert len(vark) == 1
        assert list(vark) == [vark.name]


class TestConvenience:
    def test_constructors(self):
        # pylint: disable=E1101, no-member
        for conv, method in [
                ('pos', FParameter.create_positional_only),
                ('arg', FParameter.create_positional_or_keyword),
                ('ctx', FParameter.create_contextual),
                ('kwarg', FParameter.create_keyword_only),
            ]:
            assert getattr(forge._parameter, conv) == method

    def test_self_(self):
        assert isinstance(self_, FParameter)
        assert self_._asdict() == dict(
            **FPARAM_CTX_DEFAULTS,
            name='self',
            interface_name='self',
        )

    def test_cls_(self):
        assert isinstance(cls_, FParameter)
        assert cls_._asdict() == dict(
            **FPARAM_CTX_DEFAULTS,
            name='cls',
            interface_name='cls',
        )

    def test_args(self):
        args = forge._parameter.args
        assert isinstance(args, VarPositional)
        assert args.name == 'args'
        assert args.converter is None
        assert args.validator is None

    def test_kwargs(self):
        kwargs = forge._parameter.kwargs
        assert isinstance(kwargs, VarKeyword)
        assert kwargs.name == 'kwargs'
        assert kwargs.converter is None
        assert kwargs.validator is None