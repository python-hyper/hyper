#!/usr/bin/env python
# -*- coding: utf-8 -*-
import itertools
import os
import re
import sys

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

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

def resolve_extras():
    py_version = sys.version_info[:2]
    if py_version in [(2,7), (3,3)]:
        extras = dict(
            TLS=['pyOpenSSL>=0.14'],
            # TODO NPN=['pyOpenSSL>=0.15'],
        )
    else:
        extras = dict(
            TLS=[],
        )
    extras['all'] = itertools.chain(*extras.values())
    return extras

packages = ['hyper', 'hyper.http20']

setup(
    name='hyper',
    version=version,
    description='HTTP/2.0 for Python',
    long_description=open('README.rst').read() + '\n\n' + open('HISTORY.rst').read(),
    author='Cory Benfield',
    author_email='cory@lukasa.co.uk',
    url='http://hyper.rtfd.org',
    packages=packages,
    package_data={'': ['LICENSE', 'README.rst', 'CONTRIBUTORS.rst', 'HISTORY.rst']},
    package_dir={'hyper': 'hyper'},
    include_package_data=True,
    license='MIT License',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
    ],
    extras_require=resolve_extras(),
)
