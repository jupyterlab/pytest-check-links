import sys
import time

import pytest
from pytest_httpserver import HTTPServer

pytest_plugins = ["pytester"]

skip_pywin32 = pytest.mark.skipif(sys.platform == "win32", reason="pywin32 double import")


@pytest.fixture(scope="module")
def local_server():
    """Provide a local HTTP server for reliable testing without external dependencies."""
    server = HTTPServer(host="127.0.0.1", port=0)  # port=0 picks available port
    server.expect_request("/delay").respond_with_handler(_delay_handler)
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


def _delay_handler(request):
    """Simulate httpbin.org/delay endpoint with small delay."""
    time.sleep(0.05)  # Small delay to simulate network latency
    return '{"status": "ok"}'


@pytest.fixture
def local_links_md(pytester, local_server):
    """Create a markdown file with links to local server (replaces httpbin.md)."""
    base_url = f"http://{local_server.host}:{local_server.port}"
    content = "\n".join([
        f"- [one]({base_url}/delay#1)",
        f"- [two]({base_url}/delay#2)",
        f"- [three]({base_url}/delay#3)",
        f"- [four]({base_url}/delay#4)",
        f"- [five]({base_url}/delay#5)",
        f"- [six]({base_url}/delay#6)",
    ])
    pytester.makefile(".md", local_links=content)
    return "local_links.md"


@pytest.fixture
def anchor_args():
    return ["-v", "--check-links", "--check-anchors"]


@pytest.fixture
def base_args():
    return ["-v", "--check-links", "--check-links-cache"]


@pytest.fixture
def memory_args(base_args):
    return [*base_args, "--check-links-cache-backend", "memory"]
