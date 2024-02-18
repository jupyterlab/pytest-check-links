"""pytest-check-links plugin."""
from __future__ import annotations

import os
import re
import time
import warnings
from pathlib import Path
from typing import Any, Generator, cast
from xml.etree.ElementTree import Element

import html5lib
import pytest
from docutils.core import publish_parts
from requests import Request, Response, Session
from requests.utils import unquote  # type:ignore[attr-defined]

from .args import StoreCacheAction, StoreExtensionsAction

_ENC = "utf8"

default_extensions = {".md", ".rst", ".html", ".ipynb"}
supported_extensions = {".md", ".rst", ".html", ".ipynb"}

default_cache = {
    "cache_name": ".pytest-check-links-cache",
    "backend": None,
    "expire_after": None,
    "allowable_codes": list(range(200, 512)),
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add options to pytest."""
    group = parser.getgroup("general")
    group.addoption("--check-links", action="store_true", help="Check links for validity")
    group.addoption("--check-anchors", action="store_true", help="Check link anchors for validity")
    group.addoption(
        "--links-ext",
        action=StoreExtensionsAction,
        default=default_extensions,
        help="Which file extensions to check links for, "
        "as a comma-separated list of values. Supported "
        "extensions are: %s." % extensions_str(supported_extensions),
    )
    group.addoption(
        "--check-links-ignore",
        action="append",
        help="A list of regular expressions that match URIs that should not be checked.",
    )
    group.addoption(
        "--check-links-cache", action="store_true", help="Cache requests when checking links"
    )
    group.addoption("--check-links-cache-name", action=StoreCacheAction, help="Name of link cache")
    group.addoption(
        "--check-links-cache-backend", action=StoreCacheAction, help="Cache persistence backend"
    )
    group.addoption(
        "--check-links-cache-expire-after",
        action=StoreCacheAction,
        help="Time to cache link responses (seconds)",
    )
    group.addoption(
        "--check-links-cache-allowable-codes",
        action=StoreCacheAction,
        help="HTTP response codes to cache",
    )
    group.addoption(
        "--check-links-cache-backend-opt",
        action=StoreCacheAction,
        help="Backend-specific options for link cache, specified as `opt:value`",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest."""
    if config.option.links_ext:
        validate_extensions(config.option.links_ext)


def pytest_collect_file(path: Any, parent: pytest.Collector) -> CheckLinks | None:
    """Add pytest file collection filter."""
    config = parent.config
    ignore_links = config.option.check_links_ignore

    if config.option.check_links:
        requests_session = ensure_requests_session(config)
        if path.ext.lower() in config.option.links_ext:
            path_obj = Path(path)
            check_anchors = config.option.check_anchors
            if hasattr(CheckLinks, "from_parent"):
                return cast(
                    CheckLinks,
                    CheckLinks.from_parent(
                        parent,
                        path=path_obj,
                        requests_session=requests_session,
                        check_anchors=check_anchors,
                        ignore_links=ignore_links,
                    ),
                )
            return CheckLinks(
                path=path_obj,
                parent=parent,
                requests_session=requests_session,
                check_anchors=check_anchors,
                ignore_links=ignore_links,
            )
    return None


def ensure_requests_session(config: pytest.Config) -> Session:
    """Build the singleton requests.Session (or subclass)"""
    session_attr = "check_links_requests_session"
    if not hasattr(config.option, session_attr):
        if config.option.check_links_cache:
            from requests_cache import CachedSession

            conf_kwargs = getattr(config.option, "check_links_cache_kwargs", {})
            kwargs = dict(default_cache)
            kwargs.update(conf_kwargs)
            requests_session = CachedSession(**kwargs)  # type:ignore[arg-type]
            if kwargs.get("expire_after"):
                requests_session.cache.delete(expired=True)
        else:
            requests_session = Session()  # type:ignore[assignment]

        requests_session.headers["User-Agent"] = "pytest-check-links"

        setattr(config.option, session_attr, requests_session)

    return cast(Session, getattr(config.option, session_attr))


class CheckLinks(pytest.File):
    """Check the links in a file"""

    def __init__(
        self,
        *,
        requests_session: Session | None = None,
        check_anchors: bool = False,
        ignore_links: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize."""
        super().__init__(**kwargs)
        self.check_anchors = check_anchors
        self.requests_session = requests_session
        self.ignore_links = ignore_links or []

    def teardown(self) -> None:
        """Teardown the handler."""
        if self.requests_session:
            self.requests_session.close()

    def _html_from_html(self) -> str:
        """Return HTML from an HTML file"""
        with Path(self.path).open(encoding=_ENC) as f:
            return f.read()

    def _html_from_markdown(self) -> str:
        """Return HTML from a markdown file"""
        # FIXME: use commonmark or a pluggable engine
        from nbconvert.filters import markdown2html

        with Path(self.path).open(encoding=_ENC) as f:
            markdown = f.read()
        return markdown2html(markdown)

    def _html_from_rst(self) -> str:
        """Return HTML from an rst file"""
        with Path(self.path).open(encoding=_ENC) as f:
            rst = f.read()
        return cast(
            str, publish_parts(rst, source_path=str(self.path), writer_name="html")["html_body"]
        )

    def _items_from_notebook(self) -> Generator[LinkItem, None, None]:
        """Yield LinkItems from a notebook"""
        import nbformat
        from nbconvert.filters.markdown_mistune import IPythonRenderer, MarkdownWithMath

        nb = nbformat.read(str(self.path), as_version=4)  # type:ignore[no-untyped-call]
        for cell_num, cell in enumerate(nb.cells):
            if cell.cell_type != "markdown":
                continue

            attachments = cell.get("attachments", {})
            renderer = IPythonRenderer(escape=False, attachments=attachments)
            html = MarkdownWithMath(renderer=renderer).render(cell.source)
            basename = "Cell %i" % cell_num
            for item in links_in_html(basename, self, html):
                if not item.target:
                    continue
                ignore = False
                for pattern in self.ignore_links:
                    if re.match(pattern, item.target):
                        ignore = True
                if not ignore:
                    yield item

    def collect(self) -> Generator[LinkItem, None, None]:
        """Collect the test."""
        path = self.path
        if path.suffix == ".ipynb":
            for item in self._items_from_notebook():
                yield item
            return

        if path.suffix == ".html":
            html = self._html_from_html()
        elif path.suffix == ".md":
            html = self._html_from_markdown()
        elif path.suffix == ".rst":
            html = self._html_from_rst()

        for item in links_in_html(str(path), self, html):
            if not item.target:
                continue
            ignore = False
            for pattern in self.ignore_links:
                if re.match(pattern, item.target):
                    ignore = True
            if not ignore:
                yield item


class BrokenLinkError(Exception):
    """A broken link error."""

    def __init__(self, url: str, error: Exception | str) -> None:
        """Initialize the error."""
        self.url = url
        self.error = error

    def __repr__(self) -> str:
        """The repr for the error."""
        return f"<{self.__class__.__name__} url={self.url}, error={self.error}>"


def links_in_html(base_name: str, parent: CheckLinks, html: str) -> Generator[LinkItem, None, None]:
    """Yield LinkItems from a markdown cell

    Parsed HTML with html5lib, yielding LinkItems for testing.
    """
    parsed = html5lib.parse(html, namespaceHTMLElements=False)

    for element in parsed.iter():
        url = None
        tag = element.tag
        if tag == "a":
            attr = "href"
            url = element.get("href", "")
            if url.startswith("#") and not parent.check_anchors:
                # skip internal links
                continue

        elif tag in {"img", "iframe"}:
            attr = "src"
        else:
            continue

        url = element.get(attr)
        name = f"{base_name} <{tag} {attr}={url}>"

        if url:
            if ":" in url:
                proto = url.split(":", 1)[0]
                if proto.lower() not in {"http", "https"}:
                    # ignore non-http links (mailto:, data:, etc.)
                    continue
            if hasattr(LinkItem, "from_parent"):
                yield LinkItem.from_parent(parent, name=name, target=url, parsed=parsed)
            else:
                yield LinkItem(name=name, parent=parent, target=url, parsed=parsed)


class LinkItem(pytest.Item):

    """Test item for an HTML link

    Args:

        name, parent: inherited from pytest.Item
        target (str): The URL or path target for the link
        parsed (xml.etree.ElementTree.Element): The parsed HTML
        description (str, optional): The description to be used in the report header
    """

    parent: CheckLinks

    def __init__(
        self,
        name: str | None = None,
        parent: CheckLinks | None = None,
        target: str | None = None,
        parsed: Element | None = None,
        description: str = "",
        **kwargs: Any,
    ):
        """Initialize the item."""
        super().__init__(name, parent, **kwargs)
        self.target = target
        self.parsed = parsed
        self.description = description or f"{self.path}: {target}"

    def repr_failure(self, excinfo: Any) -> str:  # type:ignore[override]
        """Repr for a failure."""
        exc = excinfo.value
        if isinstance(exc, BrokenLinkError):
            return f"{exc.url}: {exc.error}"
        return str(super().repr_failure(excinfo))

    def reportinfo(self) -> tuple[Path, int, str]:
        """Get the report information."""
        return self.path, 0, self.description

    def sleep(self, headers: dict[str, Any] | None) -> bool:
        """Handle responses or errors with a Retry-After header.

        https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.37
        """
        if headers is None:
            return False

        header = headers.get("Retry-After")

        if header is None:
            return False

        if header == "1m0s":
            sleep_time = 60
        else:
            try:
                sleep_time = int(header)
            except ValueError:
                sleep_time = 10

        time.sleep(sleep_time)

        return True

    def handle_anchor(self, parsed: Element, anchor: str) -> None:
        """Verify an anchor exists in the parsed HTML"""
        anchors = set(parsed.findall(f'*//a[@name="{anchor}"]'))
        anchors |= set(parsed.findall(f'*//*[@id="{anchor}"]'))
        if not self.target:
            return

        if not anchors:
            raise BrokenLinkError(self.target, "Missing anchor: %s" % anchor)

        if len(anchors) > 1:
            raise BrokenLinkError(
                self.target, "Ambiguous anchor: %d (found %s)" % (len(anchors), anchor)
            )

    def fetch_with_retries(self, url: str, retries: int = 3) -> Response:
        """Fetch a URL, optionally retrying after a delay (by header)"""

        url_no_anchor = url.split("#")[0]
        session = self.parent.requests_session
        if session is None:
            msg = "No session!"
            raise RuntimeError(msg)

        try:
            response = session.get(url_no_anchor)
        except Exception as err:
            if hasattr(err, "headers") and retries and self.sleep(err.headers):
                self.uncache_url(url_no_anchor)
                return self.fetch_with_retries(url, retries=retries - 1)

            raise BrokenLinkError(url, "%s" % err) from err

        if response.status_code >= 400:
            if retries and self.sleep(response.headers):  # type:ignore[arg-type]
                self.uncache_url(url_no_anchor)
                return self.fetch_with_retries(url, retries=retries - 1)

            raise BrokenLinkError(url, "%d: %s" % (response.status_code, response.reason))

        return response

    def uncache_url(self, url: str) -> bool:
        """Uncache a url."""
        from requests_cache import BaseCache  # type:ignore[attr-defined]

        uncached = False
        session = self.parent.requests_session
        if session is None:
            msg = "No current session"
            raise ValueError(msg)
        if hasattr(session, "cache"):
            request = Request("GET", url, headers=session.headers).prepare()
            if session.cache is None:
                msg = "No session cache found"
                raise ValueError(msg)
            cache: BaseCache = session.cache
            key = cache.create_key(request)
            if cache.contains(key):
                session.cache.delete(key)
                uncached = True
        return uncached

    def runtest(self) -> None:
        """Run the test."""
        url = self.target or ""

        if ":" in url:
            response = self.fetch_with_retries(url)
            if self.parent.check_anchors and "#" in url:
                anchor = url.split("#")[1]
                if anchor and "html" in response.headers.get("Content-Type", ""):
                    parsed = html5lib.parse(response.content, namespaceHTMLElements=False)
                    return self.handle_anchor(parsed, anchor)
        else:
            if url.startswith("/"):
                raise BrokenLinkError(url, "absolute path link")
            # relative URL
            anchor = None
            if "?" in url:
                url = url.split("?")[0]
            if "#" in url:
                url, anchor = url.split("#")

            if not url and anchor:
                if self.parent.check_anchors and self.parsed:
                    self.handle_anchor(self.parsed, anchor)
                return None

            url_path = unquote(url).replace("/", os.path.sep)
            dirpath = self.path.parent
            exists = False
            for ext in supported_extensions:
                rel_path = url_path.replace(".html", ext)
                target_path = dirpath.joinpath(rel_path)
                if target_path.exists():
                    exists = True
                    # only check anchors in html for now
                    if ext == ".html" and anchor and self.parent.check_anchors:
                        with target_path.open() as fd:
                            parsed = html5lib.parse(fd, namespaceHTMLElements=False)
                            return self.handle_anchor(parsed, anchor)
                    break
            if not exists:
                target_path = dirpath.joinpath(url_path)
                raise BrokenLinkError(url, "No such file: %s" % target_path)
            return None


def extensions_str(extensions: set[str]) -> str:
    """Get the extensions as a string."""
    if not extensions:
        return ""
    exts = ['"%s"' % e.lstrip(".") for e in extensions if e]
    if len(exts) == 1:
        return exts[0]
    return ", ".join(exts[:-1]) + " and %s" % exts[-1]


def validate_extensions(extensions: set[str]) -> None:
    """Validate the extensions."""
    invalid = set(extensions) - supported_extensions
    if invalid:
        warnings.warn(
            "Unsupported extensions for check-links: %s" % extensions_str(invalid), stacklevel=2
        )
