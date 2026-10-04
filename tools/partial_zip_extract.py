"""Recover readable entries from a truncated ZIP (local headers only)."""

import argparse
import os
import struct
import sys
import zlib


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zip_file")
    parser.add_argument("out_dir")
    parser.add_argument("--max-files", type=int, default=500)
    args = parser.parse_args()

    data = open(args.zip_file, "rb").read()
    os.makedirs(args.out_dir, exist_ok=True)
    pos = 0
    saved = 0
    while saved < args.max_files:
        idx = data.find(b"PK\x03\x04", pos)
        if idx < 0:
            break
        if idx + 30 > len(data):
            break
        (
            _ver,
            _flags,
            method,
            _mtime,
            _mdate,
            crc,
            csize,
            usize,
            name_len,
            extra_len,
        ) = struct.unpack_from("<HHHHHIIIHH", data, idx + 4)
        name_start = idx + 30
        name_end = name_start + name_len
        if name_end > len(data):
            break
        name = data[name_start:name_end].decode("utf-8", errors="replace")
        if name.endswith("/"):
            pos = idx + 4
            continue
        payload_start = name_end + extra_len
        payload_end = payload_start + csize
        if payload_end > len(data):
            break
        payload = data[payload_start:payload_end]
        try:
            raw = payload if method == 0 else zlib.decompress(payload, -15)
            if len(raw) != usize:
                continue
        except zlib.error:
            pos = idx + 4
            continue
        out = os.path.join(args.out_dir, name.replace("\\", os.sep))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(raw)
        saved += 1
        print(f"saved {name} ({len(raw)} bytes)")
        pos = payload_end
    print(f"done, saved {saved} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
