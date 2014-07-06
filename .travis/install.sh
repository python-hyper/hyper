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
    wget https://github.com/tatsuhiro-t/nghttp2/releases/download/v0.4.1/nghttp2-0.4.1.tar.gz
    tar -xzvf nghttp2-0.4.1.tar.gz
    cd nghttp2-0.4.1
    autoreconf -i
    automake
    autoconf
    ./configure
    make
    sudo make install

    # The makefile doesn't install into the active virtualenv. Install again.
    cd python
    python setup.py install
    cd ../..
fi

pip install .
pip install -r test_requirements.txt
