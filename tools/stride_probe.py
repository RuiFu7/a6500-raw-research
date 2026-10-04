#!/usr/bin/env python3
"""Probe a memory dump for row stride and bit depth.

Tries byte-level and 16-bit-level autocorrelation to find the row period,
then reports candidate (bits, stride) pairs for Bayer analysis.
"""

import argparse
import json
import sys

import numpy as np


def acf_lags(x: np.ndarray, max_lag: int):
    """Mean |diff| at each lag (smaller = more correlated)."""
    n = len(x)
    out = []
    for lag in range(1, max_lag + 1):
        d = x[:-lag].astype(np.int64) - x[lag:].astype(np.int64)
        out.append(float(np.abs(d).mean()))
    return np.array(out)


def top_lags(costs: np.ndarray, k=12, block=64):
    """Return lags with local minima (period candidates), dedup near-multiples."""
    idx = np.argsort(costs)
    chosen = []
    seen = set()
    for i in idx:
        lag = int(i) + 1
        if lag in seen:
            continue
        if any(abs(lag - c) < block for c in chosen):
            continue
        chosen.append(lag)
        seen.add(lag)
        if len(chosen) >= k:
            break
    return chosen


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("inputs", nargs="+")
    p.add_argument("--max-lag", type=int, default=2048)
    p.add_argument("--window", type=int, default=262144,
                   help="bytes to sample from the start for autocorrelation")
    p.add_argument("--json", default="")
    args = p.parse_args()

    report = {}
    for fn in args.inputs:
        data = open(fn, "rb").read()
        win = data[: args.window]
        b8 = np.frombuffer(win, dtype=np.uint8)
        u16 = np.frombuffer(win[: len(win) // 2 * 2], dtype="<u2")
        cost8 = acf_lags(b8, min(args.max_lag, len(b8) - 2))
        cost16 = acf_lags(u16, min(args.max_lag // 2, len(u16) - 2))
        rep = {
            "size": len(data),
            "window": len(win),
            "byte_diff_lags": top_lags(cost8),
            "word16_diff_lags": [l * 2 for l in top_lags(cost16)],
            "byte_mean": float(b8.mean()),
            "byte_std": float(b8.std()),
            "u16_mean": float(u16.mean()),
            "u16_std": float(u16.std()),
        }
        # Simpler high/low byte split on little-endian u16 buffer.
        hi = (u16 >> 8).astype(np.uint8)
        lo = (u16 & 0xFF).astype(np.uint8)
        rep["u16_lo_byte_mean"] = float(lo.mean())
        rep["u16_hi_byte_mean"] = float(hi.mean())
        report[fn] = rep

    if args.json:
        json.dump(report, open(args.json, "w", encoding="utf-8"), indent=1)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
