from ._config import (
    get_run_validators,
    set_run_validators,
)
from ._marker import (
    empty,
    void,
)
from ._parameter import (
    Factory,
    FParameter,
    VarKeyword,
    VarPositional,
)
from ._signature import (
    FSignature,
    Mapper,
    resign,
    returns,
    sign,
)
from ._utils import (
    getparam,
    hasparam,
    get_return_type,
    set_return_type,
    stringify_callable,
)

# pylint: disable=C0103, invalid-name
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