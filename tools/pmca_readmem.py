#!/usr/bin/env python3
"""Read physical DRAM from a Sony senser (service mode) camera via PMCA.

Read-only: uses the senser MemoryDump (0xff03) protocol, no camera writes.

Usage:
  python pmca_readmem.py BASE SIZE OUTFILE [BASE2 SIZE2 OUTFILE2 ...]

All addresses/sizes are hex (0x...). Data is streamed to OUTFILE.
Reads are performed in chunks of --chunk bytes (default 0x10000) to avoid
overrunning any per-request limit in the senser firmware.
"""

import sys
import os
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
_PMCA = os.path.join(_HERE, "vendor", "Sony-PMCA-RE")
sys.path.insert(0, _PMCA)

# Patch usb.core.find to use the bundled libusb backend (same as pmca-console).
import usb.backend.libusb1 as _b
import libusb_package
import usb.core

_backend = _b.get_backend(find_library=lambda n: libusb_package.get_library_path())
_old_find = usb.core.find


def _patched_find(*a, **k):
    if "backend" not in k:
        k["backend"] = _backend
    return _old_find(*a, **k)


usb.core.find = _patched_find

from pmca.usb.sony import SonySenserAuthDevice, SonySenserCamera, SonySenserDevice  # noqa: E402
from pmca.usb.sony import SonyMscExtCmdDevice  # noqa: E402
from pmca.usb.driver.generic import GenericUsbDriver  # noqa: E402
from pmca.commands.usb import importDriver, listDevices  # noqa: E402
import time  # noqa: E402


def _connect():
    driver = importDriver()
    ctx = driver.__enter__()
    try:
        devices = [d for d in listDevices(ctx, quiet=True)]
    except Exception as e:
        raise RuntimeError("device enumeration failed: %s" % e)

    # Case 1: already in service mode.
    senser = [d for d in devices if isinstance(d, SonySenserDevice)]
    if len(senser) == 1:
        return driver, senser[0]

    # Case 2: mass storage mode -> request switch to service mode, then re-enumerate.
    msc = [d for d in devices if isinstance(d, SonyMscExtCmdDevice)]
    if len(msc) == 1:
        if not isinstance(msc[0].driver, GenericUsbDriver):
            raise RuntimeError("mass storage device is not using libusb driver")
        print("switching to service mode", flush=True)
        auth = SonySenserAuthDevice(msc[0].driver)
        auth.start()
        auth.authenticate()
        for _ in range(12):
            time.sleep(0.5)
            try:
                devs2 = [d for d in listDevices(ctx, quiet=True)]
            except Exception:
                devs2 = []
            s2 = [d for d in devs2 if isinstance(d, SonySenserDevice)]
            if len(s2) == 1:
                return driver, s2[0]
        raise RuntimeError("camera did not switch to service mode")

    raise RuntimeError("no Sony camera found; is it connected in mass storage mode?")


def _auth(cam):
    auth = SonySenserAuthDevice(cam.driver)
    auth.start()
    auth.authenticate()
    return auth


def main():
    parser = argparse.ArgumentParser(description="Read DRAM from Sony senser camera")
    parser.add_argument("jobs", nargs="+", help="BASE SIZE OUTFILE [BASE SIZE OUTFILE ...]")
    parser.add_argument("--chunk", type=lambda x: int(x, 0), default=0x10000,
                        help="chunk size per MemoryDump call (default 0x10000)")
    args = parser.parse_args()
    if len(args.jobs) < 3 or len(args.jobs) % 3 != 0:
        parser.error("jobs must be BASE SIZE OUTFILE triples")
    jobs = []
    for i in range(0, len(args.jobs), 3):
        base = int(args.jobs[i], 0)
        size = int(args.jobs[i + 1], 0)
        out = args.jobs[i + 2]
        jobs.append((base, size, out))

    driver, dev = _connect()
    auth = _auth(dev)
    cam = SonySenserCamera(dev)
    try:
        for base, size, out in jobs:
            print("reading 0x%08x +0x%x -> %s" % (base, size, out), flush=True)
            with open(out, "wb") as f:
                off = 0
                while off < size:
                    n = min(args.chunk, size - off)
                    cam.readMemory(base + off, n, f)
                    off += n
            print("done %s" % out, flush=True)
    finally:
        auth.stop()
        driver.__exit__(None, None, None)


if __name__ == "__main__":
    main()
