from setuptools import setup


setup(
    name='forge',
    version='0.1',
    author='Devin Fee',
    author_email='devin@devinfee.com',
    description='Counterfeit (function) signatures for fun and profit',
    license='MIT',
    keywords='signatures parameters arguments',
    url='http://github.com/dfee/forge',
    py_modules=['forge'],
    long_description=__doc__,
    python_requires='~=3.3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.3',
    ],
    extras_require={
        'testing': [
            'mypy',
            'pylint',
            'pytest',
            'pytest-cov',
        ],
    }
)