"""
This script will run pytest with our plugin enabled,
and with the normal python plugin disabled. This means collection
of normal tests will be disabled, unless other plugins are set
to collect further tests. If that is the case, you can disable
these plugins with the py.test command line option
"-p no:<plugin-name-here>".
"""
# pragma: no cover

import subprocess
import sys


def main(args=None):

    if args is None:
        args = sys.argv[1:]

    return subprocess.call(
        [sys.executable, "-m", "pytest", "--check-links", "-p", "no:python"] + args
    )


if __name__ == "__main__":
    sys.exit(main())
