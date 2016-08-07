# -*- coding: utf-8 -*-
import json

import pytest

from hyper.cli import KeyValue
from hyper.cli import get_content_type_and_charset, main, parse_argument
from hyper.cli import set_request_data, set_url_info
from hyper.common.headers import HTTPHeaderMap


# mock for testing
class DummyUrlInfo(object):
    def __init__(self):
        self.path = '/'


class DummyNamespace(object):
    def __init__(self, attrs):
        self.body = {}
        self.headers = HTTPHeaderMap()
        self.items = []
        self.method = None
        self._url = ''
        self.url = DummyUrlInfo()
        for key, value in attrs.items():
            setattr(self, key, value)


class DummyResponse(object):
    def __init__(self, headers):
        self.headers = HTTPHeaderMap(headers.items())

    def read(self):
        ctype = self.headers.get('content-type')
        if ctype is not None:
            if 'json' in ctype[0].decode('utf-8'):
                return b'{"data": "dummy"}'
        return b'<html>dummy</html>'

    def getheader(self, name):
        return self.headers.get(name)

    def getheaders(self):
        return self.headers


class DummyConnection(object):
    def __init__(self, host, port, secure=False):
        self.host = host
        self.port = port
        self.response = DummyResponse({'content-type': 'application/json'})
        self.secure = secure

    def request(self, method, path, body, headers):
        return method, path, body, headers

    def get_response(self):
        return self.response


def _get_value(obj, key):
    if '.' in key:
        attr1, attr2 = key.split('.')
        return _get_value(getattr(obj, attr1), attr2)
    else:
        return getattr(obj, key)


@pytest.mark.parametrize('argv', [
    ['example.com'],
    ['example.com/'],
    ['http://example.com'],
    ['https://example.com'],
    ['https://example.com/'],
    ['https://example.com/httpbin/get'],
], ids=[
    'specified host only',
    'specified host and path',
    'specified host with url scheme http://',
    'specified host with url scheme https://',
    'specified host with url scheme https:// and root',
    'specified host with url scheme https:// and path',
])
def test_cli_normal(monkeypatch, argv):
    monkeypatch.setattr('hyper.cli.HTTPConnection', DummyConnection)
    main(argv)
    assert True


@pytest.mark.parametrize('argv', [
    [],
    ['-h'],
    ['--version'],
], ids=[
    'specified no argument',
    'specified "-h" option',
    'specified "--version" option',
])
def test_cli_with_system_exit(argv):
    with pytest.raises(SystemExit):
        main(argv)


@pytest.mark.parametrize(('argv', 'expected'), [
    (['--debug', 'example.com'], {'debug': True}),
    (['get', 'example.com'], {'method': 'GET'}),
    (['GET', 'example.com', 'x-test:header'],
     {'method': 'GET', 'headers': {'x-test': 'header'}}),
    (['GET', 'example.com', 'param==test'],
     {'method': 'GET', 'url.path': '/?param=test'}),
    (['POST', 'example.com', 'data=test'],
     {'method': 'POST', 'body': '{"data": "test"}'}),
    (['GET', 'example.com', ':authority:example.org'],
     {'method': 'GET', 'headers': {
                            ':authority': 'example.org'}}),
    (['GET', 'example.com', ':authority:example.org', 'x-test:header'],
     {'method': 'GET', 'headers': {
                            ':authority': 'example.org',
                            'x-test': 'header'}}),
], ids=[
    'specified "--debug" option',
    'specify host with lower get method',
    'specified host and additional header',
    'specified host and get parameter',
    'specified host and post data',
    'specified host and override default header',
    'specified host and override default header and additional header',
])
def test_parse_argument(argv, expected):
    args = parse_argument(argv)
    for key, value in expected.items():
        assert value == _get_value(args, key)


@pytest.mark.parametrize(('response', 'expected'), [
    (DummyResponse({}), ('unknown', 'utf-8')),
    (DummyResponse({'content-type': 'text/html; charset=latin-1'}),
     ('text/html', 'latin-1')),
    (DummyResponse({'content-type': 'application/json'}),
     ('application/json', 'utf-8')),
], ids=[
    'unknown conetnt type and default charset',
    'text/html and charset=latin-1',
    'application/json and default charset',
])
def test_get_content_type_and_charset(response, expected):
    ctype, charset = get_content_type_and_charset(response)
    assert expected == (ctype, charset)


@pytest.mark.parametrize(('args', 'expected'), [
    (DummyNamespace({}), {'headers': {}, 'method': 'GET'}),
    (
        DummyNamespace(
            {'items': [
                KeyValue('x-header', 'header', ':', ''),
                KeyValue('param', 'test', '==', ''),
            ]}
        ),
        {'headers': {'x-header': 'header'},
         'method': 'GET',
         'url.path': '/?param=test',
         }
    ),
    (
        DummyNamespace(
            {'items': [
                KeyValue('data1', 'test1', '=', ''),
                KeyValue('data2', 'test2', '=', ''),
            ]}
        ),
        {'headers': {'content-type': 'application/json'},
         'method': 'POST',
         'body': json.dumps({'data1': 'test1', 'data2': 'test2'}),
         }
    ),
], ids=[
    'set no request data',
    'set header and GET parameters',
    'set header and POST data',
])
def test_set_request_data(args, expected):
    set_request_data(args)
    for key, value in expected.items():
        assert value == _get_value(args, key)


@pytest.mark.parametrize(('args', 'expected'), [
    (DummyNamespace({'_url': ''}),
     {'query': None, 'host': 'localhost', 'fragment': None,
      'port': 443, 'netloc': None, 'scheme': 'https', 'path': '/',
      'secure': True}),
    (DummyNamespace({'_url': 'example.com'}),
     {'host': 'example.com', 'port': 443, 'path': '/', 'secure': True}),
    (DummyNamespace({'_url': 'example.com/httpbin/get'}),
     {'host': 'example.com', 'port': 443, 'path': '/httpbin/get',
     'secure': True}),
    (DummyNamespace({'_url': 'example.com:80'}),
     {'host': 'example.com', 'port': 80, 'path': '/', 'secure': True}),
    (DummyNamespace({'_url': 'http://example.com'}),
     {'host': 'example.com', 'port': 80, 'path': '/', 'scheme': 'http',
     'secure': False}),
    (DummyNamespace({'_url': 'http://example.com/'}),
     {'host': 'example.com', 'port': 80, 'path': '/', 'scheme': 'http',
     'secure': False}),
    (DummyNamespace({'_url': 'http://example.com:8080'}),
     {'host': 'example.com', 'port': 8080, 'path': '/', 'scheme': 'http',
     'secure': False}),
    (DummyNamespace({'_url': 'https://example.com'}),
     {'host': 'example.com', 'port': 443, 'path': '/', 'scheme': 'https',
     'secure': True}),
    (DummyNamespace({'_url': 'https://example.com/httpbin/get'}),
     {'host': 'example.com', 'port': 443, 'path': '/httpbin/get',
      'scheme': 'https', 'secure': True}),
    (DummyNamespace({'_url': 'https://example.com:8443/httpbin/get'}),
     {'host': 'example.com', 'port': 8443, 'path': '/httpbin/get',
      'scheme': 'https', 'secure': True}),
], ids=[
    'set no url (it means default settings)',
    'set only hostname',
    'set hostname with path',
    'set hostname with port number',
    'set url with http://',
    'set url + "/" with http://',
    'set url with http:// and port number',
    'set url with https://',
    'set url with path',
    'set url with port number and path',
])
def test_set_url_info(args, expected):
    set_url_info(args)
    for key, value in expected.items():
        assert value == getattr(args.url, key)
