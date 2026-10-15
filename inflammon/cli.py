"""Command line for the weekly refresh."""

from __future__ import annotations

import argparse
import json

from inflammon.pipeline import refresh


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="inflammon",
        description="Inflammation Signal Monitor. Refreshes public data and writes the JSON snapshot.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    refresh_parser = sub.add_parser("refresh", help="Pull public sources and rebuild the snapshot")
    refresh_parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the HTTP cache and call the source APIs again",
    )
    args = parser.parse_args(argv)
    if args.command == "refresh":
        summary = refresh(force=args.force)
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
