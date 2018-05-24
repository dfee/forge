.. image:: https://raw.githubusercontent.com/dfee/forge/master/docs/_static/forge-horizontal.png
   :alt: forge logo

================================================
``forge`` (python) signatures for fun and profit
================================================

.. image:: https://travis-ci.org/dfee/forge.png?branch=master
    :target: https://travis-ci.org/dfee/forge
    :alt: master Travis CI Status
.. image:: https://coveralls.io/repos/github/dfee/forge/badge.svg?branch=master
    :target: https://coveralls.io/github/dfee/forge?branch=master
    :alt: master Coveralls Status


.. overview-begin

``forge`` is an *elegant* Python package that allows for **meta-programming of function signatures**. Now, you can finally **add**, **remove**, or **enhance parameters** at your will.

Use it to write **legible** signatures for consumption by team members, the public, or other code.

.. overview-end

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

    assert forge.stringify_callable(myfunc) == \
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

    assert forge.stringify_callable(myfunc) == "myfunc(*, color='blue')"
    assert myfunc() == 'blue'


You can also supply type annotations for usage with linters like mypy:

.. code-block:: python

    import forge

    @forge.sign(forge.arg('number', type=int))
    @forge.returns(str)
    def to_str(number):
        return str(number)

    assert forge.stringify_callable(to_str) == 'to_str(number:int) -> str'
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
            raise TypeError(f"{name} must be >= 5")

    @forge.sign(forge.arg('count', validator=validate_gt5))
    def send_presents(count):
        return [Present() for i in range(count)]

    assert forge.stringify_callable(send_presents) == 'send_presents(count)'

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
            raise TypeError(f'expected one of {ctx.colors}, received {value}')

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
        return f'{ctx.title} {value}'

    class RoleAnnouncer:
        def __init__(self, title):
            self.title = title

        @forge.sign(forge.self, forge.arg('name', converter=titleize))
        def announce(self, name):
            return f'Now announcing {name}!'

    doctor_ra = RoleAnnouncer('Doctor')
    captain_ra = RoleAnnouncer('Captain')

    assert doctor_ra.announce('Strangelove') == \
        "Now announcing Doctor Strangelove!"
    assert captain_ra.announce('Lionel Mandrake') == \
        "Now announcing Captain Lionel Mandrake!"

.. quickstart-end


.. _readme-requirements:

Requirements
============

- CPython >= 3.6.0
- PyPy >= 3.5.3


.. _readme-author:

Author
=======

This package was conceived of and written by `Devin Fee <https://github.com/dfee>`_. Other contributors are listed under https://github.com/dfee/forge/graphs/contributors.


.. _readme-license:

License
=======

``forge`` is offered under the MIT license.


.. _readme-source-code:

Source code
===========

The latest developer version is available in a github repository:
https://github.com/dfee/forge