"""Scan a Sony updater/dump for known firmware signatures and PE sections."""

import argparse
import struct
import sys

DAT_MAGIC = b"\x89UFU\r\n\x1a\n"
SIGNATURES = {
    "DAT": DAT_MAGIC,
    "ZIP": b"PK\x03\x04",
    "ZIP_EMPTY": b"PK\x05\x06",
    "LZH": b"-lh0-",
    "GZIP": b"\x1f\x8b",
    "TAR_U": b"ustar",
    "EXT2": b"\x53\xef",
}


def pe_sections(data):
    if data[:2] != b"MZ":
        return []
    pe_off = struct.unpack_from("<I", data, 0x3C)[0]
    if data[pe_off:pe_off + 4] != b"PE\0\0":
        return []
    num_sections = struct.unpack_from("<H", data, pe_off + 6)[0]
    opt_size = struct.unpack_from("<H", data, pe_off + 20)[0]
    first = pe_off + 24 + opt_size
    out = []
    for i in range(num_sections):
        off = first + i * 40
        name = data[off:off + 8].rstrip(b"\0").decode("ascii", "replace")
        vsize, vaddr, raw_size, raw_off = struct.unpack_from("<IIII", data, off + 8)
        out.append((name, raw_off, raw_size, vaddr, vsize))
    return out


def find_all(haystack, needle, limit=20):
    pos = 0
    found = []
    while True:
        idx = haystack.find(needle, pos)
        if idx < 0:
            break
        found.append(idx)
        if len(found) >= limit:
            break
        pos = idx + 1
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    args = parser.parse_args()

    with open(args.input, "rb") as f:
        data = f.read()
    print(f"size={len(data)}")
    for name, offset, size, vaddr, vsize in pe_sections(data):
        print(f"section {name!r} raw_off=0x{offset:x} raw_size=0x{size:x} "
              f"vaddr=0x{vaddr:x} vsize=0x{vsize:x}")

    for label, needle in SIGNATURES.items():
        hits = find_all(data, needle)
        if hits:
            print(f"{label}: {', '.join(f'0x{x:x}' for x in hits)}")
    print(f"tail64: {data[-64:].hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
