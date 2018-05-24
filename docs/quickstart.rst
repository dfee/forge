==========
Quickstart
==========

.. _quickstart_resigning-a-function:

Re-signing a function
=====================

The primary purpose of forge is to alter the public signature of functions:

.. testcode::

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

.. testcode::

    import forge

    @forge.sign(forge.kwarg('color', 'colour', default='blue'))
    def myfunc(colour):
        return colour

    assert forge.stringify_callable(myfunc) == "myfunc(*, color='blue')"
    assert myfunc() == 'blue'


You can also supply type annotations for usage with linters like mypy:

.. testcode::

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

.. testcode::

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

.. testcode::

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

.. testcode::

    import forge

    def uppercase(ctx, name, value):
        return value.upper()

    @forge.sign(forge.arg('message', converter=uppercase))
    def shout(message):
        return message

    assert shout('hello over there') == 'HELLO OVER THERE'


You can optionally provide a context parameter, such as ``self``, ``cls``, or create your own named FParameter with ``forge.ctx('myparam')``, and use that alongside conversion:

.. testcode::

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