from docutils.core import publish_parts
import io
import os
import time
import warnings
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import unquote

import html5lib
import pytest

from .args import StoreExtensionsAction

_ENC = 'utf8'

default_extensions = {'.md', '.rst', '.html', '.ipynb'}
supported_extensions = {'.md', '.rst', '.html', '.ipynb'}


def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption('--check-links', action='store_true',
        help="Check links for validity")
    group.addoption('--links-ext', action=StoreExtensionsAction,
        default=default_extensions,
        help="Which file extensions to check links for, "
             "as a comma-separated list of values. Supported "
             "extensions are: %s." %
                extensions_str(supported_extensions))


def pytest_configure(config):
    if config.option.links_ext:
        validate_extensions(config.option.links_ext)


def pytest_collect_file(path, parent):
    config = parent.config
    if config.option.check_links:
        if path.ext.lower() in config.option.links_ext:
            return CheckLinks(path, parent)


class CheckLinks(pytest.File):
    """Check the links in a file"""
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
            if url.startswith('#'):
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
            yield LinkItem(name, parent, url)


class LinkItem(pytest.Item):
    """Test item for an HTML link

    Args:

        name, parent: inherited from pytest.Item
        target (str): The URL or path target for the link
        description (str, optional): The description to be used in the report header
    """
    def __init__(self, name, parent, target, description=''):
        super(LinkItem, self).__init__(name, parent)
        self.target = target
        self.retry_attempts = 0
        self.description = description or '{}: {}'.format(self.fspath, target)

    def repr_failure(self, excinfo):
        exc = excinfo.value
        if isinstance(exc, BrokenLinkError):
            return '{}: {}'.format(exc.url, exc.error)
        else:
            return super(LinkItem, self).repr_failure(excinfo)

    def reportinfo(self):
        return self.fspath, 0, self.description

    def handle_retry(self, obj):
        """Handle responses with a Retry-After header.

        https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.37
        """
        if self.retry_attempts < 3:
            try:
                sleep_time = int(obj.headers['Retry-After'])
            except ValueError:
                sleep_time = 10
            # Github uses this non-conforming Retry-After
            if obj.headers['Retry-After'] == '1m0s':
                sleep_time = 60
            self.retry_attempts += 1
            time.sleep(sleep_time)
            return self.runtest()

        raise BrokenLinkError(self.target, "%s %s" % (obj.code, obj.reason))

    def runtest(self):
        if ':' in self.target:
            # external reference, download
            req = Request(self.target)
            req.add_header('User-Agent', 'pytest-check-links')
            try:
                f = urlopen(req)
            except Exception as e:
                if hasattr(e, 'headers') and 'Retry-After' in e.headers:
                    return self.handle_retry(e)
                raise BrokenLinkError(self.target, str(e))
            else:
                code = f.getcode()
                f.close()
                if code >= 400:
                    if 'Retry-After' in f.headers:
                        return self.handle_retry(e)
                    raise BrokenLinkError(self.target, str(code))
        else:
            if self.target.startswith('/'):
                raise BrokenLinkError(self.target, "absolute path link")
            # relative URL
            url = self.target
            if '?' in url:
                url = url.split('?')[0]
            if '#' in url:
                url = url.split('#')[0]

            url_path = unquote(url).replace('/', os.path.sep)
            dirpath = self.fspath.dirpath()
            exists = False
            for ext in supported_extensions:
                rel_path = url_path.replace('.html', ext)
                target_path = dirpath.join(rel_path)
                if target_path.exists():
                    exists = True
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
