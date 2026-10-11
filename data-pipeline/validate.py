#!/usr/bin/env python3
"""Validate your own scored sample offline: contract 1 and the battery. Invoked BY PATH, never installed."""
import sys

from pipeline.own_sample import main

if __name__ == "__main__":
    sys.exit(main())
