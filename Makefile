.PHONY: certs publish test

certs:
	curl https://mkcert.org/generate/ -o hyper/certs.pem

publish:
	rm -rf dist/
	python setup.py sdist bdist_wheel
	twine upload -s dist/*

test:
	py.test -n 4 --cov hyper test/
