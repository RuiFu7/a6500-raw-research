"""Build a reproducible module index (CSV + JSON) for unpacked firmware."""

import argparse
import csv
import hashlib
import json
import os
import sys


MAGIC_HINTS = [
    (b"\x7fELF", "ELF"),
    (b"MZ", "PE"),
    (b"\x89UFU\r\n\x1a\n", "Sony DAT"),
    (b"PK\x03\x04", "ZIP"),
    (b"\x1f\x8b", "GZIP"),
    (b"\x1f\x8b\x08", "GZIP"),
    (b"ustar", "TAR"),
    (b"\x53\xef", "EXT2"),
    (b"hsqs", "SQUASHFS"),
    (b"\x28\xcd\x3d\x45", "CRAMFS"),
]


def sniff(path: str) -> str:
    with open(path, "rb") as f:
        head = f.read(16)
    for magic, name in MAGIC_HINTS:
        if head.startswith(magic):
            return name
    return "raw"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    parser.add_argument("out_prefix")
    args = parser.parse_args()

    rows = []
    root = os.path.abspath(args.root)
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            size = os.path.getsize(path)
            rows.append(
                {
                    "path": rel.replace(os.sep, "/"),
                    "size": size,
                    "magic": sniff(path),
                    "sha256": sha256(path),
                }
            )
    rows.sort(key=lambda r: r["path"])

    csv_path = args.out_prefix + ".csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "size", "magic", "sha256"])
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.out_prefix + ".json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"root": root, "count": len(rows), "files": rows}, f, indent=1)

    print(f"indexed {len(rows)} files -> {csv_path}, {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
