import subprocess
import pytest


def test_cli_meta():
    assert subprocess.call(["pytest-check-links", "--version"]) == 0
    assert subprocess.call(["pytest-check-links", "--help"]) == 0


@pytest.mark.parametrize("example,rc,expected,unexpected", [
    ["httpbin.md", 0, [" 6 passed"], [" failed"]],
    ["rst.rst", 1, [" 2 failed", " 7 passed"], [" warning"]]
])
def test_cli_pass(testdir, example, rc, expected, unexpected):
    testdir.copy_example(example)
    testdir.copy_example("setup.cfg")
    proc = subprocess.Popen(["pytest-check-links"], stdout=subprocess.PIPE, shell=True)
    stdout, _ = proc.communicate()
    output = stdout.decode('utf-8').strip().splitlines()
    assert rc == proc.returncode
    assert output
    summary = output[-1]
    for ex in expected:
        assert ex in summary, stdout.decode('utf-8')
    for unex in unexpected:
        assert unex not in summary, stdout.decode('utf-8')
