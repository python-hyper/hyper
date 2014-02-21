certs:
	curl http://ci.kennethreitz.org/job/ca-bundle/lastSuccessfulBuild/artifact/cacerts.pem -o hyper/certs.pem

publish:
	python setup.py sdist upload
	python setup.py bdist_wheel upload
