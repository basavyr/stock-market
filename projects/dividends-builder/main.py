"""Backward-compatible entrypoint.

The public site should not ship any portfolio data.

Run this file (or `generate.py`) to create/update a local-only `export.json`
that you then upload in the UI.
"""

from generate import main


if __name__ == "__main__":
    main()
