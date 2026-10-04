#!/usr/bin/env python3
"""Scan dumps for row width and Bayer-like phase structure.

For each dump, try a set of row widths (in bytes) and bit depths; score each
layout by how well 2x2 same-color phases separate (Bayer signature) and how
much the dump changes between the three time samples at the same address.
"""

import argparse
import hashlib
import json
import sys

import numpy as np


WIDTHS = [64, 128, 192, 240, 256, 320, 384, 480, 512, 640, 768, 960, 1024,
          1280, 1440, 1600, 1920, 2048, 2592, 3072, 3840, 4096]


def bayer_phase_score(data, row_bytes, bits):
    """Lower = stronger 2x2 phase separation (more Bayer-like)."""
    if bits == 8:
        arr = np.frombuffer(data, dtype=np.uint8).astype(np.int32)
        px = 1
    else:
        arr = np.frombuffer(data[: len(data) // 2 * 2], dtype="<u2").astype(np.int32)
        px = 2
    if row_bytes % px != 0:
        return None
    width = row_bytes // px
    n = len(arr)
    rows = n // width
    if rows < 8 or width < 8:
        return None
    img = arr[: rows * width].reshape(rows, width)
    # Same-color phase means vs cross-phase means: Bayer puts R and B on one
    # checker, G on the other. Compare phase mean differences and neighbor
    # correlation within same phase.
    p00 = img[0::2, 0::2].astype(np.float64)
    p01 = img[0::2, 1::2].astype(np.float64)
    p10 = img[1::2, 0::2].astype(np.float64)
    p11 = img[1::2, 1::2].astype(np.float64)
    m00, m01, m10, m11 = p00.mean(), p01.mean(), p10.mean(), p11.mean()
    # Same-color adjacent (2px apart) should be close; cross-phase spread wide.
    same = abs(m00 - m11) + abs(m01 - m10)
    cross = abs(m00 - m01) + abs(m00 - m10) + abs(m11 - m01) + abs(m11 - m10)
    # Also measure horizontal/vertical same-color neighbor smoothness.
    h = np.abs(img[:, :-2] - img[:, 2:]).mean()
    v = np.abs(img[:-2, :] - img[2:, :]).mean()
    base = np.abs(np.diff(img, axis=1)).mean()
    score = cross - same + h + v
    return {
        "width": width,
        "row_bytes": row_bytes,
        "rows": rows,
        "bits": bits,
        "same_phase_diff": float(same),
        "cross_phase_diff": float(cross),
        "h_adj": float(h),
        "v_adj": float(v),
        "base_h": float(base),
        "score": float(score),
    }


def changed_ratio(a: bytes, b: bytes):
    n = min(len(a), len(b))
    if n == 0:
        return 1.0
    d = np.frombuffer(a[:n], dtype=np.uint8) != np.frombuffer(b[:n], dtype=np.uint8)
    return float(d.mean())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("groups", nargs="+", help="triples: A1 A2 A3 B1 B2 B3 ...")
    p.add_argument("--json", default="")
    p.add_argument("--top", type=int, default=6)
    args = p.parse_args()
    if len(args.groups) % 3 != 0:
        p.error("expected triples of dump files")

    report = {}
    for g in range(0, len(args.groups), 3):
        t1, t2, t3 = args.groups[g : g + 3]
        d1 = open(t1, "rb").read()
        d2 = open(t2, "rb").read()
        d3 = open(t3, "rb").read()
        base = "/".join(t1.replace("\\", "/").split("/")[-1].rsplit("1", 1)[:-1])
        key = t1.split("\\")[-1][:-5] + "x"  # e.g. RA1x from RA1.BIN
        scans = []
        for row_bytes in WIDTHS:
            for bits in (8, 16):
                r = bayer_phase_score(d1, row_bytes, bits)
                if r:
                    scans.append(r)
        scans.sort(key=lambda r: r["score"])
        report[key] = {
            "t1_size": len(d1),
            "md5": {
                "t1": hashlib.md5(d1).hexdigest(),
                "t2": hashlib.md5(d2).hexdigest(),
                "t3": hashlib.md5(d3).hexdigest(),
            },
            "changed_12": changed_ratio(d1, d2),
            "changed_23": changed_ratio(d2, d3),
            "changed_13": changed_ratio(d1, d3),
            "top_widths": scans[: args.top],
        }

    if args.json:
        json.dump(report, open(args.json, "w", encoding="utf-8"), indent=1)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
