import platform
import sys
from setuptools import setup


def permit_setup():
    # pylint: disable=W0612, unused-variable
    implementation = platform.python_implementation()
    ver = sys.version_info

    if not any([
            implementation == 'CPython' and ver.major == 3 and ver.minor >= 6,
            implementation == 'PyPy' and ver.major == 3 and ver.minor >= 5,
        ]):
        raise RuntimeError('CPython 3.6+ or PyPy 3.5+ required')

if permit_setup():
    setup()