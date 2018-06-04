from ._compose import (
    Mapper,
    BaseRevision,
    BatchRevision as batch,
    # Unit
    DeleteRevision as delete,
    IdentityRevision as identity,
    InsertRevision as insert,
    ManageRevision as manage,
    ModifyRevision as modify,
    TranslocateRevision as translocate,
    # Group
    CopyRevision as copy,
    ReplaceRevision as replace,
    returns, # todo make revision
    SynthesizeRevision as synthesize,
)
from ._config import (
    get_run_validators,
    set_run_validators,
)
from ._exceptions import (
    ForgeError,
    ImmutableInstanceError,
    NoParameterError,
    RevisionError,
)
from ._marker import (
    empty,
    void,
)
from ._signature import (
    CallArguments,
    Factory,
    FParameter,
    FSignature,
    VarKeyword,
    VarPositional,
    callwith,
    getparam,
    hasparam,
    stringify_callable,
)

# pylint: disable=C0103, invalid-name

# Compose
move = translocate
sign = synthesize

# Signature
fsignature = FSignature.from_callable

# Parameters
pos = FParameter.create_positional_only
arg = pok = FParameter.create_positional_or_keyword
kwarg = kwo = FParameter.create_keyword_only
ctx = FParameter.create_contextual
vpo = FParameter.create_var_positional
vkw = FParameter.create_var_keyword

args = VarPositional()
kwargs = VarKeyword()
self = ctx('self')
cls = ctx('cls')