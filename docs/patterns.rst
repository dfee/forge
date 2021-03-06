==================
Patterns and usage
==================

Forge enables new software development patterns for Python.
Selected patterns are documented below.


Model management
================

This pattern helps you work with objects and their corresponding management methods.
Commonly, models are generated by a ``metaclass`` and convert declartive-style user-code into enhanced Python classes.

In this example we'll write a service class that manages an ``Article`` object.
For simplicity, we'll use :class:`types.SimpleNamespace` rather than defining our own metaclass and field instances.

.. testcode::

    from types import SimpleNamespace
    from datetime import datetime
    import forge

    class Article(SimpleNamespace):
        pass

    def create_article(title=None, text=None):
        return Article(title=title, text=text, created_at=datetime.now())

    @forge.copy(create_article)
    def create_draft(**kwargs):
        kwargs['title'] = kwargs['title'] or '(draft)'
        return create_article(**kwargs)

    assert forge.repr_callable(create_draft) == \
        "create_draft(title=None, text=None)"

    draft = create_draft()
    assert draft.title == '(draft)'

As you can see, ``create_draft`` no longer exposes the :term:`var-keyword` parameter ``kwargs``.
Instead, it has the same function signature as ``create_article``.

And, as expected, passing a keyword-argument that's not ``title`` or ``text`` raises a TypeError.

.. testcode::

    try:
        create_draft(author='Abe Lincoln')
    except TypeError as exc:
        assert exc.args[0] == "create_draft() got an unexpected keyword argument 'author'"

As expected, ``create_draft`` now raises an error when undefined keyword arguments are passed.

How about creating another method for *editing* the article?
Let's keep in mind that we might want to erase the ``text`` of the article, so a value of ``None`` is significant.

In this example we're going to use four revisions: :class:`~forge.compose` (to perform a batch of revisions), :class:`~forge.copy` (to copy another function's signature), :class:`~forge.insert` (to add an additional parameter), and :class:`~forge.modify` (to alter one or more parameters).

.. testcode::

    @forge.compose(
        forge.copy(create_article),
        forge.insert(forge.arg('article'), index=0),
        forge.modify(
            lambda param: param.name != 'article',
            multiple=True,
            default=forge.void,
        ),
    )
    def edit_article(article, **kwargs):
        for k, v in kwargs.items():
            if v is not forge.void:
                setattr(article, k, v)

    assert forge.repr_callable(edit_article) == \
        "edit_article(article, title=<void>, text=<void>)"

    edit_article(draft, text='hello world')
    assert draft.title == '(draft)'
    assert draft.text == 'hello world'

As your ``Article`` class gains more attributes (``author``, ``tags``, ``status``, ``published_on``, etc.) the amount of effort to maintenance, update and test these parameters - or a subset of these parameters – becomes costly and taxing.


Var-keyword precision
=====================

This pattern is useful when you want to explicitly define which :term:`keyword-only` parameters a callable takes.
This is a useful alternative to provided a generic :term:`var-keyword` and *white-listing* or *black-listing* parameters within the callable's code.

.. include:: ../README.rst
    :start-after: example-start
    :end-before: example-end


Void arguments
==============

The ``void arguments`` pattern allows quick-collection and filtering of arguments.
It is useful when `None` can not or should not be used as a default argument.
This code makes use of :class:`forge.void`.

Consider the situation where you'd like to make explicit the accepted arguments (i.e. not use the :term:`var-positional` parameter ``**kwargs``), but ``None`` can be used to nullify data (for example with an ORM).


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

    assert forge.repr_callable(Book.update) == \
        'update(book_id, *, title=<void>, author=<void>, publication_date=<void>)'

    book_id = Book.create(
        'Call of the Wild',
        'John London',
        datetime.date(1903, 8, 1),
    )
    Book.update(book_id, author='Jack London')
    assert Book.get(book_id).author == 'Jack London'


Chameleon function
==================

The ``chameleon function`` pattern demonstrates the powerful functionality of ``forge``.
With this pattern, you gain the ability to dynamically revise a function's signature on demand.
This could be useful for auto-discovered dependency injection.

.. testcode::

    import forge

    @forge.compose()
    def chameleon(*remove, **kwargs):
        globals()['chameleon'] = forge.compose(
            forge.copy(chameleon.__wrapped__),
            forge.insert([
                forge.kwo(k, default=v) for k, v in kwargs.items()
                if k not in remove
            ], index=0),
            forge.sort(),
        )(chameleon)
        return kwargs

    # Initial use
    assert forge.repr_callable(chameleon) == 'chameleon(*remove, **kwargs)'

    # Empty call preserves signature
    assert chameleon() == {}
    assert forge.repr_callable(chameleon) == 'chameleon(*remove, **kwargs)'

    # Var-keyword arguments add keyword-only parameters
    assert chameleon(a=1) == dict(a=1)
    assert forge.repr_callable(chameleon) == 'chameleon(*remove, a=1, **kwargs)'

    # Empty call preserves signature
    assert chameleon() == dict(a=1)

    # Var-positional arguments remove keyword-only parameters
    assert chameleon('a') == dict(a=1)
    assert forge.repr_callable(chameleon) == 'chameleon(*remove, **kwargs)'
