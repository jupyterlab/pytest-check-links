from . import examples


def test_ipynb(testdir):
    testdir.copy_example('linkcheck.ipynb')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=3, failed=3)

def test_markdown(testdir):
    testdir.copy_example('markdown.md')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=8, failed=4)

def test_rst(testdir):
    testdir.copy_example('rst.rst')
    result = testdir.runpytest("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=2)

def test_link_ext(testdir):
    testdir.copy_example('linkcheck.ipynb')
    testdir.copy_example('rst.rst')
    testdir.copy_example('markdown.md')
    result = testdir.runpytest("-v", "--check-links", "--links-ext=.md,rst")
    result.assert_outcomes(passed=15, failed=6)

def test_anchors_self(testdir):
    testdir.copy_example('anchors_self.html')
    result = testdir.runpytest("-v", "--check-links", "--check-anchors")
    result.assert_outcomes(passed=1, failed=2)

def test_anchors_other(testdir):
    testdir.copy_example('anchors_self.html')
    testdir.copy_example('anchors_other.html')
    result = testdir.runpytest("-v", "--check-links", "--check-anchors", "anchors_other.html")
    result.assert_outcomes(passed=1, failed=2)
