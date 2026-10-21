"""``python -m pipeline.governance [--output-root DIR]`` from data-pipeline/ (the integrator wires the stage in pipeline.py)."""
from __future__ import annotations

import sys

from .bake import main

if __name__ == "__main__":
    sys.exit(main())
