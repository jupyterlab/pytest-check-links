import os
import shutil
import sys
import time
from glob import glob

import pytest
import requests_cache
from flaky import flaky


def assert_sqlite(pytester, name=None, tmpdir=None, exists=True):
    name = name or ".pytest-check-links-cache.sqlite"
    tmpdir = str(tmpdir or pytester.path)
    caches = list(glob(os.path.join(tmpdir, name)))
    if exists:
        assert caches
    else:
        assert not caches


@flaky
@pytest.mark.skipif(sys.implementation.name.lower() == "pypy", reason="Does not work on pypy")
@pytest.mark.parametrize("cache_name", [None, "custom-cache"])
def test_cache_expiry(pytester, base_args, cache_name, tmpdir):
    """will the default sqlite3 backend persist and then expire?"""
    pytester.copy_example("linkcheck.ipynb")

    args = [*base_args, "--check-links-cache-expire-after", "2"]
    if cache_name:
        args += ["--check-links-cache-name", os.path.join(str(tmpdir), cache_name)]
    expected = {"passed": 3, "failed": 4}
    t0 = time.time()
    result = pytester.runpytest_subprocess(*args)
    t1 = time.time()
    result.assert_outcomes(**expected)

    if cache_name:
        assert_sqlite(pytester, name=f"{cache_name}.sqlite", tmpdir=tmpdir)
    else:
        assert_sqlite(pytester)

    t2 = time.time()
    result = pytester.runpytest_subprocess(*args)
    t3 = time.time()
    result.assert_outcomes(**expected)

    d0 = t1 - t0
    d1 = t3 - t2

    assert d0 > d1, "cache did not make second run faster"

    time.sleep(2)

    t4 = time.time()
    result = pytester.runpytest_subprocess(*args)
    t5 = time.time()
    result.assert_outcomes(**expected)

    d2 = t5 - t4
    d3 = t3 - t2

    assert d2 > d3, "cache did not expire"


@flaky
def test_cache_memory(pytester, memory_args):
    """will the memory backend cache links inside a run?"""
    expected = dict(passed=3, failed=0)

    pytester.copy_example("httpbin.md")

    def run(passed):
        t0 = time.time()
        result = pytester.runpytest_subprocess(*memory_args)
        t1 = time.time()
        result.assert_outcomes(passed=passed, failed=0)
        assert_sqlite(pytester, exists=False)
        return t1 - t0

    d0 = run(6)

    for i in range(5):
        shutil.copy(
            os.path.join(str(pytester.path), "httpbin.md"),
            os.path.join(str(pytester.path), f"httpbin{i}.md"),
        )

    d1 = run(36)
    # allow a healthy savings margin for network flake
    assert d1 < d0 * 4


@flaky
def test_cache_retry(pytester, memory_args):
    """will a Retry-After header work with cache?"""

    pytester.copy_example("httpbin.md")

    attempts: list = []

    _get = requests_cache.CachedSession.get

    def mock_get(*args, **kwargs):
        response = _get(*args, **kwargs)
        if len(attempts) < 5:
            response.status_code = 502
            response.headers["Retry-After"] = "0"
        attempts.append([args, kwargs])
        return response

    requests_cache.CachedSession.get = mock_get

    result = pytester.runpytest_inprocess(*memory_args)

    try:
        result.assert_outcomes(passed=5, failed=1)
        assert len(attempts) == 10
    finally:
        requests_cache.CachedSession.get = _get


@flaky
def test_cache_backend_opts(pytester, base_args):
    pytester.copy_example("httpbin.md")
    args = [
        *base_args,
        "--check-links-cache-backend-opt",
        "fast_save:true",
        "--check-links-cache-name",
        "foo",
    ]
    result = pytester.runpytest_subprocess(*args)
    result.assert_outcomes(passed=6, failed=0)
    assert_sqlite(pytester, name="foo.sqlite")
