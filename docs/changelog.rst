===============
Version history
===============

Versions follow `CalVer`_ with a strict backwards compatibility policy. The third digit is only for regressions.

.. _CalVer: http://calver.org/


.. _changelog_2018-5-1:

**2018.5.1** (2018-05-31)

- Added :class:`~forge.empty` as class variable to :class:`~forge.FParameter`
- Added :func:`~forge.reflect` which makes a wrapper that reflects a callable's signature
- Added :func:`~forge.sort_arguments` and :func:`~forge.callwith` which are convenience functions for re-packaging arguments for reflected functions.
- Added :func:`~forge.fsignature` which is a convenience for :func:`~forge.FSignature.from_callable` to reflect the functionality of :func:`inspect.signature` (itself a convenience for :func:`inspect.Signature.from_callable`)
- Added slice notation support for :class:`~forge.FSignature` objects.
- Exposed :class:`~forge.CallArguments`
- Removed ``get_return_type`` and ``set_return_type`` as :attr:`~forge.FSignature.return_annotation` is now a first-class attribute
- Renamed stringify_callable -> repr_callable

.. _changelog_2018-5-0:

**2018.5.0** (2018-05-15)

- Initial release