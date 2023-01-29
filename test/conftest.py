import sys

import pytest

pytest_plugins = ["pytester"]

skip_pywin32 = pytest.mark.skipif(sys.platform == "win32", reason="pywin32 double import")


@pytest.fixture
def anchor_args():
    return ["-v", "--check-links", "--check-anchors"]


@pytest.fixture
def base_args():
    return ["-v", "--check-links", "--check-links-cache"]


@pytest.fixture
def memory_args(base_args):
    return [*base_args, "--check-links-cache-backend", "memory"]
