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

@skip_pywin32
def test_rst(testdir):
    testdir.copy_example('rst.rst')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=2)

def test_link_ext(testdir):
    testdir.copy_example('linkcheck.ipynb')
    testdir.copy_example('rst.rst')
    testdir.copy_example('markdown.md')
    result = testdir.runpytest("-v", "--check-links", "--links-ext=md,ipynb")
    result.assert_outcomes(passed=11, failed=7)
