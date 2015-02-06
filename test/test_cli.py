# -*- coding: utf-8 -*-
from hyper.cli import _ARGUMENT_DEFAULTS
from hyper.cli import main, parse_argument

import pytest


@pytest.mark.parametrize('argv', [
    ['example.com'],
    ['example.com', '/home'],
    ['-v', 'example.com'],
    ['-n', 'example.com'],
], ids=[
    'specified host',
    'specified host with path',
    'specified host with "-v/--verbose" option',
    'specified host with "-n/--nullout" option',
])
def test_cli_normal(monkeypatch, argv):
    monkeypatch.setattr('hyper.cli.HTTP20Connection', DummyConnection)
    main(argv)
    assert True


@pytest.mark.parametrize('argv', [
    [],
    ['-h'],
], ids=[
    'specified no argument',
    'specified "-h" option',
])
def test_cli_with_system_exit(argv):
    with pytest.raises(SystemExit):
        main(argv)


@pytest.mark.parametrize('argv', [
    {'host': 'example.com'},
    {'host': 'example.com', 'path': '/home'},
    {'host': 'example.com', 'encoding': 'latin-1'},
    {'host': 'example.com', 'nullout': True},
    {'host': 'example.com', 'method': 'POST'},
    {'host': 'example.com', 'verbose': True},
], ids=[
    'specified host',
    'specified host with path',
    'specified host with "-e/--encoding" option',
    'specified host with "-m/--method" option',
    'specified host with "-n/--nullout" option',
    'specified host with "-v/--verbose" option',
])
def test_cli_parse_argument(argv):
    d = _ARGUMENT_DEFAULTS.copy()
    d.update(argv)
    _argv = ['-e', d['encoding'], '-m', d['method']]
    for key, value in d.items():
        if isinstance(value, bool) and value is True:
            _argv.append('--%s' % key)
    _argv.extend([d['host'], d['path']])

    args = parse_argument(_argv)
    for key in d.keys():
        assert getattr(args, key) == d[key]


def test_cli_with_main(monkeypatch):
    monkeypatch.setattr('sys.argv', ['./hyper'])
    import imp
    import hyper.cli
    with pytest.raises(SystemExit):
        imp.load_source('__main__', hyper.cli.__file__)


# mock for testing
class DummyResponse(object):
    def read(self):
        return b'<html>dummy</html>'


class DummyConnection(object):
    def __init__(self, host):
        self.host = host

    def request(self, method, path):
        return method, path

    def getresponse(self):
        return DummyResponse()
