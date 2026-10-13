"""Run the bundled SpecViz helper without installation or third-party packages."""

import sys

if sys.version_info < (3, 11):
    raise SystemExit("SpecViz requires Python 3.11 or later; install it and retry.")

from specviz.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
