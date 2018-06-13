===============
Version history
===============

Versions follow `CalVer <http://calver.org>`_ with a strict backwards compatibility policy.
The first digit is the year, the second digit is the month, the third digit is for regressions.

.. _changelog_2018-6-0:

2018.6.0
========

*Released on 2018-06-13*

- This update is a complete re-design of the ``forge`` library.
- ``forge.sign`` is now a subclass of ``forge.Revision``, and ``forge.resign`` is integrated into ``forge.Revision.__call__``.
- the following group revisions have been introduced:
    - ``forge.compose``,
    - ``forge.copy``,
    - ``forge.manage``,
    - ``forge.returns``
    - ``forge.synthesize`` (a.k.a. ``forge.sign``)
    - ``forge.sort``
- the following unit revisions have been introduced:
    - ``forge.delete``,
    - ``forge.insert``,
    - ``forge.modiy``,
    - ``forge.replace``
    - ``forge.translocate`` (a.k.a. ``forge.move``)
- Marker classes are no longer singletons (instances can be produced)
- ``stringify_callable`` is now the more serious ``repr_callable``
- introducing ``callwith``, a function that receives a callable and arguments, orders the arguments and returns with a call to the supplied callable
- ``var-positional`` and ``var-keyword`` parameters now accept a ``type`` argument


.. _changelog_2018-5-0:

2018.5.0
========

*Released on 2018-05-15*

- Initial release
