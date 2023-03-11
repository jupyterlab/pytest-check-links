def test_anchors_local_self(pytester, anchor_args):
    pytester.copy_example("anchors_self.html")
    result = pytester.runpytest(*anchor_args)
    result.assert_outcomes(passed=2, failed=2)


def test_anchors_local_other(pytester, anchor_args):
    pytester.copy_example("anchors_self.html")
    pytester.copy_example("anchors_other.html")
    args = [*anchor_args, "anchors_other.html"]
    result = pytester.runpytest(*args)
    result.assert_outcomes(passed=1, failed=2)


def test_anchors_external(pytester, anchor_args):
    pytester.copy_example("anchors_remote.html")
    result = pytester.runpytest(*anchor_args)
    result.assert_outcomes(passed=1, failed=1)
