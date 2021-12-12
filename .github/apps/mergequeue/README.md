Installation
============

`mergequeue` is a HTTP server meant to handle webhook event emitted from Github.
Registered as a Github App, it allows user to request automated merging from
a pull request comment. Each merge request is put in a queue and process by order
of arrival.

`mergequeue` requires Python 3.X.

If you want to work on `mergequeue`, you can setup the development environment with:
```
python3 -m venv env;
env/bin/python3 -m pip install flask pygithub
```
It will build a Python virtual environment and install (locally) the required
dependencies.


Documentation
=============

You can build the documentation using Sphinx with:
```
env/bin/python3 -m pip install sphinx sphinx_rtd_theme
env/bin/sphinx-build doc doc/html
```
Browse it from http://localhost:8000/ with:
```
cd doc/html && env/bin/python3 -m http.server
```

Configuration
=============

_Has to be implemented_

`config/mergequeue.ini.dist` is a comprehensive and documented configuration file.


Tests
=====

_Has to be implemented_

You can run the unit test suite with:
```
env/bin/python3 -m unittest
```

Run mergequeue
==============

You can start `mergequeue` as a daemon with the following command:
```
env/bin/python3 src/mergequeue.py <repository_owner> <repository_name> <personnal_access_token>
```
