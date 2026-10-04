"""Bayer predictor + Rice coding benchmark for 50-70 MB/s targets."""

import argparse
import sys

import numpy as np

from raw_analyze import unpack


class BitWriter:
    def __init__(self):
        self.out = bytearray()
        self.acc = 0
        self.nbits = 0

    def put_bit(self, b: int):
        self.acc = (self.acc << 1) | (b & 1)
        self.nbits += 1
        if self.nbits == 8:
            self.out.append(self.acc)
            self.acc = 0
            self.nbits = 0

    def put_bits(self, value: int, count: int):
        for i in range(count - 1, -1, -1):
            self.put_bit((value >> i) & 1)

    def finish(self) -> bytes:
        if self.nbits:
            self.out.append(self.acc << (8 - self.nbits))
        return bytes(self.out)


class BitReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.bit = 0

    def get_bit(self) -> int:
        if self.pos >= len(self.data):
            raise EOFError
        v = (self.data[self.pos] >> (7 - self.bit)) & 1
        self.bit += 1
        if self.bit == 8:
            self.bit = 0
            self.pos += 1
        return v

    def get_bits(self, count: int) -> int:
        v = 0
        for _ in range(count):
            v = (v << 1) | self.get_bit()
        return v


def rice_encode(values: np.ndarray, k: int) -> bytes:
    k = int(k)
    w = BitWriter()
    for v in values:
        q = int(v) >> k
        for _ in range(q):
            w.put_bit(1)
        w.put_bit(0)
        if k:
            w.put_bits(int(v) & ((1 << k) - 1), k)
    return w.finish()


def rice_decode(data: bytes, count: int, k: int) -> np.ndarray:
    k = int(k)
    r = BitReader(data)
    out = np.empty(count, dtype=np.int64)
    for i in range(count):
        q = 0
        while r.get_bit():
            q += 1
        rem = r.get_bits(k) if k else 0
        out[i] = q * (1 << k) + rem
    return out


def predict(img: np.ndarray, mode: str) -> np.ndarray:
    h, w = img.shape
    arr = img.astype(np.int32)
    res = np.zeros_like(arr)
    if mode == "left":
        res[:, 0] = arr[:, 0]
        res[:, 1:] = arr[:, 1:] - arr[:, :-1]
    elif mode == "up":
        res[0, :] = arr[0, :]
        res[1:, :] = arr[1:, :] - arr[:-1, :]
    else:  # left-up (JPEG-LS style)
        res[0, :] = arr[0, :]
        res[:, 0] = arr[:, 0]
        res[1:, 1:] = (
            arr[1:, 1:]
            - arr[1:, :-1]
            - arr[:-1, 1:]
            + arr[:-1, :-1]
        )
    return res


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", nargs="?", default="")
    parser.add_argument("--width", type=int, default=3072)
    parser.add_argument("--height", type=int, default=1728)
    parser.add_argument("--bits", type=int, default=10)
    parser.add_argument("--predictor", choices=["left", "up", "left-up"], default="left-up")
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--synthetic", action="store_true")
    args = parser.parse_args()

    if args.synthetic or not args.input:
        rng = np.random.default_rng(1)
        base = np.linspace(0, 900, args.width).astype(np.int32)[None, :] + np.linspace(
            0, 200, args.height
        )[:, None]
        img = np.clip(base + rng.normal(0, 8, (args.height, args.width)), 0, (1 << args.bits) - 1)
        img = img.astype(np.uint16)
    else:
        data = open(args.input, "rb").read()
        img = unpack(data, args.width, args.height, args.bits, "msb", False)

    res = predict(img, args.predictor)
    zig = np.where(res >= 0, 2 * res, -2 * res - 1).astype(np.int64)
    h, w = zig.shape
    row_ks = np.zeros(h, dtype=np.uint8)
    encoded_rows = []
    for row in range(h):
        vals = zig[row]
        best = (0, len(rice_encode(vals, 0)))
        for k in range(1, 13):
            size = len(rice_encode(vals, k))
            if size < best[1]:
                best = (k, size)
        row_ks[row] = int(best[0])
        encoded_rows.append(rice_encode(vals, best[0]))
    encoded = bytes(row_ks.tobytes()) + b"".join(encoded_rows)

    decoded_zig = np.empty_like(zig)
    offset = h
    for row in range(h):
        k = int(row_ks[row])
        n = w
        vals = rice_decode(encoded[offset:], n, k)
        decoded_zig[row] = vals
        offset += len(rice_encode(vals.astype(np.int64), k))
    decoded = np.where(
        decoded_zig & 1, -(decoded_zig + 1) // 2, decoded_zig // 2
    )
    assert np.array_equal(decoded, res), "rice round-trip mismatch"

    raw_bytes = img.nbytes
    ratio = raw_bytes / len(encoded)
    mbps = len(encoded) * args.fps / 1e6
    best_k = int(np.median(row_ks))
    print(
        json_dump(
            {
                "width": args.width,
                "height": args.height,
                "bits": args.bits,
                "predictor": args.predictor,
                "raw_bytes": raw_bytes,
                "compressed_bytes": len(encoded),
                "rice_k": best_k,
                "ratio": round(ratio, 3),
                "fps": args.fps,
                "compressed_mbps": round(mbps, 3),
                "target_mbps": 50,
                "within_70": mbps <= 70,
            }
        )
    )
    return 0


def json_dump(obj) -> str:
    import json

    return json.dumps(obj, indent=1)


if __name__ == "__main__":
    sys.exit(main())
