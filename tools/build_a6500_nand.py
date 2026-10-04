"""Build a bootable CXD90014 NAND image from a6500 kernel/rootfs."""

import os
import sys

VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vendor')
sys.path.insert(0, os.path.join(VENDOR, 'OpenMemories-CI_full'))
sys.path.insert(0, os.path.join(VENDOR, 'fwtool.py'))

from runner import archive, nand  # noqa: E402


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: build_a6500_nand.py <kernel> <initrd> <out.nand>")
        return 1
    kernel_path, initrd_path, out_path = sys.argv[1:4]
    ci_fw = os.path.join(VENDOR, 'OpenMemories-CI_full',
                         'firmware', 'DSC-RX100M5')

    def read(name):
        with open(name, 'rb') as f:
            return f.read()

    boot1 = read(os.path.join(ci_fw, 'boot1'))
    boot5 = read(os.path.join(ci_fw, 'boot5'))

    flash1 = archive.Archive()
    flash1.write('/boot/vmlinux.bin', read(kernel_path))
    flash1.write('/boot/initrd.img', read(initrd_path))
    flash1_data = archive.writeFat(flash1, 0x800000)

    flash2 = archive.Archive()
    for name in ('Backup.bin', 'DmmConfig.bin', 'ulogio.bin'):
        flash2.write('/' + name, read(os.path.join(ci_fw, name)))
    flash2.write('/updater/dat4', b'\x00\x01')
    flash2.write('/updater/mode', b'')
    flash2.patch('/Backup.bin',
                 lambda d: d[:8] + b'\x01\0\0\0' + d[12:])
    flash2_data = archive.writeFat(flash2, 0x400000)

    partitions = archive.writeFlash([flash1_data, flash2_data])
    image = nand.writeNand(boot1, boot5, partitions, 0x4000000)
    with open(out_path, 'wb') as out:
        out.write(image)
    print('kernel=%d initrd=%d nand=%d' %
          (len(read(kernel_path)), len(read(initrd_path)), len(image)))
    print('wrote %s' % out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
