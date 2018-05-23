==============
Advanced Usage
==============

Forge enables some new, interesting software development patterns.
Some of those patterns are documented below.


.. _advanced-usage_supplied-arguments:

Supplied arguments
==================

The ``supplied arguments`` pattern is useful when you want to eliminate parameters from a signature.
With this pattern, the caller has no ability to override ``default`` values, making it useful for scripts and generated code.


.. testcode::

    import logging
    import inspect
    from uuid import uuid4

    TOKEN = 'token_{}'.format(uuid4().hex)

    def get_nonce():
        return uuid4().hex

    @forge.sign(
        forge.pos('token', default=TOKEN, bound=True),
        forge.pos('nonce', factory=get_nonce, bound=True),
        forge.arg('endpoint'),
    )
    def execute_api_request(token, nonce, endpoint):
        logging.info(
            'calling %s with token: %s and nonce %s',
            endpoint, token, nonce,
        )

    # notice that `execute_api_request` now has only one parameter, `endpoint`
    assert forge.stringify_callable(execute_api_request) == \
        'execute_api_request(endpoint)'

    # the argument value for `token` is a bound constant, and
    # the argument value for `none` is a bound factory
    execute_api_request('http://dummy.api/1')
    # INFO:root:calling http://dummy.api/1 with token: token_4eb9da44e3f244959572535b8d47d34a and nonce c11f018894154a248dd336de1da98e71


.. _advanced-usgae_var-keyword-precision:

Var-keyword precision
=====================

The ``var-keyword precision`` pattern is useful when you want to explicitly define which :term:`keyword-only` parameters a callable takes.
This is a useful alternative to provided a generic :term:`var-keyword` and *white-listing* or *black-listing* parameters within the callable's code.

.. testcode::

    import inspect
    import forge
    import requests

    defaults = {
        k: forge.kwarg(default=None) for k in (
            'method', 'url', 'params', 'data', 'json', 'headers', 'cookies',
            'files', 'auth', 'timeout', 'allow_redirects', 'proxies', 'verify',
            'stream', 'cert',
        )
    }

    request = forge.sign(
        forge.arg('method'),
        forge.arg('url'),
        **{k: v for k, v in defaults.items() if k not in ('method', 'url')},
    )(requests.request)

    head = forge.sign(
        forge.arg('url'),
        **{k: v for k, v in defaults.items() if k not in ('url')},
    )(requests.request)

    get = forge.sign(
        forge.arg('url'),
        forge.arg('params', default=None),
        **{k: v for k, v in defaults.items() if k not in ('url', 'params')},
    )(requests.get)

    post = forge.sign(
        forge.arg('url'),
        forge.arg('data', default=None),
        forge.arg('json', default=None),
        **{k: v for k, v in defaults.items() if k not in ('url', 'data', 'json')},
    )

    # `requests.request` looks like this (notice the var-keyword **kwargs)
    assert forge.stringify_callable(requests.request) == \
        'request(method, url, **kwargs)'

    # our wrapped `request` looks like this
    assert forge.stringify_callable(request) == (
        'request('
            'method, url, *, params=None, data=None, json=None, headers=None, '
            'cookies=None, files=None, auth=None, timeout=None, '
            'allow_redirects=None, proxies=None, verify=None, stream=None, '
            'cert=None'
        ')'
    )


.. _advanced-usage_transmutating-parameters:

Transmutating parameters
========================

The ``transmutating-parameters`` pattern is useful when you want to convert (or manifest) an argument value to a different argument value.
This pattern is especially helpful you are passing object-ids, as for example with an ORM.

.. testcode::

    import forge

    class User:
        __repo__ = {}

        @classmethod
        def get(cls, user_id):
            return cls.__repo__.get(user_id)

        def __init__(self, id, name, email_address):
            self.id = id
            self.name = name
            self.email_address = email_address

    user_arg = forge.arg(
        'user_id',
        'user',
        converter=lambda ctx, name, value: User.get(value),
    )

    def create_user(name, email_address):
        user = User(
            id=len(User.__repo__),
            name=name,
            email_address=email_address,
        )
        user.__repo__[user.id] = user
        return user.id

    @forge.sign(user_arg, forge.arg('name'))
    def update_name(user, name):
        user.name = name


    # Notice that `user_id` is converted into a `user` object
    assert forge.stringify_callable(update_name) == \
        'update_name(user_id, name)'

    user_id = create_user('John London', 'john@email.com')
    update_name(user_id, 'Jack London')

    assert User.get(user_id).name == 'Jack London'


Void arguments
==============

The ``void-arguments`` pattern allows quick-collection and filtering of input values for processing.
This is useful when multiple parameters can optionally be provided, and `None` is a valid argument value.
This code makes use of :class:`forge.void`.

.. testcode::

    import datetime
    import forge

    class Book:
        __repo__ = {}

        def __init__(self, id, title, author, publication_date):
            self.id = id
            self.title = title
            self.author = author
            self.publication_date = publication_date

        @classmethod
        def get(cls, book_id):
            return cls.__repo__.get(book_id)

        @classmethod
        def create(cls, title, author, publication_date):
            ins = cls(
                id=len(cls.__repo__),
                title=title,
                author=author,
                publication_date=publication_date,
            )
            cls.__repo__[ins.id] = ins
            return ins.id

        @classmethod
        @forge.sign(
            forge.cls,
            forge.arg('book_id', 'book', converter=lambda ctx, name, value: ctx.get(value)),
            forge.kwarg('title', default=forge.void),
            forge.kwarg('author', default=forge.void),
            forge.kwarg('publication_date', default=forge.void),
        )
        def update(cls, book, **kwargs):
            for k, v in kwargs.items():
                if v is not forge.void:
                    setattr(book, k, v)

    assert forge.stringify_callable(Book.update) == \
        'update(book_id, *, title=<void>, author=<void>, publication_date=<void>)'

    book_id = Book.create(
        'Call of the Wild',
        'John London',
        datetime.date(1903, 8, 1),
    )
    Book.update(book_id, author='Jack London')
    assert Book.get(book_id).author == 'Jack London'


.. _advanced-usage_chameleon-begin:

Chameleon function
==================

The ``chameleon function`` pattern demonstrates the powerful functionality of ``forge``.
With this pattern, you gain the ability to dynamically revise a function's signature on demand.
This could be useful for auto-discovered dependency injection.

.. testcode::

    import forge

    @forge.sign(
        *forge.args('remove'),
        **forge.kwargs,
    )
    def chameleon(*remove, **kwargs):
        forge.resign(
            *forge.args('remove'),
            **{
                k: forge.kwarg(default=v) for k, v in kwargs.items()
                if k not in remove
            },
            **forge.kwargs,
        )(chameleon)
        return kwargs

    # Initial use
    assert forge.stringify_callable(chameleon) == 'chameleon(*remove, **kwargs)'

    # Empty call preserves signature
    assert chameleon() == {}
    assert forge.stringify_callable(chameleon) == 'chameleon(*remove, **kwargs)'

    # Var-keyword arguments add keyword-only parameters
    assert chameleon(a=1) == dict(a=1)
    assert forge.stringify_callable(chameleon) == 'chameleon(*remove, a=1, **kwargs)'

    # Empty call preserves signature
    assert chameleon() == dict(a=1)

    # Var-positional arguments remove keyword-only parameters
    assert chameleon('a') == dict(a=1)
    assert forge.stringify_callable(chameleon) == 'chameleon(*remove, **kwargs)'