"""Harness gate CLI entrypoint."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lacerta.harness.gate",
        description="Lacerta harness gate (scenarios land in L1).",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default=None,
        help="Scenario name (unused until L1)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        help="Number of runs (unused until L1)",
    )
    parser.parse_args(argv)
    print("L0: gate not implemented; scenarios land in L1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
