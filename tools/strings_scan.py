"""Extract printable strings from binaries and filter by keywords."""

import argparse
import re
import sys


def extract(data: bytes, min_len: int = 6):
    pattern = re.compile(rb"[\x20-\x7e]{%d,}" % min_len)
    for match in pattern.finditer(data):
        yield match.start(), match.group().decode("ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+")
    parser.add_argument("--min-len", type=int, default=6)
    parser.add_argument("--keywords", default="")
    parser.add_argument("--max-per-file", type=int, default=5000)
    parser.add_argument("--output", default="", help="write results to a UTF-8 file")
    args = parser.parse_args()

    keywords = [k.lower() for k in args.keywords.split(",") if k]
    out = open(args.output, "w", encoding="utf-8") if args.output else None
    for path in args.inputs:
        with open(path, "rb") as f:
            data = f.read()
        count = 0
        for offset, text in extract(data, args.min_len):
            if keywords and not any(k in text.lower() for k in keywords):
                continue
            line = f"{path}:0x{offset:x}: {text}"
            if out:
                out.write(line + "\n")
            else:
                print(line)
            count += 1
            if count >= args.max_per_file:
                line = f"{path}: ... truncated"
                if out:
                    out.write(line + "\n")
                else:
                    print(line)
                break
    if out:
        out.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
