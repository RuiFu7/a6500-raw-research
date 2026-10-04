"""Unpack a Sony zImage and apply the QEMU console patch."""

import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'vendor',
    'OpenMemories-CI_full'))

from runner.kernel_patch import getKernelBase, patchConsoleEnable  # noqa: E402
from runner.zimage import unpackZimage  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: unpack_patch_kernel.py <zimage> <out>")
        return 1
    data = open(sys.argv[1], 'rb').read()
    kernel = unpackZimage(data)
    if len(kernel) == 0:
        print('not a gzip zImage; falling back to raw kernel')
        kernel = data
    else:
        print('unpacked %d -> %d bytes' % (len(data), len(kernel)))
    print('kernel base: 0x%x' % getKernelBase(kernel))
    kernel = patchConsoleEnable(kernel)
    with open(sys.argv[2], 'wb') as out:
        out.write(kernel)
    print('patched -> %s' % sys.argv[2])
    return 0


if __name__ == '__main__':
    sys.exit(main())
