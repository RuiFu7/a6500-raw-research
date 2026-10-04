#!/usr/bin/env python3
"""Boot alpha6500 vmlinux.bin with a rebuilt cramfs initrd in QEMU."""

import os
import socket
import subprocess
import sys
import time

QEMU = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', '..',
                 'tools', 'vendor', 'a6300_updater_emu_full',
                 'qemu-system-arm.exe'))
BASE = os.path.dirname(os.path.abspath(__file__))
KERNEL = os.path.join(BASE, 'a6500-kernel', 'vmlinux_patched.img')
INITRD = os.path.join(BASE, 'a6500-kernel', 'initrd_cramfs.img')
CMDLINE = (
    "initrd=0x80628000,0x00F00000 root=/dev/ram0 init=/sbin/init "
    "stack_usage=y heap_profile.records=0 cxd90014.bam=N "
    "console=ttyAM0,115200n8 rw noatime noalign amba2.console=1 cfg.uart=5 "
    "cfg.poff=1,1 pm.ddr_ctrl=dpd warm.boot_drop=0 warm.ignore_drop=1 "
    "mem=1024M@0x80000000@0 memrsv=0x28000@0x80000000 "
    "memrsv=0x3D270000@0x82D90000"
)


def main() -> int:
    port = 4341
    args = [
        QEMU,
        '-machine', 'cxd90014',
        '-display', 'none',
        '-serial', 'tcp::%d,server,mux' % port,
        '-icount', 'shift=2',
        '-device', 'bionz_hibari,id=hibari,bus=/sio1',
        '-connect-gpio', 'odev=gpio5,onum=18,idev=hibari,iname=ssi-gpio-cs',
        '-device', 'bionz_piroshki,id=piroshki,bus=/sio1',
        '-connect-gpio', 'odev=gpio1,onum=3,idev=piroshki,iname=ssi-gpio-cs',
        '-kernel', KERNEL,
        '-initrd', INITRD,
        '-append', CMDLINE,
    ]
    proc = subprocess.Popen(
        args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    sock = None
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            sock = socket.create_connection(('127.0.0.1', port), timeout=2)
            break
        except OSError:
            time.sleep(0.5)
    if sock is None:
        proc.kill()
        print('no serial port within 60s')
        return 1
    sock.settimeout(0.2)

    log = []
    end = time.monotonic() + 150
    while time.monotonic() < end:
        if proc.poll() is not None:
            break
        try:
            data = sock.recv(4096)
        except socket.timeout:
            continue
        except OSError:
            break
        if not data:
            break
        text = data.decode('latin1', 'replace')
        log.append(text)
        sys.stdout.write(text)
        sys.stdout.flush()

    proc.kill()
    sock.close()
    with open(os.path.join(BASE, 'a6500_boot_cramfs.log'), 'w',
              encoding='utf-8') as out:
        out.write(''.join(log))
    print('\ncaptured %d bytes' % sum(len(x) for x in log))
    return 0


if __name__ == '__main__':
    sys.exit(main())
