# pytest-check-links

pytest plugin that checks URLs for HTML-containing files.

[![codecov](https://codecov.io/gh/jupyterlab/pytest-check-links/branch/master/graph/badge.svg)](https://codecov.io/gh/jupyterlab/pytest-check-links)
[![Tests](https://github.com/jupyterlab/pytest-check-links/workflows/Tests/badge.svg)](https://github.com/jupyterlab/pytest-check-links/actions?query=workflow%3ATests+branch%3Amaster)
[![PyPI version](https://badge.fury.io/py/pytest-check-links.svg)](https://badge.fury.io/py/pytest-check-links)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pytest-check-links)


## Supported files

- `.html`
- `.rst`
- `.md` (TODO: select renderer)
- `.ipynb` (requires `nbconvert`)

## Install

    pip install pytest-check-links

## Use

    pytest --check-links mynotebook.ipynb

## Configure

#### --links-ext

> default: `md,rst,html,ipynb`

A comma-separated list of extensions to check

#### --check-anchors

Also check whether links with `#anchors` HTML files (either local, or with
served with `html` in the `Content-Type`) actually exist, and point to _exactly one_
named anchor.

#### --check-links-ignore

A regular expression that matches URIs that should not be checked.
Can be specified multiple times for multiple ignore patterns.
This can be used for files that have a lot of links to GitHub pages,
such as a Changelog.  GitHub has rate limiting, which would normally cause these files to take up to an hour to complete for larger repositories.  For example:

    pytest --check-links --check-links-ignore "https://github.com/.*/pull/.*" CHANGELOG.md

### Cache

Caching requires the installation of `requests-cache`.

    pip install requests-cache

If enabled, each occurance of a link will be checked, no matter how many times
it appears in a collection of files to check.

#### --check-links-cache

Cache requests when checking links. Caching is disabled by default, and this option
must be provided, even if other cache configuration options are provided.

#### --check-links-cache-name

> default: `.pytest-check-links-cache`

Name of link cache, either the base name of a file or similar, depending on backend.

#### --check-links-cache-backend

> default: `sqlite3`

Cache persistence backend. The other known backends are:
- `memory`
- `redis`
- `mongodb`

See the [requests-cache documentation](https://requests-cache.readthedocs.io)
for more information.

#### --check-links-cache-expire-after

> default: `None` (unlimited)

Time to cache link responses (seconds).

#### --check-links-cache-backend-opt

Backend-specific options for link cache, provided as `key:value`. These are passed
directly to the `requests_cache.CachedSession` constructor, as they vary depending
on the backend.

Values will be parsed as JSON first, so to overload the default of caching all
HTTP response codes (which requires a list of `int`s):

```bash
--check-links-backend-opt allowable_codes:[200]
```


## TODO

- pick a markdown renderer (probably commonmark) or make the markdown renderer pluggable
- options for validating links (allow absolute links, only remote or local, etc.)
- find URLs in Python docstrings
