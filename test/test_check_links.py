from pathlib import Path

from .conftest import skip_pywin32


def test_ipynb(testdir):
    testdir.copy_example('linkcheck.ipynb')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=3, failed=3)

def test_markdown(testdir):
    testdir.copy_example('markdown.md')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=8, failed=4)
    result = testdir.runpytest("-v", "--check-links", "--check-links-ignore", "http.*example.com/.*")
    result.assert_outcomes(passed=8, failed=1)

def test_markdown_nested(testdir):
    testdir.copy_example('nested/nested.md')
    testdir.mkdir('nested')
    md = testdir.tmpdir / 'nested.md'
    md.move(testdir.tmpdir / 'nested' / 'nested.md')
    testdir.copy_example('markdown.md')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=9, failed=4)
    result = testdir.runpytest("-v", "--check-links", "--check-links-ignore", "http.*example.com/.*")
    result.assert_outcomes(passed=9, failed=1)

@skip_pywin32
def test_rst(testdir):
    testdir.copy_example('rst.rst')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=2)

@skip_pywin32
def test_rst_nested(testdir):
    testdir.copy_example('nested/nested.rst')
    testdir.mkdir('nested')
    rst = testdir.tmpdir / 'nested.rst'
    rst.move(testdir.tmpdir / 'nested' / 'nested.rst')
    testdir.copy_example('rst.rst')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=13, failed=5)

def test_link_ext(testdir):
    testdir.copy_example('linkcheck.ipynb')
    testdir.copy_example('rst.rst')
    testdir.copy_example('markdown.md')
    result = testdir.runpytest("-v", "--check-links", "--links-ext=md,ipynb")
    result.assert_outcomes(passed=11, failed=7)
