"""Entry point for `python -m pr_vetting`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
