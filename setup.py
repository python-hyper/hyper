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

py_version = sys.version_info[:2]
py_long_version = sys.version_info[:3]

def resolve_install_requires():
    if py_version == (3,3):
        return ['pyOpenSSL>=0.15', 'service_identity>=14.0.0']
    elif py_version == (2,7) and py_long_version < (2,7,9):
        return ['pyOpenSSL>=0.15', 'service_identity>=14.0.0']
    return []

packages = [
    'hyper',
    'hyper.http20',
    'hyper.common',
    'hyper.http11',
    'hyper.packages',
    'hyper.packages.hpack',
    'hyper.packages.hyperframe',
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
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    install_requires=resolve_install_requires(),
    entry_points={
        'console_scripts': [
            'hyper = hyper.cli:main',
        ],
    },
    extras_require={
        'fast': ['pycohttpparser', 'nahpackpy'],
    }
)
