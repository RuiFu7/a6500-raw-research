"""Extract Sony updater .exe / .dat and unpack with fwtool.py."""

import argparse
import os
import subprocess
import sys

DAT_MAGIC = b"\x89UFU\r\n\x1a\n"


def find_dat_offset(data: bytes) -> int:
    return data.find(DAT_MAGIC)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="updater .exe or FirmwareData .dat")
    parser.add_argument("out_dir")
    parser.add_argument(
        "--fwtool",
        default=None,
        help="path to fwtool.py (default: tools/vendor/fwtool.py/fwtool.py)",
    )
    args = parser.parse_args()

    data = open(args.input, "rb").read(64)
    offset = find_dat_offset(data)
    if offset is None and not data.startswith(DAT_MAGIC):
        # Look deeper; DAT can be embedded after PE overlay.
        with open(args.input, "rb") as f:
            head = f.read(16 * 1024 * 1024)
        offset = head.find(DAT_MAGIC)
    if offset is None:
        print("no Sony DAT signature found", file=sys.stderr)
        return 1

    os.makedirs(args.out_dir, exist_ok=True)
    dat_path = os.path.join(args.out_dir, "FirmwareData.dat")
    if offset == 0:
        src = args.input
    else:
        with open(args.input, "rb") as f:
            f.seek(offset)
            with open(dat_path, "wb") as out:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        src = dat_path
        print(f"embedded DAT at offset 0x{offset:x} -> {dat_path}")

    fwtool = args.fwtool or os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "vendor",
        "fwtool.py",
        "fwtool.py",
    )
    cmd = [sys.executable, fwtool, "unpack", "-f", src, "-o", args.out_dir]
    print("running:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
