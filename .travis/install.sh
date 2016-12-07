#!/bin/bash

set -e
set -x

if [[ "$HYPER_FAST_PARSE" = true ]]; then
    pip install pycohttpparser~=1.0
fi

pip install -U setuptools
pip install .
pip install -r test_requirements.txt
pip install flake8
