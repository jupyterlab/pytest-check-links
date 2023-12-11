"""
This script will run pytest with our plugin enabled,
and with the normal python plugin disabled. This means collection
of normal tests will be disabled, unless other plugins are set
to collect further tests. If that is the case, you can disable
these plugins with the py.test command line option
"-p no:<plugin-name-here>".
"""
# pragma: no cover
from __future__ import annotations

import subprocess
import sys


def main(args: list[str] | None = None) -> int:
    """Main function."""
    if args is None:
        args = sys.argv[1:]

    return subprocess.call(
        [sys.executable, "-m", "pytest", "--check-links", "-p", "no:python", *args]  # noqa: S603
    )


if __name__ == "__main__":
    sys.exit(main())
