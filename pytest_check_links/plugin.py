from docutils.core import publish_parts
import io
import os
import time
import warnings

import html5lib
import pytest
import requests

from .args import StoreExtensionsAction, StoreCacheAction

_ENC = 'utf8'

default_extensions = {'.md', '.rst', '.html', '.ipynb'}
supported_extensions = {'.md', '.rst', '.html', '.ipynb'}

default_cache = dict(
    cache_name='.pytest-check-links-cache',
    backend=None,
    expire_after=None,
    allowable_codes=list(range(200, 512)),
)


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption('--check-links', action='store_true',
        help="Check links for validity")
    group.addoption('--check-anchors', action='store_true',
        help="Check link anchors for validity")
    group.addoption('--links-ext', action=StoreExtensionsAction,
        default=default_extensions,
        help="Which file extensions to check links for, "
             "as a comma-separated list of values. Supported "
             "extensions are: %s." %
                extensions_str(supported_extensions))

    group.addoption('--check-links-cache', action='store_true',
        help="Cache requests when checking links")
    group.addoption('--check-links-cache-name', action=StoreCacheAction,
        default="pytest-check-links", help="Name of link cache")
    group.addoption('--check-links-cache-backend', action=StoreCacheAction,
        default=None, help="Cache persistence backend")
    group.addoption('--check-links-cache-expire-after', action=StoreCacheAction,
        default=300, help="Time to cache link responses (seconds)")
    group.addoption('--check-links-cache-allowable-codes', action=StoreCacheAction,
        default=[200, 404], help="HTTP response codes to cache")
    group.addoption('--check-links-cache-backend-opt', action=StoreCacheAction,
        default=[200, 404], help="Backend-specific options for link cache")


def pytest_configure(config):
    if config.option.links_ext:
        validate_extensions(config.option.links_ext)

def pytest_collect_file(path, parent):
    config = parent.config
    if config.option.check_links:
        cache_kwargs = None
        if config.option.check_links_cache:
            cache_kwargs = getattr(config.option, "check_links_cache_kwargs", {})
        if path.ext.lower() in config.option.links_ext:
            return CheckLinks(path, parent, config.option.check_anchors, cache_kwargs)


class CheckLinks(pytest.File):
    """Check the links in a file"""
    def __init__(self, path, parent, check_anchors=False, cache_kwargs=None):
        super(CheckLinks, self).__init__(path, parent)
        self.check_anchors = check_anchors
        if cache_kwargs is not None:
            from requests_cache import CachedSession
            final_cache_kwargs = dict(default_cache)
            final_cache_kwargs.update(cache_kwargs)
            session = CachedSession(**final_cache_kwargs)
            if final_cache_kwargs.get("expire_after"):
                session.remove_expired_responses()
        else:
            session = requests.Session()

        session.headers['User-Agent'] = 'pytest-check-links'
        self.requests_session = session

    def _html_from_html(self):
        """Return HTML from an HTML file"""
        with io.open(str(self.fspath), encoding=_ENC) as f:
            return f.read()

    def _html_from_markdown(self):
        """Return HTML from a markdown file"""
        # FIXME: use commonmark or a pluggable engine
        from nbconvert.filters import markdown2html
        with io.open(str(self.fspath), encoding=_ENC) as f:
            markdown = f.read()
        return markdown2html(markdown)

    def _html_from_rst(self):
        """Return HTML from an rst file"""
        with io.open(str(self.fspath), encoding=_ENC) as f:
            rst = f.read()
        return publish_parts(rst, writer_name='html')['html_body']

    def _items_from_notebook(self):
        """Yield LinkItems from a notebook"""
        import nbformat
        from nbconvert.filters import markdown2html

        nb = nbformat.read(str(self.fspath), as_version=4)
        for cell_num, cell in enumerate(nb.cells):
            if cell.cell_type != 'markdown':
                continue

            html = markdown2html(cell.source)
            basename = 'Cell %i' % cell_num
            for item in links_in_html(basename, self, html):
                yield item

    def collect(self):
        path = self.fspath
        if path.ext == '.ipynb':
            for item in self._items_from_notebook():
                yield item
            return

        if path.ext == '.html':
            html = self._html_from_html()
        elif path.ext == '.md':
            html = self._html_from_markdown()
        elif path.ext == '.rst':
            html = self._html_from_rst()

        for item in links_in_html(path, self, html):
            yield item


class BrokenLinkError(Exception):
    def __init__(self, url, error):
        self.url = url
        self.error = error

    def __repr__(self):
        return "<%s url=%s, error=%s>" % (
            self.__class__.__name__, self.url, self.error
        )


