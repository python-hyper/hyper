#!/bin/bash

set -e
set -x

if [[ "$TEST_RELEASE" == true ]]; then
    py.test test_release.py
else
    if [[ $TRAVIS_PYTHON_VERSION == pypy* ]]; then
        py.test test/
    else
        coverage run -m py.test test/
        coverage report
    fi
fi
