"""Self-tests for the firmware analysis toolchain."""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np

from raw_analyze import guess_pattern, unpack

PY = sys.executable


def pack_msb(img: np.ndarray, bits: int) -> bytes:
    h, w = img.shape
    flat = img.ravel()
    if bits == 10:
        n = len(flat) // 4 * 4
        a = flat[:n].reshape(-1, 4)
        out = np.empty((n // 4, 5), dtype=np.uint8)
        out[:, 0] = a[:, 0] >> 2
        out[:, 1] = ((a[:, 0] & 0x3) << 6) | (a[:, 1] >> 4)
        out[:, 2] = ((a[:, 1] & 0xF) << 4) | (a[:, 2] >> 6)
        out[:, 3] = ((a[:, 2] & 0x3F) << 2) | (a[:, 3] >> 8)
        out[:, 4] = a[:, 3] & 0xFF
        return out.tobytes()
    if bits == 12:
        n = len(flat) // 2 * 2
        a = flat[:n].reshape(-1, 2)
        out = np.empty((n // 2, 3), dtype=np.uint8)
        out[:, 0] = a[:, 0] >> 4
        out[:, 1] = ((a[:, 0] & 0xF) << 4) | (a[:, 1] >> 8)
        out[:, 2] = a[:, 1] & 0xFF
        return out.tobytes()
    raise ValueError


class TestTools(unittest.TestCase):
    def test_unpack_roundtrip_10bit(self):
        rng = np.random.default_rng(7)
        img = rng.integers(0, 1024, (8, 12), dtype=np.uint16)
        data = pack_msb(img, 10)
        back = unpack(data, 12, 8, 10, "msb", False)
        np.testing.assert_array_equal(back, img[:8, :12])

    def test_unpack_roundtrip_12bit(self):
        rng = np.random.default_rng(8)
        img = rng.integers(0, 4096, (8, 12), dtype=np.uint16)
        data = pack_msb(img, 12)
        back = unpack(data, 12, 8, 12, "msb", False)
        np.testing.assert_array_equal(back, img[:8, :12])

    def test_pattern_guess(self):
        h, w = 64, 64
        img = np.zeros((h, w), dtype=np.uint16)
        for r in range(h):
            for c in range(w):
                img[r, c] = 100 + ((r % 2) * 40 + (c % 2) * 10)
        self.assertEqual(guess_pattern(img), "RGGB")

    def test_raw_analyze_cli(self):
        h, w = 16, 16
        rng = np.random.default_rng(3)
        img = rng.integers(0, 1024, (h, w), dtype=np.uint16)
        with tempfile.TemporaryDirectory() as td:
            raw = os.path.join(td, "frame.raw")
            js = os.path.join(td, "report.json")
            with open(raw, "wb") as f:
                f.write(pack_msb(img, 10))
            subprocess.check_call(
                [PY, "tools/raw_analyze.py", raw, "--width", str(w), "--height", str(h),
                 "--bits", "10", "--json", js]
            )
            with open(js, encoding="utf-8") as f:
                rep = json.load(f)
            self.assertEqual(rep["bits"], 10)
            self.assertEqual(rep["width"], w)
            self.assertEqual(rep["height"], h)
            self.assertIn("bayer_pattern_guess", rep)

    def test_debayer_cli(self):
        h, w = 32, 32
        img = np.zeros((h, w), dtype=np.uint16)
        for r in range(h):
            for c in range(w):
                img[r, c] = (r * 5 + c * 3) % 256
        with tempfile.TemporaryDirectory() as td:
            raw = os.path.join(td, "bayer.raw")
            png = os.path.join(td, "out.png")
            with open(raw, "wb") as f:
                f.write(img.astype(np.uint8).tobytes())
            subprocess.check_call(
                [PY, "tools/debayer.py", raw, "--width", str(w), "--height", str(h),
                 "--bits", "8", "--output", png]
            )
            self.assertTrue(os.path.getsize(png) > 0)

    def test_compression_bench(self):
        with tempfile.TemporaryDirectory() as td:
            raw = os.path.join(td, "smooth.raw")
            h, w = 64, 64
            rng = np.random.default_rng(4)
            base = np.linspace(0, 900, w)[None, :] + np.linspace(0, 300, h)[:, None]
            img = np.clip(base + rng.normal(0, 5, (h, w)), 0, 1023).astype(np.uint16)
            with open(raw, "wb") as f:
                f.write(pack_msb(img, 10))
            out = subprocess.check_output(
                [PY, "tools/compression_bench.py", raw, "--width", str(w),
                 "--height", str(h), "--bits", "10", "--fps", "25"],
                text=True,
            )
            rep = json.loads(out)
            self.assertGreater(rep["ratio"], 1.5)

    def test_elf_disasm_cli(self):
        scenario = (
            "firmware/unpacked/ilce6500-v106/firmware.tar_unpacked/"
            "0700_part_image/dev/nflasha15_unpacked_unpacked/"
            "scenario/CAMERA_SCN_EXTERNAL_RAW_RECORD.so"
        )
        out = subprocess.check_output(
            [PY, "tools/elf_disasm.py", scenario, "--filter", "cam_scn_raw_output_on"],
            text=True,
        )
        self.assertIn("cam_scn_raw_output_on", out)
        self.assertIn("cam_scn_raw_ulogio_record_1bytehhhh", out)
        self.assertIn("cam_scn_raw_output_common", out)

    def test_find_symbol_cli(self):
        lib_dir = (
            "firmware/unpacked/ilce6500-v106/firmware.tar_unpacked/"
            "0700_part_image/dev/nflasha15_unpacked_unpacked/lib"
        )
        out = subprocess.check_output(
            [PY, "tools/find_symbol.py", lib_dir, "--symbol", "setRawResolution",
             "--defined-only"],
            text=True,
        )
        self.assertIn("libBizFw.so", out)
        self.assertIn("SdiCh16setRawResolution", out)


if __name__ == "__main__":
    unittest.main()
