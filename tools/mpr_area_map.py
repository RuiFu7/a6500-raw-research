"""Extract the MPR area/buffer label table from libmpr.so."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_file(root: Path) -> Path:
    candidates = sorted(root.rglob("libmpr.so"))
    preferred = [p for p in candidates if "ilce6500-v106" in p.as_posix().lower()]
    if preferred:
        return preferred[0]
    if not candidates:
        raise FileNotFoundError("libmpr.so")
    return candidates[0]


def read_string(data: bytes, address: int) -> str:
    if address < 0 or address >= len(data):
        return ""
    end = data.find(b"\0", address)
    if end < 0:
        return ""
    return data[address:end].decode("ascii", "replace").rstrip()


def extract_map(data: bytes) -> list[dict[str, str | int]]:
    marker = b"Still Stream RAW Main"
    marker_offset = data.find(marker)
    if marker_offset < 0:
        return []

    pointer = marker_offset.to_bytes(4, "little")
    pointer_at = data.find(pointer)
    if pointer_at < 0:
        return []

    entry_start = pointer_at - 4
    marker_id = int.from_bytes(data[entry_start:pointer_at], "little")
    scan = entry_start
    base = entry_start - marker_id * 8
    while scan >= 8:
        scan -= 8
        if int.from_bytes(data[scan:scan + 4], "little") == 0xffffffff:
            base = scan + 8
            break

    rows: list[dict[str, str | int]] = []
    for index in range(0, 0x500, 8):
        offset = base + index
        if offset + 8 > len(data):
            break
        area_id = int.from_bytes(data[offset:offset + 4], "little")
        label_addr = int.from_bytes(data[offset + 4:offset + 8], "little")
        if area_id == 0xffffffff or label_addr == 0:
            break
        label = read_string(data, label_addr)
        if not label:
            break
        rows.append(
            {
                "id": area_id,
                "label": label,
                "label_address": hex(label_addr),
                "table_entry_address": hex(base + index),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    path = args.input if args.input.exists() else find_file(args.input)
    data = path.read_bytes()
    rows = extract_map(data)
    if not rows:
        print("No MPR area table found", file=sys.stderr)
        return 1

    for row in rows:
        print(f"{row['id']:#x}\t{row['label']}")

    if args.json:
        args.json.write_text(
            json.dumps({"input": str(path), "rows": rows}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
