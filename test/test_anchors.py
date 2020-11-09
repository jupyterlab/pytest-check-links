import pytest


def test_anchors_local_self(testdir, anchor_args):
    testdir.copy_example('anchors_self.html')
    result = testdir.runpytest(*anchor_args)
    result.assert_outcomes(passed=2, failed=2)


def test_anchors_local_other(testdir, anchor_args):
    testdir.copy_example('anchors_self.html')
    testdir.copy_example('anchors_other.html')
    args = anchor_args + ["anchors_other.html"]
    result = testdir.runpytest(*args)
    result.assert_outcomes(passed=1, failed=2)


def test_anchors_external(testdir, anchor_args):
    testdir.copy_example('anchors_remote.html')
    result = testdir.runpytest(*anchor_args)
    result.assert_outcomes(passed=1, failed=1)
