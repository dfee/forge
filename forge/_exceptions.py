class ForgeError(Exception):
    """
    A common base class for ``forge`` exceptions
    """
    pass


class ImmutableInstanceError(ForgeError):
    """
    An error that is raised when trying to set an attribute on a
    :class:`~forge._immutable.Immutable` instance.
    """
    pass


class RevisionError(ForgeError):
    """
    A generic error raised by :meth:`~forge.BaseRevision.apply`
    An error that is raised when a revision fails
    """
    pass
