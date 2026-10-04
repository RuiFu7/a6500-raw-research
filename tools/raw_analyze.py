"""Analyze a raw memory dump for bit depth, packing and Bayer pattern."""

import argparse
import json
import sys

import numpy as np
from PIL import Image


def unpack(data: bytes, width: int, height: int, bits: int, packed: str, big_endian: bool):
    if bits == 8:
        arr = np.frombuffer(data, dtype=np.uint8)
    elif bits == 16:
        dtype = ">u2" if big_endian else "<u2"
        arr = np.frombuffer(data, dtype=np.dtype(dtype))
    else:
        # MSB-aligned packed Bayer: 10bpp=5B/4px, 12bpp=3B/2px, 14bpp=7B/4px
        per = {10: (5, 4), 12: (3, 2), 14: (7, 4)}[bits]
        unit = np.frombuffer(data, dtype=np.uint8).astype(np.uint16)
        n_units = len(unit) // per[0]
        unit = unit[: n_units * per[0]].reshape(-1, per[0])
        if packed == "msb":
            if bits == 10:
                p0 = (
                    unit[:, 0].astype(np.uint16) << 2
                    | (unit[:, 1] >> 6)
                )
                p1 = ((unit[:, 1] & 0x3F) << 4 | unit[:, 2] >> 4).astype(np.uint16)
                p2 = ((unit[:, 2] & 0x0F) << 6 | unit[:, 3] >> 2).astype(np.uint16)
                p3 = ((unit[:, 3] & 0x03) << 8 | unit[:, 4]).astype(np.uint16)
                raw = np.stack([p0, p1, p2, p3], axis=1).ravel()
            elif bits == 12:
                p0 = (unit[:, 0] << 4 | unit[:, 1] >> 4).astype(np.uint16)
                p1 = ((unit[:, 1] & 0x0F) << 8 | unit[:, 2]).astype(np.uint16)
                raw = np.stack([p0, p1], axis=1).ravel()
            else:  # 14
                p0 = (unit[:, 0] << 6 | unit[:, 1] >> 2).astype(np.uint16)
                p1 = (
                    (unit[:, 1] & 0x03) << 12 | unit[:, 2] << 4 | unit[:, 3] >> 4
                ).astype(np.uint16)
                p2 = (
                    (unit[:, 3] & 0x0F) << 10 | unit[:, 4] << 2 | unit[:, 5] >> 6
                ).astype(np.uint16)
                p3 = ((unit[:, 5] & 0x3F) << 8 | unit[:, 6]).astype(np.uint16)
                raw = np.stack([p0, p1, p2, p3], axis=1).ravel()
        else:
            raise ValueError("only msb-aligned packing is implemented")
        arr = raw
    expected = width * height
    if len(arr) < expected:
        raise ValueError(
            f"short buffer: {len(arr)} samples < {expected} ({width}x{height})"
        )
    return arr[:expected].reshape(height, width).astype(np.uint16)


def guess_pattern(img: np.ndarray) -> str:
    """Pick the 2x2 Bayer phase whose same-color pairs are most correlated."""
    h, w = img.shape
    cy = img[:, :-2].astype(np.int32) - img[:, 2:].astype(np.int32)
    cx = img[:-2, :].astype(np.int32) - img[2:, :].astype(np.int32)
    row_cost = [np.abs(cy[r::2]).mean() for r in range(2)]
    col_cost = [np.abs(cx[:, c::2]).mean() for c in range(2)]
    best_r = int(np.argmin(row_cost))
    best_c = int(np.argmin(col_cost))
    patterns = ["RGGB", "BGGR", "GRBG", "GBRG"]
    idx = {"RGGB": 0, "BGGR": 3, "GRBG": 1, "GBRG": 2}["RGGB"]
    # Map phase (best_r, best_c) onto pattern naming by shifting RGGB.
    shift = (best_r * 2 + best_c) % 4
    return patterns[(idx + shift) % 4]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--width", type=int, default=0)
    parser.add_argument("--height", type=int, default=0)
    parser.add_argument("--bits", type=int, choices=[8, 10, 12, 14, 16], default=0)
    parser.add_argument("--packed", choices=["msb"], default="msb")
    parser.add_argument("--big-endian", action="store_true")
    parser.add_argument("--json", default="")
    parser.add_argument("--png", default="")
    args = parser.parse_args()

    data = open(args.input, "rb").read()
    report = {"input": args.input, "size": len(data)}
    if args.width and args.height and args.bits:
        img = unpack(data, args.width, args.height, args.bits, args.packed, args.big_endian)
        report.update(
            width=args.width,
            height=args.height,
            bits=args.bits,
            packing=args.packed,
        )
    else:
        # Shallow auto mode: byte/word statistics only.
        arr8 = np.frombuffer(data, dtype=np.uint8)
        arr16 = np.frombuffer(data[: len(data) // 2 * 2], dtype="<u2")
        report.update(
            width=0,
            height=0,
            bits=0,
            auto={
                "u8": {"min": int(arr8.min()), "max": int(arr8.max()), "mean": float(arr8.mean())},
                "u16le": {
                    "min": int(arr16.min()),
                    "max": int(arr16.max()),
                    "mean": float(arr16.mean()),
                },
            },
        )
        if args.json:
            json.dump(report, open(args.json, "w", encoding="utf-8"), indent=1)
        print(json.dumps(report, indent=1))
        return 0

    stats = {
        "min": int(img.min()),
        "max": int(img.max()),
        "mean": float(img.mean()),
        "std": float(img.std()),
        "p01": float(np.percentile(img, 1)),
        "p99": float(np.percentile(img, 99)),
    }
    phases = {}
    for r in range(2):
        for c in range(2):
            p = img[r::2, c::2]
            phases[f"({r},{c})"] = {
                "mean": float(p.mean()),
                "std": float(p.std()),
                "min": int(p.min()),
                "max": int(p.max()),
            }
    report.update(stats=stats, phases=phases, bayer_pattern_guess=guess_pattern(img))
    if args.png:
        out = (img.astype(np.float32) - stats["p01"]) / max(stats["p99"] - stats["p01"], 1)
        Image.fromarray(np.clip(out * 255, 0, 255).astype(np.uint8), mode="L").save(args.png)
        report["png"] = args.png
    if args.json:
        json.dump(report, open(args.json, "w", encoding="utf-8"), indent=1)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
