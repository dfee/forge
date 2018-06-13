=============
API Reference
=============

.. currentmodule:: forge

.. _api_config:

Config
======

.. autofunction:: forge.get_run_validators

.. autofunction:: forge.set_run_validators


.. _api_exceptions:

Exceptions
==========

.. autoclass:: forge.ForgeError

.. autoclass:: forge.ImmutableInstanceError


.. _api_marker:

Marker
======

.. autoclass:: forge.empty
   :members:

.. autoclass:: forge.void
   :members:


.. _api_revisions:

Revisions
=========

.. autoclass:: forge.Mapper
   :members:

.. autoclass:: forge.Revision
   :members:
   :special-members: __call__


.. _api_revisions_group:

Group revisions
---------------

.. autoclass:: forge.compose
   :members:

.. autoclass:: forge.copy
   :members:

.. autoclass:: forge.manage
   :members:

.. autoclass:: forge.returns
   :members:
   :special-members: __call__

.. autoclass:: forge.synthesize
   :members:

.. data:: forge.sign

    a convenience "short-name" for :class:`~forge.synthesize`

.. autoclass:: forge.sort
   :members:


.. _api_revisions_unit:

Unit revisions
--------------
.. autoclass:: forge.delete
   :members:

.. autoclass:: forge.insert
   :members:

.. autoclass:: forge.modify
   :members:

.. autoclass:: forge.replace
   :members:

.. autoclass:: forge.translocate
   :members:

.. data:: forge.move

    a convenience "short-name" for :class:`~forge.translocate`


.. _api_signature:

Signature
=========

.. _api_signature-classes:

Classes
-------
.. autoclass:: forge.FSignature
   :members:

.. autoclass:: forge.FParameter
   :members:

.. autoclass:: forge.Factory
   :members:


.. _api_signature-constructors:

Constructors
------------
.. autofunction:: forge.pos

.. autofunction:: forge.pok

.. function:: forge.arg

    a convenience for :func:`forge.pok`

.. autofunction:: forge.ctx

.. autofunction:: forge.vpo

.. autofunction:: forge.kwo

.. function:: forge.kwarg

    a convenience for :func:`forge.kwo`

.. autofunction:: forge.vkw


.. _api_parameter-helpers:

Helpers
-------

.. autofunction:: findparam

.. autofunction:: forge.args

    a "ready-to-go" instance of :class:`~forge.VarPositional`, with the name ``args``.
    Use as ``*args``, or supply :meth:`~forge.VarPositional.replace` arguments.
    For example, to change the name to ``items``: ``*args(name='items')``.

.. autodata:: forge.kwargs

    a "ready-to-go" instance of :class:`~forge.VarKeyword`, with the name ``kwargs``.
    Use as ``**kwargs``, or supply :meth:`~forge.VarKeyword.replace` arguments.
    For example, to change the name to ``extras``: ``**kwargs(name='extras')``.

.. autodata:: forge.self

    a "ready-to-go" instance of :class:`~forge.FParameter` as the ``self`` context parameter.

.. autodata:: forge.cls

    a "ready-to-go" instance of :class:`~forge.FParameter` as the ``cls`` context parameter.


.. _api_utils:

Utils
=====

.. autofunction:: forge.callwith

.. autofunction:: forge.repr_callable
