import argparse

import pytest

from pytest_check_links.args import StoreCacheAction, parse_status_codes, parse_timeout
from pytest_check_links.plugin import default_cache, purge_disallowed_cache


def test_parse_status_codes_accepts_lists_and_ranges():
    assert parse_status_codes("200, 301 400-402 500..501") == [
        200,
        301,
        400,
        401,
        402,
        500,
        501,
    ]


def test_parse_status_codes_rejects_invalid_codes():
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid HTTP status"):
        parse_status_codes("99")


def test_parse_timeout_rejects_non_positive_values():
    with pytest.raises(argparse.ArgumentTypeError, match="greater than 0"):
        parse_timeout("0")


def test_cache_allowable_codes_are_parsed():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-links-cache-allowable-codes", action=StoreCacheAction)

    namespace = parser.parse_args(["--check-links-cache-allowable-codes", "200, 301 400-402"])

    assert namespace.check_links_cache_kwargs["allowable_codes"] == [200, 301, 400, 401, 402]


def test_default_cache_allows_only_success_and_redirect_responses():
    assert default_cache["allowable_codes"] == list(range(200, 400))


def test_purge_disallowed_cache_removes_cached_responses_outside_allowlist():
    class CachedResponse:
        def __init__(self, status_code, cache_key):
            self.status_code = status_code
            self.cache_key = cache_key

    class Cache:
        def __init__(self):
            self.deleted = []

        def filter(self):
            return iter(
                [
                    CachedResponse(200, "ok"),
                    CachedResponse(302, "redirect"),
                    CachedResponse(404, "missing"),
                    CachedResponse(503, "unavailable"),
                ]
            )

        def delete(self, *keys):
            self.deleted.extend(keys)

    class Session:
        def __init__(self):
            self.cache = Cache()

    session = Session()

    purge_disallowed_cache(session, [200, 302])

    assert session.cache.deleted == ["missing", "unavailable"]
