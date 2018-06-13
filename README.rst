.. image:: https://raw.githubusercontent.com/dfee/forge/master/docs/_static/forge-horizontal.png
   :alt: forge logo

===============================
``forge`` *(python signatures)*
===============================


.. image:: https://img.shields.io/badge/pypi-v2018.6.0-blue.svg
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

.. overview-start

``forge`` is an elegant Python package for revising function signatures at runtime.
This libraries aim is to help you write better, more literate code with less boilerplate.

.. overview-end


.. installation-start

Installation
============

``forge`` is a Python-only package `hosted on PyPI <https://pypi.org/project/python-forge>`_ for **Python 3.5+**.

The recommended installation method is `pip-installing <https://pip.pypa.io/en/stable/>`_ into a `virtualenv <https://docs.python.org/3/library/venv.html>`_:

.. code-block:: console

    $ pip install python-forge

.. installation-end


.. example-start

Example
=======

Consider a library like `requests <https://github.com/requests/requests>`_ that provides a useful API for performing HTTP requests.
Every HTTP method has it's own function which is a thin wrapper around :func:`requests.Session.request`.
The code is a little more than 150 lines, but using ``forge`` we can narrow that down to about 1/10th the size, while **increasing** the literacy of the code.

.. testcode::

    import forge
    import requests

    request = forge.copy(requests.Session.request, exclude='self')(requests.request)

    def with_method(method):
        revised = forge.modify(
            'method', default=method, bound=True,
            kind=forge.FParameter.POSITIONAL_ONLY,
        )(request)
        revised.__name__ = method.lower()
        return revised

    post = with_method('POST')
    get = with_method('GET')
    put = with_method('PUT')
    delete = with_method('DELETE')
    options = with_method('OPTIONS')
    head = with_method('HEAD')
    patch = with_method('PATCH')

So what happened?
The first thing we did was create an alternate ``request`` function to replace ``requests.request`` that provides the exact same functionality but makes its parameters explicit:

.. testcode::

    # `requests.get` looks like this:
    assert forge.repr_callable(requests.get) == 'get(url, params=None, **kwargs)'

    # our `request` looks like this:
    assert forge.repr_callable(get) == (
        'get(url, params=None, data=None, headers=None, cookies=None, '
            'files=None, auth=None, timeout=None, allow_redirects=True, '
            'proxies=None, hooks=None, stream=None, verify=None, cert=None, '
            'json=None)'
    )


Next, we built a factory function ``with_method`` that creates new functions which make HTTP requests with the proper HTTP verb.
Because the ``method`` parameter is bound, it won't show up it is removed from the resulting functions signature.
Of course, the signature of these generated functions remains explicit, let's try it out:

.. testcode::

    response = get('http://google.com')
    assert 'Feeling Lucky' in response.text

You can review the alternate code (the actual implementation) by visiting the code for `requests.api <https://github.com/requests/requests/blob/991e8b76b7a9d21f698b24fa0058d3d5968721bc/requests/api.py>`_.

.. example-end


.. project-information-start

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


.. _requests_api_get: https://github.com/requests/requests/blob/991e8b76b7a9d21f698b24fa0058d3d5968721bc/requests/api.py#L61
