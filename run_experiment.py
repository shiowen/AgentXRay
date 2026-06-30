#!/usr/bin/env python3
"""Canonical command-line entry point for AgentXRay experiments."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deagent.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
