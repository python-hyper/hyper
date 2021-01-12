#!/bin/bash

set -e
set -x

if [[ "$HYPER_FAST_PARSE" = true ]]; then
    pip install pycohttpparser~=1.0
fi

pip install -U pip
pip install -U setuptools wheel build
python3 -m build -nwx .
pip install --upgrade ./dist/*.whl
pip install -r test_requirements.txt
pip install flake8
