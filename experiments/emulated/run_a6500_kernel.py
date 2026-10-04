#!/usr/bin/env python3
"""Boot the alpha6500 vmlinux.bin + initrd.img in QEMU (cxd90014 machine)."""

import os
import select
import socket
import subprocess
import sys
import threading
import time

QEMU = r"tools/vendor/a6300_updater_emu_full/qemu-system-arm.exe"
KERNEL = r"experiments/emulated/a6500-kernel/vmlinux.bin"
INITRD = r"experiments/emulated/a6500-kernel/initrd.img"
BASE_PORT = 4331
CMDLINE = (
    "initrd=0x80628000,0x00F00000 root=/dev/ram0 init=/sbin/init "
    "stack_usage=y heap_profile.records=0 cxd90014.bam=N "
    "console=ttyAM0,115200n8 rw noatime noalign amba2.console=1 cfg.uart=5 "
    "cfg.poff=1,1 pm.ddr_ctrl=dpd warm.boot_drop=0 warm.ignore_drop=1 "
    "mem=1024M@0x80000000@0 memrsv=0x28000@0x80000000 "
    "memrsv=0x3D270000@0x82D90000"
)


def find_port():
    for port in range(BASE_PORT, BASE_PORT + 32):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", port))
            s.close()
            return port
        except OSError:
            s.close()
    raise RuntimeError("no free port")


def main() -> int:
    port = find_port()
    args = [
        QEMU,
        "-machine", "cxd90014",
        "-display", "none",
        "-serial", f"tcp::{port},server,mux",
        "-icount", "shift=2",
        "-kernel", KERNEL,
        "-initrd", INITRD,
        "-append", CMDLINE,
    ]
    proc = subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    sock = socket.create_connection(("127.0.0.1", port), timeout=60)
    sock.settimeout(0.1)

    stop = threading.Event()

    def pump():
        while not stop.is_set():
            try:
                data = sock.recv(4096)
                if data:
                    sys.stdout.write(data.decode("latin1", "replace"))
                    sys.stdout.flush()
                else:
                    break
            except socket.timeout:
                continue
            except OSError:
                break

    thread = threading.Thread(target=pump, daemon=True)
    thread.start()
    try:
        while proc.poll() is None:
            if os.name == "nt":
                import msvcrt
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    sock.sendall(ch.encode("latin1"))
            else:
                r, _, _ = select.select([sys.stdin], [], [], 0.1)
                if r:
                    sock.sendall(sys.stdin.readline().encode("latin1"))
            time.sleep(0.02)
    finally:
        stop.set()
        proc.kill()
        sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
