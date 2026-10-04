#!/usr/bin/env python3
"""Disassemble selected Thumb ranges from a base-zero av-cam.bin."""
from __future__ import annotations
import argparse
from pathlib import Path
import capstone

def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("--range", action="append", required=True, metavar="START:END")
    args=p.parse_args()
    data=args.input.read_bytes()
    md=capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB)
    for spec in args.range:
        start_s,end_s=spec.split(":",1)
        start=int(start_s,0); end=int(end_s,0)
        print(f"=== RANGE 0x{start:08x}-0x{end:08x} ===")
        for ins in md.disasm(data[start:end],start):
            print(f"{ins.address:08x} {ins.mnemonic:<8} {ins.op_str}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())