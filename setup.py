import platform
import sys
from setuptools import setup


def permit_setup():
    """
    Determines whether setup is permitted:
    - CPython >= 3.6+
    - PyPy >= 3.5+
    :return: True if setup is allowed
    """
    implementation = platform.python_implementation()
    v = sys.version_info  # pylint: disable=C0103, invalid-name

    return any([
        all([implementation == 'CPython', v.major == 3, v.minor >= 6]),
        all([implementation == 'PyPy', v.major == 3, v.minor >= 5]),
    ])

if permit_setup():
    setup()
else:
    raise RuntimeError('CPython 3.6+ or PyPy 3.5+ required')