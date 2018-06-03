import re

import pytest

import forge
import forge._parameter

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use


def test_namespace():
    """
    Keep the namespace clean
    """
    private_ptn = re.compile(r'^\_[a-zA-Z]')
    assert set(filter(private_ptn.match, forge.__dict__.keys())) == set([
        '_compose',
        '_config',
        '_counter',
        '_exceptions',
        '_immutable',
        '_marker',
        '_parameter',
        '_signature',
        '_utils',
    ])

    public_ptn = re.compile(r'^[a-zA-Z]')
    assert set(filter(public_ptn.match, forge.__dict__.keys())) == set([
        ## Compose
        'BaseRevision',
        # unit
        'delete', 'insert', 'modify', 'translocate', 'move', 'replace',
        # meta
        'batch', # collection
        # group
        'copy',
        'identity',
        'manage',
        'synthesize', 'sign',
        # other
        'returns',

        ## Parameters
        'Factory',
        'FParameter',
        # variadic
        'VarKeyword', 'kwargs',
        'VarPositional', 'args',
        # context
        'ctx', 'self', 'cls',
        # constructors
        'pos', 'pok', 'arg', 'kwo', 'kwarg', 'vkw', 'vpo',

        ## Signature
        'FSignature',
        'Mapper',
        'fsignature',

        ## Config
        'get_run_validators',
        'set_run_validators',

        ## Exceptions
        'ForgeError',
        'ImmutableInstanceError',
        'ForgeError',
        'NoParameterError',
        'RevisionError',

        ## Markers
        'empty',
        'void',

        ## Utils
        'CallArguments',
        'callwith',
        'getparam',
        'hasparam',
        'stringify_callable',
    ])


class TestComposeConvenience:
    @pytest.mark.parametrize(('name', 'obj'), [
        ('copy', forge._compose.CopyRevision),
        ('delete', forge._compose.DeleteRevision),
        ('insert', forge._compose.InsertRevision),
        ('manage', forge._compose.ManageRevision),
        ('modify', forge._compose.ModifyRevision),
        ('move', forge._compose.TranslocateRevision),
        ('translocate', forge._compose.TranslocateRevision),
        ('replace', forge._compose.ReplaceRevision),
    ])
    def test_constructors(self, name, obj):
        """
        Assert constructor nicknames are what we exect them to be.
        """
        assert getattr(forge, name) == obj


class TestSignatureConvenience:
    @pytest.mark.parametrize(('name', 'obj'), [
        ('fsignature', forge.FSignature.from_callable),
    ])
    def test_constructors(self, name, obj):
        """
        Assert constructor nicknames are what we exect them to be.
        """
        assert getattr(forge, name) == obj



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
        assert isinstance(args, forge._parameter.VarPositional)
        assert args.name == 'args'
        assert args.converter is None
        assert args.validator is None

    def test_kwargs(self):
        """
        Assert ``forge.kwargs`` is what we expect it to be.
        """
        kwargs = forge.kwargs
        assert isinstance(kwargs, forge._parameter.VarKeyword)
        assert kwargs.name == 'kwargs'
        assert kwargs.converter is None
        assert kwargs.validator is None