#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Single entry point for the rein-analyzing-requirements scripts.

Run `python3 scripts/req.py --help` for the command list.

Keep this file parseable by very old Pythons (no f-strings, no annotations):
it must reach the version check below and print a clear message instead of
dying with a SyntaxError. All real code lives in the reqlib package.
"""
import os
import sys

if sys.version_info < (3, 9):
    sys.stderr.write(
        "req.py needs Python 3.9 or newer, but this is Python %d.%d.\n"
        "Install Python 3.9+, or install uv and run: uv run scripts/req.py ...\n"
        % tuple(sys.version_info[:2])
    )
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reqlib.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