def links_in_html(base_name, parent, html):
    """Yield LinkItems from a markdown cell

    Parsed HTML with html5lib, yielding LinkItems for testing.
    """
    parsed = html5lib.parse(html, namespaceHTMLElements=False)

    for element in parsed.getiterator():
        url = None
        tag = element.tag
        if tag == 'a':
            attr = 'href'
            url = element.get('href', '')
            if url.startswith('#') and not parent.check_anchors:
                # skip internal links
                continue

        elif tag in {'img', 'iframe'}:
            attr = 'src'
        else:
            continue

        url = element.get(attr)
        name = '{} <{} {}={}>'.format(base_name, tag, attr, url)

        if url:
            if ':' in url:
                proto = url.split(':', 1)[0]
                if proto.lower() not in {'http', 'https'}:
                    # ignore non-http links (mailto:, data:, etc.)
                    continue
            yield LinkItem(name, parent, url, parsed)


class LinkItem(pytest.Item):
    """Test item for an HTML link

    Args:

        name, parent: inherited from pytest.Item
        target (str): The URL or path target for the link
        parsed (xml.etree.ElementTree.Element): The parsed HTML
        description (str, optional): The description to be used in the report header
    """
    def __init__(self, name, parent, target, parsed, description=''):
        super(LinkItem, self).__init__(name, parent)
        self.target = target
        self.parsed = parsed
        self.description = description or '{}: {}'.format(self.fspath, target)

    def repr_failure(self, excinfo):
        exc = excinfo.value
        if isinstance(exc, BrokenLinkError):
            return '{}: {}'.format(exc.url, exc.error)
        else:
            return super(LinkItem, self).repr_failure(excinfo)

    def reportinfo(self):
        return self.fspath, 0, self.description

    def sleep(self, response):
        """Handle responses with a Retry-After header.

        https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.37
        """
        header = response.headers.get('Retry-After')

        if header is None:
            return False

        if header == '1m0s':
            sleep_time = 60
        else:
            try:
                sleep_time = int(sleep_time)
            except ValueError:
                sleep_time = 10

        time.sleep(sleep_time)

        return True

    def handle_anchor(self, parsed, anchor):
        """Verify an anchor exists in the parsed HTML
        """
        anchors = parsed.findall('*//a[@name="{}"]'.format(anchor))

        if not anchors:
            raise BrokenLinkError(self.target, "Missing anchor: %s" % anchor)

        if len(anchors) > 1:
            raise BrokenLinkError(
                self.target,
                "Ambiguous anchor: %d (found %s)" % (
                    len(anchors), anchor
                )
            )

    def fetch_with_retries(self, url, retries=3):
        """Fetch a URL, optionally retrying after a delay (by header)
        """
        response = self.parent.requests_session.get(url)

        if response.status_code >= 400:
            if retries and self.sleep(response):
                return self.fetch_with_retries(url, retries=retries - 1)

            raise BrokenLinkError(url, "%d: %s" % (
                response.status_code,
                response.reason
            ))

    def runtest(self):
        if ':' in self.target:
            return self.fetch_with_retries(self.target)
        else:
            if self.target.startswith('/'):
                raise BrokenLinkError(self.target, "absolute path link")
            # relative URL
            url = self.target
            anchor = None
            if '?' in url:
                url = url.split('?')[0]
            if '#' in url:
                url, anchor = url.split('#')

            if not url and anchor:
                if self.parent.check_anchors:
                    self.handle_anchor(self.parsed, anchor)
                return

            url_path = requests.compat.unquote(url).replace('/', os.path.sep)
            dirpath = self.fspath.dirpath()
            exists = False
            for ext in supported_extensions:
                rel_path = url_path.replace('.html', ext)
                target_path = dirpath.join(rel_path)
                if target_path.exists():
                    exists = True
                    # only check anchors in html for now
                    if ext == ".html" and anchor and self.parent.check_anchors:
                        with target_path.open() as fpt:
                            parsed = html5lib.parse(fpt, namespaceHTMLElements=False)
                            return self.handle_anchor(parsed, anchor)
                    break
            if not exists:
                target_path = dirpath.join(url_path)
                raise BrokenLinkError(self.target, "No such file: %s" % target_path)


def extensions_str(extensions):
    if not extensions:
        return ''
    extensions = ['"%s"' % e.lstrip('.') for e in extensions if e]
    if len(extensions) == 1:
        return extensions[0]
    return (", ".join(extensions[:-1]) +
            " and %s" % extensions[-1])


def validate_extensions(extensions):
    invalid = set(extensions) - supported_extensions
    if invalid:
        warnings.warn("C1", "Unsupported extensions for check-links: %s" %
            extensions_str(invalid))
