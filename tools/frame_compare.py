#!/usr/bin/env python3
"""Compare the three time-point dumps of a candidate buffer.

Reports the fraction of bytes/words that changed between samples and where
the changes concentrate (start/middle/end of the 2MB window). A live video
frame buffer should change substantially frame-to-frame.
"""

import argparse
import sys

import numpy as np


def diff_ratio(a: np.ndarray, b: np.ndarray):
    if a.shape != b.shape:
        return None
    d = (a != b)
    return float(d.mean())


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("samples", nargs="+",
                   help="at least two same-size dumps, e.g. RA1.BIN RA2.BIN RA3.BIN")
    args = p.parse_args()
    arrays = {}
    for fn in args.samples:
        data = open(fn, "rb").read()
        arr8 = np.frombuffer(data, dtype=np.uint8)
        arr16 = np.frombuffer(data[: len(data) // 2 * 2], dtype="<u2")
        arrays[fn] = (arr8, arr16)

    names = list(arrays.keys())
    print("== byte-level diff ratios ==")
    for i in range(len(names) - 1):
        a, b = names[i], names[i + 1]
        r8 = diff_ratio(arrays[a][0], arrays[b][0])
        print("%s vs %s : %.4f" % (a, b, r8))
    for i in range(0, len(names) - 2, 2):
        a, c = names[i], names[i + 2]
        r8 = diff_ratio(arrays[a][0], arrays[c][0])
        print("%s vs %s : %.4f" % (a, c, r8))

    # Where do changes concentrate? Split into 16 chunks.
    print("== change concentration (16 chunks, %names) ==")
    a = arrays[names[0]][0]
    b = arrays[names[-1]][0]
    n = len(a)
    chunk = n // 16
    conc = []
    for k in range(16):
        seg = a[k * chunk:(k + 1) * chunk]
        seg2 = b[k * chunk:(k + 1) * chunk]
        conc.append(float((seg != seg2).mean()))
    print(" ".join("%.3f" % x for x in conc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
