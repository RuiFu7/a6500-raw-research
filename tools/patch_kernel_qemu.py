"""Apply the OpenMemories-CI QEMU console patch to a Sony ARM kernel."""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'vendor',
    'OpenMemories-CI_full'))

from runner.kernel_patch import getKernelBase, patchConsoleEnable  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: patch_kernel_qemu.py <kernel> <out>")
        return 1
    kernel = open(sys.argv[1], 'rb').read()
    print('kernel base: 0x%x' % getKernelBase(kernel))
    patched = patchConsoleEnable(kernel)
    with open(sys.argv[2], 'wb') as out:
        out.write(patched)
    print('patched %d bytes -> %s' % (len(patched), sys.argv[2]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
