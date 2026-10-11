#!/usr/bin/env python3
"""Fetch sources into the device data root and record the licence manifest. Invoked BY PATH, never installed."""
import sys

from pipeline.io.fetch import main

if __name__ == "__main__":
    sys.exit(main())
