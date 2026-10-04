#!/usr/bin/env python3
"""Find the (row width, header offset) that makes an 8/16-bit dump smoothest
within rows. A real frame buffer has a sharp minimum; metadata/header regions
do not. Also reports the 2x2 Bayer phase spread at the best layout.
"""

import argparse
import sys

import numpy as np


def row_diff_cost(a2d: np.ndarray):
    """Mean |pixel - right neighbor| across a (rows, cols) uint array."""
    if a2d.shape[1] < 2:
        return None
    d = np.abs(a2d[:, :-1].astype(np.int32) - a2d[:, 1:].astype(np.int32))
    return float(d.mean())


def scan(data: np.ndarray, min_w, max_w, step, offsets, rows):
    best = []
    for off in offsets:
        if off >= len(data):
            continue
        sub = data[off:]
        if len(sub) // 2 < rows * (min_w // 2):
            continue
        for w in range(min_w, max_w + 1, step):
            n = rows * w
            if n > len(sub):
                n = len(sub) // w * w
                if n < w * 4:
                    continue
            a = sub[:n].reshape(-1, w)
            c = row_diff_cost(a)
            if c is not None:
                best.append((c, off, w))
    best.sort()
    return best


def dedup(cands, tol=0.06):
    out = []
    for c, off, w in cands:
        if any(abs(w - old) < tol * old for _, _, old in out):
            continue
        out.append((c, off, w))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--bits", type=int, choices=[8, 16], default=8)
    p.add_argument("--min-w", type=int, default=128)
    p.add_argument("--max-w", type=int, default=6144)
    p.add_argument("--step", type=int, default=8)
    p.add_argument("--rows", type=int, default=48)
    p.add_argument("--offsets", type=str, default="0,8,16,24,32,48,64,96,128")
    p.add_argument("--top", type=int, default=10)
    args = p.parse_args()

    raw = open(args.input, "rb").read()
    offsets = [int(x) for x in args.offsets.split(",") if x.strip() != ""]
    if args.bits == 16:
        data = np.frombuffer(raw[: len(raw) // 2 * 2], dtype="<u2")
        px = args.min_w // 2
        cands = scan(data, px, args.max_w // 2, max(1, args.step // 2), offsets, args.rows)
        # report byte row width
        cands = [(c, off * 2, w * 2) for c, off, w in cands]
    else:
        data = np.frombuffer(raw, dtype=np.uint8)
        cands = scan(data, args.min_w, args.max_w, args.step, offsets, args.rows)

    d = dedup(cands)[: args.top]
    print("best (cost, offset, row_width_bytes):")
    for c, off, w in d:
        print("  cost=%.4f  off=%5d  width=%6d" % (c, off, w))
    return 0


if __name__ == "__main__":
    sys.exit(main())
