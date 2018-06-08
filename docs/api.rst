=============
API Reference
=============

.. currentmodule:: forge

``forge`` works by decorating callable using subclasses of :class:`forge.Revision`.
What follows is the API explanation, if you'd like a more hands-on introduction, have a look at :doc:`basic`.


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

.. autoclass:: forge.void


.. _api_revisions:

Revisions
=========

.. autoclass:: forge.Mapper

.. autoclass:: forge.Revision


.. _api_revisions_group:

Group revisions
---------------

.. autoclass:: forge.compose

.. autoclass:: forge.copy

.. autoclass:: forge.manage

.. autoclass:: forge.returns

.. autoclass:: forge.synthesize

.. data:: forge.sign

    a convenience "short-name" for :class:`~forge.synthesize`

.. autoclass:: forge.sort


.. _api_revisions_unit:

Unit revisions
--------------
.. autoclass:: forge.delete

.. autoclass:: forge.insert

.. autoclass:: forge.modify

.. autoclass:: forge.replace

.. autoclass:: forge.translocate

.. data:: forge.move

    a convenience "short-name" for :class:`~forge.translocate`


.. _api_signature:

Signature
=========

.. _api_signature-classes:

Classes
-------
.. autoclass:: forge.FSignature

.. autoclass:: forge.FParameter

.. autoclass:: forge.VarPositional

.. autoclass:: forge.VarKeyword

.. autoclass:: forge.Factory


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

.. data:: forge.args

    a "ready-to-go" instance of :class:`~forge.VarPositional`, with the name ``args``.
    Use as ``*args``, or supply :meth:`~forge.VarPositional.replace` arguments.
    For example, to change the name to ``items``: ``*args(name='items')``.

.. data:: forge.kwargs

    a "ready-to-go" instance of :class:`~forge.VarKeyword`, with the name ``kwargs``.
    Use as ``**kwargs``, or supply :meth:`~forge.VarKeyword.replace` arguments.
    For example, to change the name to ``extras``: ``**kwargs(name='extras')``.

.. data:: forge.self

    a "ready-to-go" instance of :class:`~forge.FParameter` as the ``self`` context parameter.

.. data:: forge.cls

    a "ready-to-go" instance of :class:`~forge.FParameter` as the ``cls`` context parameter.


.. _api_utils:

Utils
=====

.. autofunction:: forge.callwith

.. autofunction:: forge.repr_callable