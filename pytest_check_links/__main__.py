"""
This script will run pytest with our plugin enabled,
and with the normal python plugin disabled. This means collection
of normal tests will be disabled, unless other plugins are set
to collect further tests. If that is the case, you can disable
these plugins with the py.test command line option
"-p no:<plugin-name-here>".
"""
# pragma: no cover

import sys


def main(args=None):
    import pytest

    if args is None:
        args = sys.argv[1:]

    return pytest.main(args + [
        '--check-links',
    ], [
        'no:python',
    ])


if __name__ == '__main__':
    sys.exit(main())
