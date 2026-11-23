"""Entrypoint for python -m parity_guard."""

import sys
from parity_guard.cli import main

if __name__ == "__main__":
    sys.exit(main())
