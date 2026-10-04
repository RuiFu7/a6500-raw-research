#!/usr/bin/env python3
"""Estimate the row width of an 8-bit frame dump.

A real image resized to its true row width has smooth (correlated) pixels
within each row; a wrong width makes in-row neighbors look random. We scan
candidate widths and report the horizontal neighbor-difference minimum.
"""

import argparse
import sys

import numpy as np


def in_row_diff_cost(img8: np.ndarray, w: int, rows: int):
    """Mean |pixel - right neighbor| over complete rows, excluding last col."""
    n = rows * w
    if n > len(img8):
        n = len(img8) // w * w
    a = img8[:n].reshape(-1, w)
    d = np.abs(a[:, :-1].astype(np.int16) - a[:, 1:].astype(np.int16))
    return float(d.mean())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--min-w", type=int, default=128)
    p.add_argument("--max-w", type=int, default=5200)
    p.add_argument("--step", type=int, default=16)
    p.add_argument("--rows", type=int, default=64)
    p.add_argument("--top", type=int, default=14)
    args = p.parse_args()

    data = open(args.input, "rb").read()
    img8 = np.frombuffer(data, dtype=np.uint8)
    costs = []
    for w in range(args.min_w, args.max_w + 1, args.step):
        c = in_row_diff_cost(img8, w, args.rows)
        costs.append((w, c))
    costs.sort(key=lambda t: t[1])
    top = costs[: args.top]
    # Deduplicate near-multiples (keep the smallest within 8%).
    dedup = []
    for w, c in top:
        if any(abs(w - old) < 0.08 * old for old, _ in dedup):
            continue
        dedup.append((w, c))
    print("candidate row widths (8-bit):")
    for w, c in dedup:
        print("  w=%5d  cost=%.4f" % (w, c))
    # Also try 16-bit view (each row width in pixels, so bytes = 2*w).
    print("candidate row widths (16-bit, output = byte row width):")
    img16 = np.frombuffer(data[: len(data) // 2 * 2], dtype="<u2")
    costs16 = []
    for w in range(args.min_w // 2, args.max_w // 2 + 1, max(1, args.step // 2)):
        c = in_row_diff_cost(img16, w, args.rows)
        costs16.append((w * 2, c))  # report byte row width
    costs16.sort(key=lambda t: t[1])
    seen = []
    for w, c in costs16[: args.top]:
        if any(abs(w - old) < 0.08 * old for old, _ in seen):
            continue
        seen.append((w, c))
    for w, c in seen:
        print("  bytes=%5d (px=%5d)  cost=%.4f" % (w, w // 2, c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
