"""Extract candidate links from a downloaded HTML search/result page."""

import argparse
import html
import re
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="HTML file to parse")
    parser.add_argument(
        "--filter",
        default="",
        help="comma-separated substrings; print only links whose text matches",
    )
    args = parser.parse_args()

    text = open(args.input, encoding="utf-8", errors="replace").read()
    filters = [f.lower() for f in args.filter.split(",") if f]
    pattern = re.compile(r'<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.S)
    seen = set()
    for url, label in pattern.findall(text):
        label = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
        if not label:
            continue
        if filters and not any(f in label.lower() for f in filters):
            continue
        if "bing.com" in url or url in seen:
            continue
        seen.add(url)
        print(f"{url}\t{label[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
