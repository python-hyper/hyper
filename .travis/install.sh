#!/bin/bash

set -e
set -x

if [[ "$NGHTTP2" = true ]]; then
    # GCC 4.6 seems to cause problems, so go straight to 4.8.
    sudo add-apt-repository --yes ppa:ubuntu-toolchain-r/test
    sudo apt-get update
    sudo apt-get install g++-4.8 libstdc++-4.8-dev
    export CXX="g++-4.8" CC="gcc-4.8"
    $CC --version

    # Install nghttp2. Right now I haven't built a PPA for this so we have to
    # do it from source, which kinda sucks. First, install a ton of
    # prerequisite packages.
    sudo apt-get install autoconf automake autotools-dev libtool pkg-config \
                         zlib1g-dev libcunit1-dev libssl-dev libxml2-dev \
                         libevent-dev libjansson-dev libjemalloc-dev
    pip install cython

    # Now, download and install nghttp2's latest version.
    git clone https://github.com/tatsuhiro-t/nghttp2.git
    cd nghttp2
    DIR=`pwd`
    export PYTHONPATH="$DIR/lib/python${TRAVIS_PYTHON_VERSION}/site-packages"
    mkdir -p $PYTHONPATH
    autoreconf -i
    automake
    autoconf
    ./configure --disable-threads --prefix=`pwd`
    make
    make install

    # The makefile doesn't install into the active virtualenv. Install again.
    cd python
    python setup.py install
    cd ../..

    # Let's try ldconfig.
    sudo sh -c 'echo "/usr/local/lib" > /etc/ld.so.conf.d/libnghttp2.conf'
    sudo ldconfig
fi

if [[ "$HYPER_FAST_PARSE" = true ]]; then
    pip install pycohttpparser~=1.0
fi

pip install -U setuptools
pip install .
pip install -r test_requirements.txt
pip install flake8
