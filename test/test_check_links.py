import shutil

from .conftest import skip_pywin32


def test_ipynb(pytester):
    pytester.copy_example("linkcheck.ipynb")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=3, failed=4)
    result = pytester.runpytest_subprocess(
        "-v", "--check-links", "--check-links-ignore", "http.*example.com/.*"
    )
    result.assert_outcomes(passed=3, failed=3)


def test_markdown(pytester):
    pytester.copy_example("markdown.md")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=3)
    result = pytester.runpytest_subprocess(
        "-v", "--check-links", "--check-links-ignore", "http.*example.com/.*"
    )
    result.assert_outcomes(passed=7, failed=1)


def test_markdown_nested(pytester):
    pytester.copy_example("nested/nested.md")
    pytester.mkdir("nested")
    md = pytester.path / "nested.md"
    shutil.move(md, pytester.path / "nested" / "nested.md")
    pytester.copy_example("markdown.md")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=8, failed=3)
    result = pytester.runpytest_subprocess(
        "-v", "--check-links", "--check-links-ignore", "http.*example.com/.*"
    )
    result.assert_outcomes(passed=8, failed=1)


@skip_pywin32
def test_rst(pytester):
    pytester.copy_example("rst.rst")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=7, failed=2)


@skip_pywin32
def test_rst_nested(pytester):
    pytester.copy_example("nested/nested.rst")
    pytester.mkdir("nested")
    rst = pytester.path / "nested.rst"
    shutil.move(rst, pytester.path / "nested" / "nested.rst")
    pytester.copy_example("rst.rst")
    result = pytester.runpytest_subprocess("-v", "--check-links")
    result.assert_outcomes(passed=13, failed=5)


def test_link_ext(pytester):
    pytester.copy_example("linkcheck.ipynb")
    pytester.copy_example("rst.rst")
    pytester.copy_example("markdown.md")
    result = pytester.runpytest_subprocess("-v", "--check-links", "--links-ext=md,ipynb")
    result.assert_outcomes(passed=10, failed=7)
