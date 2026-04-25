"""Allow running cctools as ``python -m cctools``."""

from cctools.cli import main

raise SystemExit(main())
