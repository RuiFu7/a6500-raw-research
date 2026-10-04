"""Bilinear Bayer debayer for raw dumps."""

import argparse
import sys

import numpy as np
from PIL import Image

from raw_analyze import unpack

PHASE = {
    "RGGB": ((0, 0), (0, 1), (1, 0), (1, 1)),
    "BGGR": ((1, 1), (1, 0), (0, 1), (0, 0)),
    "GRBG": ((0, 1), (0, 0), (1, 1), (1, 0)),
    "GBRG": ((1, 0), (1, 1), (0, 0), (0, 1)),
}


def debayer(img: np.ndarray, pattern: str) -> np.ndarray:
    h, w = img.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint16)
    for ch, (pr, pc) in zip(range(3), PHASE[pattern]):
        plane = np.zeros_like(img, dtype=np.float32)
        plane[pr::2, pc::2] = img[pr::2, pc::2]
        # Horizontal then vertical interpolation for missing pixels.
        for r in range(pr, h, 2):
            row = plane[r].copy()
            idx = np.arange(pc, w, 2)
            for c in idx:
                vals = []
                if c > 0:
                    vals.append(row[c - 1])
                if c + 1 < w:
                    vals.append(row[c + 1])
                if vals:
                    row[c] = float(np.mean(vals))
            plane[r] = row
        for c in range(pc, w, 2):
            col = plane[:, c].copy()
            idx = np.arange(pr, h, 2)
            for r in idx:
                vals = []
                if r > 0:
                    vals.append(col[r - 1])
                if r + 1 < h:
                    vals.append(col[r + 1])
                if vals:
                    col[r] = float(np.mean(vals))
            plane[:, c] = col
        rgb[:, :, ch] = np.clip(plane, 0, 65535).astype(np.uint16)
    return rgb


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument("--bits", type=int, choices=[8, 10, 12, 14, 16], default=8)
    parser.add_argument("--pattern", default="RGGB")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    data = open(args.input, "rb").read()
    img = unpack(data, args.width, args.height, args.bits, "msb", False)
    rgb = debayer(img, args.pattern)
    maxv = (1 << args.bits) - 1
    out8 = (rgb.astype(np.float32) / maxv * 255).clip(0, 255).astype(np.uint8)
    Image.fromarray(out8, mode="RGB").save(args.output)
    print(f"wrote {args.output} ({args.width}x{args.height}, {args.pattern}, {args.bits}bit)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
