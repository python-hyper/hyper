# Hyper: HTTP Abstraction for Python

HTTP is changing under our feet. HTTP/1.1, our old friend, is being
supplemented by the brand new HTTP/2.0 standard. HTTP/2.0 provides many
benefits: improved speed, lower bandwidth usage, better connection management,
and more.

Unfortunately, most web servers do not support HTTP/2.0 at this time. What's
needed is to abstract the difference between HTTP/1.1 and HTTP/2.0, so that
your application can reap the benefits of HTTP/2.0 when possible whilst
maintaining maximum compatibility.

Enter `hyper`:

    from hyper import HTTPConnection

    conn = HTTPConnection("www.python.org")
    conn.request("GET", "/index.html")

    r1 = conn.getresponse()

Did that code use HTTP/1.1, or HTTP/2.0? You don't have to worry. Whatever
`www.python.org` supports, `hyper` will use.

## Compatibility

`hyper` is intended to be a drop-in replacement for `httplib`/`http.client`,
with an identical API. You can get all of the HTTP/2.0 goodness by simply
replacing your `import httplib` or `import http.client` line with
`import hyper as httplib` or `import hyper as http.client`. You should then be
good to go.

## License

`hyper` is made available under the MIT License. For more details, see the
`LICENSE` file in the repository.

## Maintainer

`hyper` is maintained by Cory Benfield.
