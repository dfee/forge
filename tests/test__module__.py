import re

import forge

# Keep the namespace clean

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
        'arg',
        'args',
        'cls',
        'ctx',
        'kwarg',
        'kwargs',
        'pos',
        'self',
        # Signature
        'FSignature',
        'Mapper',
        'resign',
        'returns',
        'sign',
        # Utils
        'get_run_validators',
        'set_run_validators',
        'void',
    ])