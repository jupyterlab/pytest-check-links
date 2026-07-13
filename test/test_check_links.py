import shutil
from types import SimpleNamespace

import pytest
from requests import Response
from requests.exceptions import Timeout

from pytest_check_links.plugin import BrokenLinkError, LinkItem

from .conftest import skip_pywin32


class FakeSession:
    def __init__(self, response=None, error=None):
        self.headers = {}
        self.calls = []
        self.error = error
        self.response = response

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return self.response


def make_response(status_code, reason):
    response = Response()
    response.status_code = status_code
    response.reason = reason
    response.headers = {}
    return response


def make_link_item(
    session,
    request_timeout=None,
    transient_status_codes=None,
    transient_result="fail",
):
    item = SimpleNamespace(
        parent=SimpleNamespace(requests_session=session),
        config=SimpleNamespace(
            option=SimpleNamespace(
                check_links_request_timeout=request_timeout,
                check_links_transient_status_codes=transient_status_codes,
                check_links_transient_result=transient_result,
            )
        ),
        uncached=[],
        sleep=lambda headers: False,
    )

    def uncache_url(url):
        item.uncached.append(url)
        return True

    def handle_transient_failure(url, error):
        return LinkItem.handle_transient_failure(item, url, error)

    item.uncache_url = uncache_url
    item.handle_transient_failure = handle_transient_failure
    return item


def test_fetch_with_retries_passes_configured_timeout():
    session = FakeSession(response=make_response(200, "OK"))
    item = make_link_item(session, request_timeout=7)

    response = LinkItem.fetch_with_retries(item, "https://example.test/path#anchor")

    assert response.status_code == 200
    assert session.calls == [("https://example.test/path", {"timeout": 7})]


def test_fetch_with_retries_preserves_unconfigured_timeout_failure():
    session = FakeSession(error=Timeout("read timed out"))
    item = make_link_item(session)

    with pytest.raises(BrokenLinkError, match="read timed out"):
        LinkItem.fetch_with_retries(item, "https://example.test")


def test_fetch_with_retries_can_skip_configured_timeout_failure():
    session = FakeSession(error=Timeout("read timed out"))
    item = make_link_item(session, request_timeout=7, transient_result="skip")

    with pytest.raises(pytest.skip.Exception, match="transient link check failure"):
        LinkItem.fetch_with_retries(item, "https://example.test")


def test_fetch_with_retries_uncaches_and_skips_transient_status():
    session = FakeSession(response=make_response(503, "Service Unavailable"))
    session.cache = object()
    session.settings = SimpleNamespace(allowable_codes=[200, 301])
    item = make_link_item(session, transient_status_codes=[503], transient_result="skip")

    with pytest.raises(pytest.skip.Exception, match="503: Service Unavailable"):
        LinkItem.fetch_with_retries(item, "https://example.test")

    assert item.uncached == ["https://example.test"]


def test_ipynb(pytester):
    pytester.copy_example("linkcheck.ipynb")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=3, failed=4)
    result = pytester.runpytest_subprocess(
        "-v", "--check-links", "--check-links-ignore", "http.*example.com/.*"
    )
    result.assert_outcomes(passed=3, failed=3)


def test_markdown(pytester):
    pytester.copy_example("markdown.md")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=3)
    result = pytester.runpytest_subprocess(
        "-v", "--check-links", "--check-links-ignore", "http.*example.com/.*"
    )
    result.assert_outcomes(passed=7, failed=1)


def test_markdown_nested(pytester):
    pytester.copy_example("nested/nested.md")
    pytester.mkdir("nested")
    md = pytester.path / "nested.md"
    shutil.move(md, pytester.path / "nested" / "nested.md")
    pytester.copy_example("markdown.md")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=8, failed=3)
    result = pytester.runpytest_subprocess(
        "-v", "--check-links", "--check-links-ignore", "http.*example.com/.*"
    )
    result.assert_outcomes(passed=8, failed=1)


@skip_pywin32
def test_rst(pytester):
    pytester.copy_example("rst.rst")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=2)


@skip_pywin32
def test_rst_nested(pytester):
    pytester.copy_example("nested/nested.rst")
    pytester.mkdir("nested")
    rst = pytester.path / "nested.rst"
    shutil.move(rst, pytester.path / "nested" / "nested.rst")
    pytester.copy_example("rst.rst")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=13, failed=5)


def test_link_ext(pytester):
    pytester.copy_example("linkcheck.ipynb")
    pytester.copy_example("rst.rst")
    pytester.copy_example("markdown.md")
    result = pytester.runpytest_subprocess("-v", "--check-links", "--links-ext=md,ipynb")
    result.assert_outcomes(passed=10, failed=7)
