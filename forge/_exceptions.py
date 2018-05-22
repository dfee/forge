class ImmutableInstanceError(Exception):
    """
    An error that is raised when trying to set an attribute on a
    :class:`~forge._immutable.Immutable` instance.
    """
    pass


class NoParameterError(Exception):
    """
    An error that is raised when a :class:`forge.FParameter` or
    :class:`inspect.Parameter` is not found.
    """
    pass
