import os
from six.moves.urllib.request import urlopen, Request
from six.moves.urllib.parse import unquote

import html5lib
import pytest

def pytest_addoption(parser):
    group = parser.getgroup("general")
    group.addoption('--check-links', action='store_true',
        help="Check links for validity")


def pytest_collect_file(path, parent):
    config = parent.config
    if config.option.check_links:
        if path.ext.lower() in {'.md', '.html', '.ipynb'}:
            return CheckLinks(path, parent)


class CheckLinks(pytest.File):
    """Check the links in a file"""
    def _html_from_html(self):
        """Return HTML from an HTML file"""
        with open(str(self.fspath)) as f:
            return f.read()
    
    def _html_from_markdown(self):
        """Return HTML from a markdown file"""
        # FIXME: use commonmark or a pluggable engine
        from nbconvert.filters import markdown2html
        with open(str(self.fspath)) as f:
            markdown = f.read()
        return markdown2html(markdown)
    
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
        fspath (localpath): The file containing the link (for relative URLs)
    """
    def __init__(self, name, parent, target, description=''):
        super(LinkItem, self).__init__(name, parent)
        self.target = target
        self.description = description or '{}: {}'.format(self.fspath, target)

    def repr_failure(self, excinfo):
        exc = excinfo.value
        if isinstance(exc, BrokenLinkError):
            return '{}: {}'.format(exc.url, exc.error)
        else:
            return super(LinkItem, self).repr_failure(excinfo)

    def reportinfo(self):
        return self.fspath, 0, self.description

    def runtest(self):
        if ':' in self.target:
            # external reference, download
            req = Request(self.target)
            req.add_header('User-Agent', 'pytest-check-links')
            try:
                f = urlopen(req)
            except Exception as e:
                raise BrokenLinkError(self.target, str(e))
            else:
                code = f.getcode()
                f.close()
                if code >= 400:
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
            target_path = self.fspath.dirpath().join(url_path)
            if not target_path.exists():
                raise BrokenLinkError(self.target, "No such file: %s" % target_path)
