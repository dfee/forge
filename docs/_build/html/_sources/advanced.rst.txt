==============
Advanced Usage
==============

Forge enables some new, interesting software development patterns. Some of those patterns are documented below.

Void arguments
==============

.. code-block:: python

    import forge

    zvoid = object()

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
            forge.kwarg('title', default=zvoid),
            forge.kwarg('author', default=zvoid),
            forge.kwarg('publication_date', default=zvoid),
        )
        def update(cls, book, **kwargs):
            for k, v in kwargs.items():
                if v is not zvoid:
                    setattr(book, k, v)

    book_id = Book.create(
        'Call of the Wild',
        'John London',
        datetime.date(1903, 8, 1),
    )
    Book.update(book_id, author='Jack London')
    assert Book.get(book_id).author == 'Jack London'


Supplied arguments
==================

.. code-block:: python

    import logging
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
        logging.warning(
            'calling %s with token: %s and nonce %s',
            endpoint, token, nonce,
        )

    >>> help(execute_api_request)
    execute_api_request(endpoint)
    >>> execute('http://dummy.api/1')
    WARNING:root:calling http://dummy.api/1 with token: token_4eb9da44e3f244959572535b8d47d34a and nonce c11f018894154a248dd336de1da98e71


Var-keyword precision
=====================

Signature looks like::

    request(method, url, **kwargs)

.. code-block:: python

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

    >>> help(requests.request)
    request(method, url, **kwargs)
    >>> help(request)
    request(method, url, *, params=None, data=None, json=None, headers=None, cookies=None, files=None, auth=None, timeout=None, allow_redirects=None, proxies=None, verify=None, stream=None, cert=None)


.. _advanced-usage_transforming-parameters:

Transforming parameters
=======================

- change interface
- reduce boilerplate
- arg as a variable

.. code-block:: python

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

    @forge.sign(user_arg, forge.arg('name'))
    def update_email_address(user, name):
        user.name = name

    user_id = create_user('John London', 'john@email.com')
    update_name(user_id, 'Jack London')

    assert User.get(user_id).name == 'Jack London'


.. _advanced-usage_chameleon-begin:

Chameleon function
==================

.. code-block:: python

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

    def test_chameleon():
        assert chameleon() == {}
        assert chameleon(a=1) == dict(a=1)
        assert chameleon() == dict(a=1)
        assert chameleon('a') == dict(a=1)
        assert chameleon() == {}