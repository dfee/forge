.. image:: https://raw.githubusercontent.com/dfee/forge/master/docs/_static/forge-horizontal.png
   :alt: forge logo

================================================
``forge`` (python) signatures for fun and profit
================================================


.. image:: https://img.shields.io/badge/pypi-v2018.5.0-blue.svg
    :target: https://pypi.org/project/python-forge/
    :alt: pypi project
.. image:: https://img.shields.io/badge/license-MIT-blue.svg
    :target: https://pypi.org/project/python-forge/
    :alt: MIT license
.. image:: https://img.shields.io/badge/python-3.5%2C%203.6%2C%203.7-blue.svg
    :target: https://pypi.org/project/python-forge/
    :alt: Python 3.5+
.. image:: https://travis-ci.org/dfee/forge.png?branch=master
    :target: https://travis-ci.org/dfee/forge
    :alt: master Travis CI Status
.. image:: https://coveralls.io/repos/github/dfee/forge/badge.svg?branch=master
    :target: https://coveralls.io/github/dfee/forge?branch=master
    :alt: master Coveralls Status
.. image:: https://readthedocs.org/projects/python-forge/badge/
    :target: http://python-forge.readthedocs.io/en/latest/
    :alt: Documentation Status

.. overview-begin

``forge`` is an elegant Python package for crafting function signatures.
Its aim is to help you write better, more literate code with less boilerplate.

The power of **dynamic signatures** is finally within grasp – **add**, **remove**, or **enhance parameters** at will!

.. overview-end


.. installation-begin

``forge`` is a Python-only package `hosted on PyPI <https://pypi.org/project/python-forge>`_ for **Python 3.5+**.

The recommended installation method is `pip-installing <https://pip.pypa.io/en/stable/>`_ into a `virtualenv <https://docs.python.org/3/library/venv.html>`_:

.. code-block:: console

    $ pip install python-forge

.. installation-end


.. quickstart-begin

Re-signing a function
=====================

The primary purpose of forge is to alter the public signature of functions:

.. code-block:: python

    import forge

    @forge.sign(
        forge.pos('positional'),
        forge.arg('argument'),
        *forge.args,
        keyword=forge.kwarg(),
        **forge.kwargs,
    )
    def myfunc(*args, **kwargs):
        return (args, kwargs)

    assert forge.repr_callable(myfunc) == \
        'myfunc(positional, /, argument, *args, keyword, **kwargs)'

    args, kwargs = myfunc(1, 2, 3, 4, 5, keyword='abc', extra='xyz')

    assert args == (3, 4, 5)
    assert kwargs == {
        'positional': 1,
        'argument': 2,
        'keyword': 'abc',
        'extra': 'xyz',
        }


You can re-map a parameter to a different ParameterKind (e.g. positional-only to positional-or-keyword *or* keyword-only), and optionally supply a default value:

.. code-block:: python

    import forge

    @forge.sign(forge.kwarg('color', 'colour', default='blue'))
    def myfunc(colour):
        return colour

    assert forge.repr_callable(myfunc) == "myfunc(*, color='blue')"
    assert myfunc() == 'blue'


You can also supply type annotations for usage with linters like mypy:

.. code-block:: python

    import forge

    @forge.sign(forge.arg('number', type=int))
    @forge.returns(str)
    def to_str(number):
        return str(number)

    assert forge.repr_callable(to_str) == 'to_str(number:int) -> str'
    assert to_str(3) == '3'


.. _quickstart_validating-a-parameter:

Validating a parameter
======================

You can validate arguments by either passing a validator or an iterable (such as a list or tuple) of validators to your FParameter constructor.

.. code-block:: python

    import forge

    class Present:
        pass

    def validate_gt5(ctx, name, value):
        if value < 5:
            raise TypeError("{name} must be >= 5".format(name=name))

    @forge.sign(forge.arg('count', validator=validate_gt5))
    def send_presents(count):
        return [Present() for i in range(count)]

    assert forge.repr_callable(send_presents) == 'send_presents(count)'

    try:
        send_presents(3)
    except TypeError as exc:
        assert exc.args[0] == "count must be >= 5"

    sent = send_presents(5)
    assert len(sent) == 5
    for p in sent:
        assert isinstance(p, Present)


You can optionally provide a context parameter, such as ``self``, ``cls``, or create your own named parameter with ``forge.ctx('myparam')``, and use that alongside validation:

.. code-block:: python

    import forge

    def validate_color(ctx, name, value):
        if value not in ctx.colors:
            raise TypeError(
                'expected one of {ctx.colors}, received {value}'.\
                format(ctx=ctx, value=value)
            )

    class ColorSelector:
        def __init__(self, *colors):
            self.colors = colors
            self.selected = None

        @forge.sign(
            forge.self,
            forge.arg('color', validator=validate_color)
        )
        def select_color(self, color):
            self.selected = color

    cs = ColorSelector('red', 'green', 'blue')

    try:
        cs.select_color('orange')
    except TypeError as exc:
        assert exc.args[0] == \
            "expected one of ('red', 'green', 'blue'), received orange"

    cs.select_color('red')
    assert cs.selected == 'red'


.. _quickstart_converting-a-parameter:

Converting a parameter
======================

You can convert an argument by passing a conversion function to your FParameter constructor.

.. code-block:: python

    import forge

    def uppercase(ctx, name, value):
        return value.upper()

    @forge.sign(forge.arg('message', converter=uppercase))
    def shout(message):
        return message

    assert shout('hello over there') == 'HELLO OVER THERE'


You can optionally provide a context parameter, such as ``self``, ``cls``, or create your own named FParameter with ``forge.ctx('myparam')``, and use that alongside conversion:

.. code-block:: python

    import forge

    def titleize(ctx, name, value):
        return '{ctx.title} {value}'.format(ctx=ctx, value=value)

    class RoleAnnouncer:
        def __init__(self, title):
            self.title = title

        @forge.sign(forge.self, forge.arg('name', converter=titleize))
        def announce(self, name):
            return 'Now announcing {name}!'.format(name=name)

    doctor_ra = RoleAnnouncer('Doctor')
    captain_ra = RoleAnnouncer('Captain')

    assert doctor_ra.announce('Strangelove') == \
        "Now announcing Doctor Strangelove!"
    assert captain_ra.announce('Lionel Mandrake') == \
        "Now announcing Captain Lionel Mandrake!"

.. quickstart-end


.. project-information-begin

Project information
===================

``forge`` is released under the `MIT <https://choosealicense.com/licenses/mit/>`_ license,
its documentation lives at `Read the Docs <http://python-forge.rtfd.io/>`_,
the code on `GitHub <https://github.com/dfee/forge>`_,
and the latest release on `PyPI <https://pypi.org/project/python-forge/>`_.
It’s rigorously tested on Python 3.6+ and PyPy 3.5+.

``forge`` is authored by `Devin Fee <https://github.com/dfee>`_.
Other contributors are listed under https://github.com/dfee/forge/graphs/contributors.

.. project-information-end