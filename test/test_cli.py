import os
import subprocess

import pytest
from flaky import flaky


def run(cmd, rc=0):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603
    stdout, stderr = proc.communicate()
    output = stdout.decode("utf-8").strip().splitlines()
    err = stderr.decode("utf-8").strip().splitlines()
    assert rc == proc.returncode
    return output, err


def test_cli_version():
    run(["pytest-check-links", "--version"])


def test_cli_help():
    run(["pytest-check-links", "--help"])


@flaky
@pytest.mark.skipif(os.name != "nt", reason="Only works on Windows")
@pytest.mark.parametrize(
    "example,rc,expected,unexpected",
    [
        ("httpbin.md", 0, [" 6 passed"], [" failed"]),
        ("rst.rst", 1, [" 2 failed", " 7 passed"], [" warning"]),
    ],
)
def test_cli_pass(testdir, example, rc, expected, unexpected):
    testdir.copy_example(example)
    testdir.copy_example("setup.cfg")
    output, _ = run(["pytest-check-links"], rc)
    assert output
    summary = output[-1]
    for ex in expected:
        assert ex in summary, output
    for unex in unexpected:
        assert unex not in summary, output
