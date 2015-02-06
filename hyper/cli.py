# -*- coding: utf-8 -*-
"""
hyper/cli
~~~~~~~~~

Command line interface for hyper.
"""
import argparse
import logging
import sys

from hyper import HTTP20Connection

log = logging.getLogger('hyper')

_ARGUMENT_DEFAULTS = {
    'encoding': 'utf-8',
    'host': None,
    'nullout': False,
    'method': 'GET',
    'path': '/',
    'verbose': False,
}


def parse_argument(argv=None):
    parser = argparse.ArgumentParser()
    parser.set_defaults(**_ARGUMENT_DEFAULTS)

    # positional arguments
    parser.add_argument('host', help='set host to request')
    parser.add_argument(
        'path', nargs='?',
        help='set path to resource (default: /)')

    # optional arguments
    parser.add_argument(
        '-e', '--encoding',
        help='set charset for content-type')
    parser.add_argument(
        '-n', '--nullout', action='store_true',
        help='do not show response data')
    parser.add_argument(
        '-m', '--method',
        help='set http method (default: GET)')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='set verbose mode (loglevel=DEBUG)')

    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    return args


def request(args):
    conn = HTTP20Connection(args.host)
    conn.request(args.method, args.path)
    response = conn.getresponse()
    return response.read()


def main(argv=None):
    args = parse_argument(argv)
    if args.verbose:
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        log.addHandler(handler)
        log.setLevel(logging.DEBUG)

    data = request(args)
    if not args.nullout:
        print(data.decode(args.encoding))


if __name__ == '__main__':
    main()
