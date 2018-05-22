import re

import pytest

import forge
import forge._parameter

# Keep the namespace clean

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use

def test_namespace():
    private_ptn = re.compile(r'^\_[a-zA-Z]')
    assert set(filter(private_ptn.match, forge.__dict__.keys())) == set([
        '_config',
        '_exceptions',
        '_immutable',
        '_marker',
        '_parameter',
        '_signature',
        '_utils',
    ])

    public_ptn = re.compile(r'^[a-zA-Z]')
    assert set(filter(public_ptn.match, forge.__dict__.keys())) == set([
        # Parameters
        'FParameter',
        'VarKeyword', 'kwargs',
        'VarPositional', 'args',
        'ctx', 'self', 'cls',
        'pos',
        'pok', 'arg',
        'kwo', 'kwarg',
        'vkw',
        'vpo',
        # Signature
        'FSignature',
        'Mapper',
        'resign',
        'returns',
        'sign',
        # Config
        'get_run_validators',
        'set_run_validators',
        # Markers
        'empty',
        'void',
        # Utils
        'getparam',
        'hasparam',
        'get_return_type',
        'set_return_type',
    ])


class TestConvenience:
    def test_constructors(self):
        FP = forge.FParameter
        assert forge.pos == FP.create_positional_only
        assert forge.pok == forge.arg == FP.create_positional_or_keyword
        assert forge.ctx == FP.create_contextual
        assert forge.vpo == FP.create_var_positional
        assert forge.kwo == forge.kwarg == FP.create_keyword_only
        assert forge.vkw == FP.create_var_keyword

    @pytest.mark.parametrize(('name', 'method'), [
        ('pos', forge.FParameter.create_positional_only),
        ('pok', forge.FParameter.create_positional_or_keyword),
        ('arg', forge.FParameter.create_positional_or_keyword),
        ('ctx', forge.FParameter.create_contextual),
        ('vpo', forge.FParameter.create_var_positional),
        ('kwo', forge.FParameter.create_keyword_only),
        ('kwarg', forge.FParameter.create_keyword_only),
        ('vkw', forge.FParameter.create_var_keyword),
    ])
    def test_constructors(self, name, method):
        assert getattr(forge, name) == method

    def test_self(self):
        assert forge.self == forge.FParameter(
            forge.FParameter.POSITIONAL_OR_KEYWORD,
            name='self',
            interface_name='self',
            contextual=True,
        )

    def test_cls(self):
        assert forge.cls == forge.FParameter(
            forge.FParameter.POSITIONAL_OR_KEYWORD,
            name='cls',
            interface_name='cls',
            contextual=True,
        )

    def test_args(self):
        args = forge.args
        assert isinstance(args, forge._parameter.VarPositional)
        assert args.name == 'args'
        assert args.converter is None
        assert args.validator is None

    def test_kwargs(self):
        kwargs = forge.kwargs
        assert isinstance(kwargs, forge._parameter.VarKeyword)
        assert kwargs.name == 'kwargs'
        assert kwargs.converter is None
        assert kwargs.validator is None