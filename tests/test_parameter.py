import inspect

import pytest

import forge._parameter
from forge._parameter import (
    ParameterMap,
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

PMAP_DEFAULTS = dict(
    default=inspect.Parameter.empty,
    annotation=inspect.Parameter.empty,
    converter=None,
    validator=None,
    is_contextual=False
)

PMAP_POS_DEFAULTS = dict(
    PMAP_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_ONLY,
    is_contextual=False,
)

PMAP_POK_DEFAULTS = dict(
    PMAP_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    is_contextual=False,
)

PMAP_CTX_DEFAULTS = dict(
    PMAP_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    is_contextual=True,
    default=empty,
    converter=None,
    validator=None,
)

PMAP_VPO_DEFAULTS = dict(
    PMAP_DEFAULTS,
    kind=inspect.Parameter.VAR_POSITIONAL,
    is_contextual=False,
    default=empty,
    annotation=empty,
)

PMAP_KWO_DEFAULTS = dict(
    PMAP_DEFAULTS,
    kind=inspect.Parameter.KEYWORD_ONLY,
    is_contextual=False,
)

PMAP_VKW_DEFAULTS = dict(
    PMAP_DEFAULTS,
    kind=inspect.Parameter.VAR_KEYWORD,
    is_contextual=False,
    default=empty,
    annotation=empty,
)


class TestParameterMap:
    # pylint: disable=E1101, no-member
    @pytest.mark.parametrize(('kwargs', 'expected'), [
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'public_name': None,
                'interface_name': None,
            },
            '<missing>',
            id='name_missing',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'public_name': 'a',
                'interface_name': 'a',
            },
            'a',
            id='named',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'public_name': 'a',
                'interface_name': 'a',
                'default': None,
            },
            'a=None',
            id='named_default',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'public_name': 'a',
                'interface_name': 'a',
                'annotation': int,
            },
            'a:int',
            id='named_annotation',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'public_name': 'a',
                'interface_name': 'b',
            },
            'a->b',
            id='named_mapping',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'public_name': 'a',
                'interface_name': 'b',
                'default': None,
                'annotation': int,
            },
            'a->b:int=None',
            id='named_mapping_anotation_default',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.VAR_POSITIONAL,
                'public_name': 'a',
                'interface_name': 'a',
            },
            '*a',
            id='var_positional',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.VAR_KEYWORD,
                'public_name': 'a',
                'interface_name': 'a',
            },
            '**a',
            id='var_keyword',
        ),
    ])
    def test__str__and__repr__(self, kwargs, expected):
        pmap = ParameterMap(**kwargs)
        assert str(pmap) == expected
        assert repr(pmap) == f'<ParameterMap "{expected}">'

    @pytest.mark.parametrize(('replaces'), [
        pytest.param({'kind': inspect.Parameter.KEYWORD_ONLY}, id='kind'),
        pytest.param({'default': 1}, id='default'),
        pytest.param({'annotation': int}, id='annotation'),
        pytest.param({'public_name': 'b'}, id='public_name'),
        pytest.param({'interface_name': 'b'}, id='interface_name'),
        pytest.param({'converter': dummy_converter}, id='converter'),
        pytest.param({'validator': dummy_validator}, id='validator'),
    ])
    def test_replace(self, replaces):
        pmap = ParameterMap(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name=None,
            interface_name=None,
        )
        pmap2 = pmap.replace(**replaces) # pylint: disable=E1101, no-member
        for k, v in dict(pmap._asdict(), **replaces).items():
            assert getattr(pmap2, k) == v

    def test_public_parameter(self):
        kwargs = dict(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name='a',
            interface_name='b',
            default=None,
            annotation=int,
        )
        pub = ParameterMap(**kwargs).public_parameter
        assert pub.kind == kwargs['kind']
        assert pub.name == kwargs['public_name']
        assert pub.default == kwargs['default']
        assert pub.annotation == kwargs['annotation']

    def test_public_parameter_wo_names_raises(self):
        pmap = ParameterMap(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            pmap.public_parameter
        assert excinfo.value.args[0] == \
            'Cannot generate parameter without public_name'

    def test_interface_parameter(self):
        kwargs = dict(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name='a',
            interface_name='b',
            default=None,
            annotation=int,
        )
        priv = ParameterMap(**kwargs).interface_parameter
        assert priv.kind == kwargs['kind']
        assert priv.name == kwargs['interface_name']
        assert priv.default == kwargs['default']
        assert priv.annotation == kwargs['annotation']

    def test_interface_parameter_wo_names_raises(self):
        pmap = ParameterMap(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            pmap.interface_parameter
        assert excinfo.value.args[0] == \
            'Cannot generate parameter without interface_name'

    def test_defaults(self):
        pmap = ParameterMap(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            public_name='dummy',
            interface_name='dummy',
        )
        assert pmap.kind == inspect.Parameter.POSITIONAL_ONLY
        for k, v in PMAP_DEFAULTS.items():
            assert getattr(pmap, k) == v

    def test_from_parameter(self):
        kwargs = dict(
            name='a',
            kind=inspect.Parameter.POSITIONAL_ONLY,
            annotation=int,
            default=3,
        )
        param = inspect.Parameter(**kwargs)
        pmap = ParameterMap.from_parameter(param)
        for k, v in dict(
                PMAP_DEFAULTS,
                kind=kwargs['kind'],
                public_name=kwargs['name'],
                interface_name=kwargs['name'],
                annotation=kwargs['annotation'],
                default=kwargs['default'],
            ).items():
            assert getattr(pmap, k) == v

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'public_name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'public_name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'public_name': 'a'},
            {'public_name': 'a', 'interface_name': 'a'},
            id='public_name',
        ),
        pytest.param(
            {'public_name': 'a', 'interface_name': 'b'},
            {'public_name': 'a', 'interface_name': 'b'},
            id='public_and_interface_name',
        ),
    ])
    def test_create_positional_only(self, extra_in, extra_out):
        kwargs = dict(
            default=None,
            annotation=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        pmap = ParameterMap.create_positional_only(**kwargs, **extra_in)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == {**PMAP_POS_DEFAULTS, **kwargs, **extra_out}

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'public_name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'public_name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'public_name': 'a'},
            {'public_name': 'a', 'interface_name': 'a'},
            id='public_name',
        ),
        pytest.param(
            {'public_name': 'a', 'interface_name': 'b'},
            {'public_name': 'a', 'interface_name': 'b'},
            id='public_and_interface_name',
        ),
    ])
    def test_create_positional_or_keyword(self, extra_in, extra_out):
        kwargs = dict(
            default=None,
            annotation=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        pmap = ParameterMap.create_positional_or_keyword(**kwargs, **extra_in)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == {**PMAP_POK_DEFAULTS, **kwargs, **extra_out}

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'public_name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'public_name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'public_name': 'a'},
            {'public_name': 'a', 'interface_name': 'a'},
            id='public_name',
        ),
        pytest.param(
            {'public_name': 'a', 'interface_name': 'b'},
            {'public_name': 'a', 'interface_name': 'b'},
            id='public_and_interface_name',
        ),
    ])
    def test_create_contextual(self, extra_in, extra_out):
        kwargs = dict(annotation=int)
        pmap = ParameterMap.create_contextual(**kwargs, **extra_in)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == {**PMAP_CTX_DEFAULTS, **kwargs, **extra_out}

    def test_create_var_positional(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        pmap = ParameterMap.create_var_positional(**kwargs)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == dict(
            PMAP_VPO_DEFAULTS,
            public_name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test_create_keyword_only(self):
        kwargs = dict(
            interface_name='a',
            public_name='b',
            default=None,
            annotation=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        pmap = ParameterMap.create_keyword_only(**kwargs)
        assert isinstance(pmap, ParameterMap)
        for k, v in dict(PMAP_KWO_DEFAULTS, **kwargs).items():
            assert getattr(pmap, k) == v

    def test_create_var_keyword(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        pmap = ParameterMap.create_var_keyword(**kwargs)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == dict(
            PMAP_VKW_DEFAULTS,
            public_name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )


class TestVarPositional:
    @staticmethod
    def assert_iterable_and_get_pmap(varp):
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
        pmap = self.assert_iterable_and_get_pmap(varp)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == dict(
            PMAP_VPO_DEFAULTS,
            public_name=kwargs['name'],
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
        pmap = self.assert_iterable_and_get_pmap(varp)
        assert isinstance(pmap, ParameterMap)
        assert pmap._asdict() == dict(
            PMAP_VPO_DEFAULTS,
            public_name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

class TestVarKeyword:
    @staticmethod
    def assert_mapping_and_get_pmap(vark):
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
        name, pmap = self.assert_mapping_and_get_pmap(vark)
        assert isinstance(pmap, ParameterMap)
        assert name == kwargs['name']
        assert pmap._asdict() == dict(
            PMAP_VKW_DEFAULTS,
            public_name=kwargs['name'],
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
        name, pmap = self.assert_mapping_and_get_pmap(vark)
        assert isinstance(pmap, ParameterMap)
        assert name == kwargs['name']
        assert pmap._asdict() == dict(
            PMAP_VKW_DEFAULTS,
            public_name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test_mapping(self):
        vark = VarKeyword()
        assert vark.name in vark
        assert f'{vark.name}_' not in vark
        assert len(vark) == 1
        assert list(vark) == [vark.name]


class TestConvenience:
    def test_constructors(self):
        # pylint: disable=E1101, no-member
        for conv, method in [
                ('pos', ParameterMap.create_positional_only),
                ('arg', ParameterMap.create_positional_or_keyword),
                ('ctx', ParameterMap.create_contextual),
                ('kwarg', ParameterMap.create_keyword_only),
            ]:
            assert getattr(forge._parameter, conv) == method

    def test_self_(self):
        assert isinstance(self_, ParameterMap)
        assert self_._asdict() == dict(
            **PMAP_CTX_DEFAULTS,
            public_name='self',
            interface_name='self',
        )

    def test_cls_(self):
        assert isinstance(cls_, ParameterMap)
        assert cls_._asdict() == dict(
            **PMAP_CTX_DEFAULTS,
            public_name='cls',
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