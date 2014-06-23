#!/bin/bash

# Shell script for installing hyper's dependencies on Travis. In particular,
# this upgrades the OpenSSL version used on Travis.

set -e
set -x

sudo add-apt-repository -y "ppa:lukasaoz/openssl101-ppa"
sudo apt-get -y update
sudo apt-get install -y --force-yes openssl libssl libcrypto

pip install .
pip install -r test_requirements.txt
