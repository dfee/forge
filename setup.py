from setuptools import setup


setup(
    extras_require={
        'testing': [
            'coverage',
            'mypy',
            'pylint',
            'pytest',
        ],
    },
)