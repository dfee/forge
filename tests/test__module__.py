import re

import forge

# Keep the namespace clean

def test_namespace():
    private_ptn = re.compile(r'^\_[a-zA-Z]')
    assert set(filter(private_ptn.match, forge.__dict__.keys())) == set([
        '_exceptions',
        '_marker',
        '_parameter',
        '_signature',
        '_utils',
    ])

    public_ptn = re.compile(r'^[a-zA-Z]')
    assert set(filter(public_ptn.match, forge.__dict__.keys())) == set([
        # Parameters
        'ParameterMap',
        'arg',
        'args',
        'cls',
        'ctx',
        'kwarg',
        'kwargs',
        'pos',
        'self',
        # Signature
        'Forger',
        'SignatureMapper',
        'returns',
        'ry',
        'sign',
        # Utils
        'get_run_validators',
        'set_run_validators',
        'void',
    ])


def test_nicknames():
    for nickname, official in {
            'ry': 'Forger',
            'sign': 'Forger',
        }.items():
        assert getattr(forge, official) is getattr(forge, nickname)