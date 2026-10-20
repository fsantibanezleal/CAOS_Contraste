"""``python -m pipeline.regulatory [--output-root DIR]`` from data-pipeline/ (the integrator wires data-pipeline/run.py to ``bake.bake``)."""
from __future__ import annotations

import sys

from .bake import main

if __name__ == "__main__":
    sys.exit(main())
