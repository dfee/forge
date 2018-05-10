from setuptools import setup


setup(
    install_requires=[
        'dataclasses;python_version<"3.7"',
    ],
    extras_require={
        'testing': [
            'coverage',
            'mypy',
            'pylint',
            'pytest',
        ],
    },
)