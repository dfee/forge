import re

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
        'POSITIONAL_ONLY',
        'POSITIONAL_OR_KEYWORD',
        'KEYWORD_ONLY',
        'VAR_POSITIONAL',
        'VAR_KEYWORD',
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
        'void',
        # Utils
        'getparam',
        'hasparam',
        'get_return_type',
        'set_return_type',
    ])


def test_ctx():
    assert forge.ctx == forge.FParameter.create_contextual
    assert isinstance(forge.self, forge.FParameter)
    assert forge.self.contextual
    assert isinstance(forge.cls, forge.FParameter)
    assert forge.cls.contextual

def test_nicknames():
    FP = forge.FParameter
    assert forge.pos == FP.create_positional_only
    assert forge.pok == forge.arg == FP.create_positional_or_keyword
    assert forge.ctx == FP.create_contextual
    assert forge.vpo == FP.create_var_positional
    assert forge.kwo == forge.kwarg == FP.create_keyword_only
    assert forge.vkw == FP.create_var_keyword

def test_instances():
    assert isinstance(forge.args, forge.VarPositional)
    assert isinstance(forge.kwargs, forge.VarKeyword)