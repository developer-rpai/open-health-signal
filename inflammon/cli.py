"""Command line for the weekly refresh and the newsletter."""

from __future__ import annotations

import argparse
import json
import os
import sys

from inflammon.newsletter.publish import NewsletterSendError, build_and_save
from inflammon.pipeline import refresh


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="inflammon",
        description="Inflammation Signal Monitor. Refreshes public data and writes the weekly newsletter.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    refresh_parser = sub.add_parser("refresh", help="Pull public sources and rebuild the snapshot")
    refresh_parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore the HTTP cache and call the source APIs again",
    )

    newsletter = sub.add_parser(
        "newsletter",
        help="Build the weekly issue from the snapshot. Dry-run unless --send or NEWSLETTER_SEND=1",
    )
    newsletter.add_argument("--snapshot", default="data/snapshot")
    newsletter.add_argument("--out", default="data/newsletter")
    newsletter.add_argument("--web-data", default="web/data/newsletter")
    newsletter.add_argument("--web-email", default="web/public/newsletter/email")
    newsletter.add_argument("--site-url", default=None, help="Absolute dashboard URL used in the email")
    newsletter.add_argument("--send", action="store_true", help="Send through the provider API")
    newsletter.add_argument("--dry-run", action="store_true", help="Archive the issue and do not send")

    args = parser.parse_args(argv)
    if args.command == "refresh":
        summary = refresh(force=args.force)
        print(json.dumps(summary, indent=2))
        return
    if args.command == "newsletter":
        try:
            summary = build_and_save(
                snapshot_dir=args.snapshot,
                out_dir=args.out,
                web_data_dir=args.web_data,
                web_email_dir=args.web_email,
                site_url=args.site_url,
                send=_want_send(args),
            )
        except NewsletterSendError as exc:
            print(str(exc), file=sys.stderr)
            raise SystemExit(1) from exc
        print(json.dumps(summary, indent=2))


def _want_send(args: argparse.Namespace) -> bool:
    if args.dry_run:
        return False
    if args.send:
        return True
    return os.environ.get("NEWSLETTER_SEND", "").strip().lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    main()
