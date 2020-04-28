import os
import time
import shutil

from glob import glob

import pytest

from . import examples


@pytest.fixture
def base_args():
    return ["-v", "--check-links", "--check-links-cache"]


def assert_sqlite(testdir, name=".pytest-check-links-cache.sqlite", exists=True):
    caches = list(glob(os.path.join(testdir.tmpdir, name)))
    if exists:
        assert caches
    else:
        assert not caches


def test_cache_expiry(testdir, base_args):
    """will the default sqlite3 backend persist and then expire?
    """
    testdir.copy_example('linkcheck.ipynb')

    args = [*base_args, "--check-links-cache-expire-after", "2"]
    expected = dict(passed=3, failed=3)
    t0 = time.time()
    result = testdir.runpytest(*args)
    t1 = time.time()
    result.assert_outcomes(**expected)

    assert_sqlite(testdir)

    t2 = time.time()
    result = testdir.runpytest(*args)
    t3 = time.time()
    result.assert_outcomes(**expected)

    assert t1 - t0 > t3 - t2, "cache did not make second run faster"

    time.sleep(2)

    t4 = time.time()
    result = testdir.runpytest(*args)
    t5 = time.time()
    result.assert_outcomes(**expected)

    assert t5 - t4 > t3 - t2, "cache did not expire"



def test_cache_memory(testdir, base_args):
    """will the memory backend cache links inside a run?
    """
    args = [*base_args, "--check-links-cache-backend", "memory"]
    expected = dict(passed=3, failed=0)

    testdir.copy_example('httpbin.md')

    def run(passed):
        t0 = time.time()
        result = testdir.runpytest(*args)
        t1 = time.time()
        result.assert_outcomes(passed=passed, failed=0)
        assert_sqlite(testdir, exists=False)
        return t1 - t0

    d0 = run(6)

    for i in range(5):
        shutil.copy(
            os.path.join(testdir.tmpdir, "httpbin.md"),
            os.path.join(testdir.tmpdir, "httpbin{}.md".format(i))
        )

    d1 = run(36)
    # allow a healthy savings margin for network flake
    assert d1 < d0 * 4
