=============
API Reference
=============

.. currentmodule:: forge

``forge`` works by decorating a callable using :func:`forge.sign` with parameters of :func:`forge.arg`, :func:`forge.kwarg`, :class:`forge.kwargs`, and .

.. note::

   When this documentation speaks about "``forge`` parameters" it means those parameters that are defined using :func:`forge.arg` and friends in the :func:`forge.sign` decorator.

What follows is the API explanation, if you'd like a more hands-on introduction, have a look at :doc:`basic`.


.. _api_parameter:

Parameter
=========

.. _api_parameter-classes:


Classes
-------
.. autoclass:: forge.FParameter

    .. attribute:: POSITIONAL_ONLY

        For more information about this :term:`parameter kind` constant, refer to :term:`positional-only`.

    .. attribute:: POSITIONAL_OR_KEYWORD

        For more information about this :term:`parameter kind` constant, refer to :term:`positional-or-keyword`.

    .. attribute:: VAR_POSTIIONAL

        For more information about this :term:`parameter kind` constant, refer to :term:`var-positional`.

    .. attribute:: KEYWORD_ONLY

        For more information about this :term:`parameter kind` constant, refer to :term:`keyword-only`.

    .. attribute:: VAR_KEYWORD

        For more information about this :term:`parameter kind` constant, refer to :term:`var-keyword`.


.. _api_parameter-constructors:

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

.. autofunction:: forge.args

.. autofunction:: forge.kwargs


.. _api_parameter-helpers:

Helpers
-------
.. data:: forge.self

    a convenience for ``forge.ctx('self')``.

.. data:: forge.cls

    a convenience for ``forge.ctx('cls')``.


.. _api_signature:

Signature
=========


.. _api_signature-classes:

Classes
-------
.. autoclass:: forge.FSignature

.. autoclass:: forge.Mapper


.. _api_signature-functions:

Functions
---------
.. autofunction:: forge.resign

.. autofunction:: forge.returns

.. autofunction:: forge.sign


.. _api_config:

Config
======

.. autofunction:: forge.get_run_validators

.. autofunction:: forge.set_run_validators


.. _api_marker:

Marker
======

.. autoclass:: forge.void


.. _api_utils:

Utils
=====

.. autofunction:: forge.getparam

.. autofunction:: forge.hasparam

.. autofunction:: forge.get_return_type

.. autofunction:: forge.set_return_type

.. autofunction:: forge.stringify_callable