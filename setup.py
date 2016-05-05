#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import sys

from setuptools import setup
from setuptools.command.test import test as TestCommand


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to py.test")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ['test/']

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(self.pytest_args)
        sys.exit(errno)


# Get the version
version_regex = r'__version__ = ["\']([^"\']*)["\']'
with open('hyper/__init__.py', 'r') as f:
    text = f.read()
    match = re.search(version_regex, text)

    if match:
        version = match.group(1)
    else:
        raise RuntimeError("No version number found!")

# Stealing this from Kenneth Reitz
if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit()

py_version = sys.version_info[:2]
py_long_version = sys.version_info[:3]

try:
    pypy_version = sys.pypy_version_info[:2]
except AttributeError:
    pypy_version = None


def resolve_install_requires():
    basic_dependencies = ['h2>=2.3,<3.0', 'hyperframe~=3.2']

    if py_version == (3, 3):
        basic_dependencies.extend(
            ['pyOpenSSL>=0.15', 'service_identity>=14.0.0']
        )
    elif py_version == (2, 7) and py_long_version < (2, 7, 9):
        basic_dependencies.extend(
            ['pyOpenSSL>=0.15', 'service_identity>=14.0.0']
        )

        # PyPy earlier than 2.6.0 doesn't support cryptography 1.0
        if pypy_version and pypy_version < (2, 6):
            basic_dependencies.append('cryptography<1.0')

    return basic_dependencies

packages = [
    'hyper',
    'hyper.http20',
    'hyper.common',
    'hyper.http11',
    'hyper.packages',
    'hyper.packages.rfc3986'
]

setup(
    name='hyper',
    version=version,
    description='HTTP/2 Client for Python',
    long_description=open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    author='Cory Benfield',
    author_email='cory@lukasa.co.uk',
    url='http://hyper.rtfd.org',
    packages=packages,
    package_data={'': ['LICENSE', 'README.rst', 'CONTRIBUTORS.rst', 'HISTORY.rst', 'NOTICES']},
    package_dir={'hyper': 'hyper'},
    include_package_data=True,
    license='MIT License',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    install_requires=resolve_install_requires(),
    tests_require=['pytest', 'requests', 'mock'],
    cmdclass={'test': PyTest},
    entry_points={
        'console_scripts': [
            'hyper = hyper.cli:main',
        ],
    },
    extras_require={
        'fast': ['pycohttpparser'],
    }
)
