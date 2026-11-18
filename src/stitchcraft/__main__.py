"""Allow `python -m stitchcraft` when the package is installed or src/ is on PYTHONPATH."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
