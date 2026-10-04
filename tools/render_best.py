#!/usr/bin/env python3
"""Render a dump under 10/12/16-bit and 8-bit interpretations across candidate
row widths, scoring each by in-row smoothness (a real image is smooth; wrong
width or bit depth looks like noise). Saves PNGs for the top candidates.
"""

import argparse
import sys

import numpy as np
from PIL import Image


def unpack10(a: np.ndarray):
    """MSB-aligned 10bpp: 5 bytes -> 4 pixels."""
    a = np.frombuffer(a, dtype=np.uint8) if isinstance(a, (bytes, bytearray)) else a
    n = len(a) // 5 * 5
    u = a[:n].astype(np.uint16).reshape(-1, 5)
    p0 = (u[:, 0] << 2) | (u[:, 1] >> 6)
    p1 = ((u[:, 1] & 0x3F) << 4) | (u[:, 2] >> 4)
    p2 = ((u[:, 2] & 0x0F) << 6) | (u[:, 3] >> 2)
    p3 = ((u[:, 3] & 0x03) << 8) | u[:, 4]
    return np.stack([p0, p1, p2, p3], axis=1).ravel().astype(np.uint16)


def unpack12(a: np.ndarray):
    """MSB-aligned 12bpp: 3 bytes -> 2 pixels."""
    a = np.frombuffer(a, dtype=np.uint8) if isinstance(a, (bytes, bytearray)) else a
    n = len(a) // 3 * 3
    u = a[:n].astype(np.uint16).reshape(-1, 3)
    p0 = (u[:, 0] << 4) | (u[:, 1] >> 4)
    p1 = ((u[:, 1] & 0x0F) << 8) | u[:, 2]
    return np.stack([p0, p1], axis=1).ravel().astype(np.uint16)


def row_corr_cost(img: np.ndarray):
    h, w = img.shape
    if w < 2 or h < 2:
        return None
    d = np.abs(img[:, :-1].astype(np.int32) - img[:, 1:].astype(np.int32))
    return float(d.mean())


def norm_save(img: np.ndarray, path: str):
    p1 = np.percentile(img, 1)
    p99 = np.percentile(img, 99)
    out = np.clip((img.astype(np.float32) - p1) / max(p99 - p1, 1), 0, 1)
    Image.fromarray((out * 255).astype(np.uint8), "L").save(path)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input")
    p.add_argument("--outdir", required=True)
    p.add_argument("--widths", type=str, default="1280,1920,2048,2560,2688,2720,2800,3072,3200,3280,3840,4000,4096")
    p.add_argument("--rows", type=int, default=700)
    args = p.parse_args()

    raw = open(args.input, "rb").read()
    widths = [int(x) for x in args.widths.split(",") if x.strip()]
    results = []
    offs = [0, 8, 16, 32, 64]

    for off in offs:
        base = raw[off:] if off < len(raw) else b""
        # 8-bit
        for w in widths:
            if len(base) // 2 < args.rows * w:
                continue
            n = args.rows * w
            img = np.frombuffer(base[:n], dtype=np.uint8).reshape(args.rows, w)
            c = row_corr_cost(img)
            results.append((c, "8bit", off, w, img))
        # 16-bit
        b16 = base[: len(base) // 2 * 2]
        for w in widths:
            if len(b16) // 2 < args.rows * w:
                continue
            n = args.rows * w
            img = np.frombuffer(b16[: n * 2], dtype="<u2").reshape(args.rows, w)
            c = row_corr_cost(img)
            results.append((c, "16bit", off, w * 2, img))
        # 10-bit packed (pixel width)
        b10 = base[: len(base) // 5 * 5]
        for w in widths:
            px = unpack10(b10)
            if len(px) < args.rows * w:
                continue
            img = px[: args.rows * w].reshape(args.rows, w)
            c = row_corr_cost(img)
            results.append((c, "10bit", off, w, img))
        # 12-bit packed
        b12 = base[: len(base) // 3 * 3]
        for w in widths:
            px = unpack12(b12)
            if len(px) < args.rows * w:
                continue
            img = px[: args.rows * w].reshape(args.rows, w)
            c = row_corr_cost(img)
            results.append((c, "12bit", off, w, img))

    # Deduplicate and report top by smoothness.
    results.sort(key=lambda t: t[0])
    best = []
    for c, bits, off, w, img in results:
        if any(abs(w - old_w) < 0.05 * old_w and bits == old_b for old_c, old_b, _, old_w, _ in best):
            continue
        best.append((c, bits, off, w, img))
        if len(best) >= 8:
            break
    print("best (cost, bits, offset, width_px/bytes):")
    for i, (c, bits, off, w, img) in enumerate(best):
        fn = "cand_%d_%s_off%d_w%d.png" % (i, bits, off, w)
        norm_save(img, args.outdir + "\\" + fn)
        print("  [%d] cost=%.4f bits=%s off=%d width=%d -> %s" % (i, c, bits, off, w, fn))
    return 0


if __name__ == "__main__":
    sys.exit(main())
