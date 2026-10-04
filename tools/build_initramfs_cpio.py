"""Build a gzip cpio initramfs from an unpacked rootfs tree."""

import gzip
import io
import os
import stat
import sys


def _pad4(data):
    return data + b'\0' * ((4 - len(data) % 4) % 4)


def cpio_entry(name, mode, data, ino, mtime=0, uid=0, gid=0):
    name = name.lstrip('/')
    name_bytes = name.encode('utf-8') + b'\0'
    fields = (
        ino, mode, uid, gid, 1, mtime, len(data),
        0, 0, 0, 0, len(name_bytes), 0,
    )
    header = b'070701' + b''.join(
        ('%08X' % value).encode('ascii') for value in fields)
    return _pad4(header + name_bytes) + _pad4(data)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != '--shell-init']
    shell_init = '--shell-init' in sys.argv
    if len(args) != 2:
        print("usage: build_initramfs_cpio.py <root> <out.cpio.gz> "
              "[--shell-init]")
        return 1
    root = os.path.abspath(args[0])
    out_path = args[1]

    entries = []
    ino = 1
    busy_data = None

    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace('\\', '/')
        path = '' if rel == '.' else rel
        st = os.stat(dirpath)
        entries.append((path or '.', stat.S_IFDIR | 0o755, b'',
                        int(st.st_mtime)))
        ino += 1
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel_path = os.path.relpath(full, root).replace('\\', '/')
            lst = os.lstat(full)
            mtime = int(lst.st_mtime)
            if stat.S_ISLNK(lst.st_mode):
                target = os.readlink(full).encode('utf-8')
                entries.append(
                    (rel_path, stat.S_IFLNK | 0o777, target, mtime))
                ino += 1
            elif stat.S_ISREG(lst.st_mode):
                mode = stat.S_IFREG | (lst.st_mode & 0o7777)
                with open(full, 'rb') as f:
                    data = f.read()
                if not (mode & 0o111) and (
                        data.startswith(b'\x7fELF') or name in ('init', 'busybox')):
                    mode |= 0o111
                entries.append((rel_path, mode, data, mtime))
                if rel_path == 'bin/busybox':
                    busy_data = data
                ino += 1

    if shell_init:
        if busy_data is None:
            print('busybox not found')
            return 1
        script = (
            b'#!/bin/sh\n'
            b'mount -t proc proc /proc\n'
            b'mount -t sysfs sysfs /sys\n'
            b'mount -t devtmpfs devtmpfs /dev\n'
            b'while true; do sh; done\n'
        )
        entries = [
            (path, stat.S_IFREG | 0o755, script, 0)
            if path in ('sbin/init', 'init') else (path, mode, data, mtime)
            for path, mode, data, mtime in entries
        ]
        entries = [
            (path, stat.S_IFREG | 0o777, busy_data, 0)
            if path == 'bin/sh' else (path, mode, data, mtime)
            for path, mode, data, mtime in entries
        ]
        entries.append(('init', stat.S_IFREG | 0o755, script, 0))
        ino += 1

    lib_links = {
        'lib/ld-linux.so.3': 'ld-2.11.2.so',
        'lib/libc.so.6': 'libc-2.11.2.so',
        'lib/libdl.so.2': 'libdl-2.11.2.so',
        'lib/libm.so.6': 'libm-2.11.2.so',
        'lib/libpthread.so.0': 'libpthread-2.11.2.so',
        'lib/librt.so.1': 'librt-2.11.2.so',
        'lib/libnsl.so.1': 'libnsl-2.11.2.so',
        'lib/libcrypt.so.1': 'libcrypt-2.11.2.so',
        'lib/libresolv.so.2': 'libresolv-2.11.2.so',
        'lib/libncurses.so.5': 'libncurses.so.5.7',
        'lib/libproc.so.3': 'libproc-3.2.7.so',
        'lib/libcom_err.so.2': 'libcom_err.so.2.1',
        'lib/libe2p.so.2': 'libe2p.so.2.3',
        'lib/libuuid.so.1': 'libuuid.so.1.3.0',
        'lib/libstdc++.so.6': 'libstdc++.so.6.0.14',
    }
    existing = {path for path, _, _, _ in entries}
    for link, target in lib_links.items():
        if link not in existing:
            entries.append(
                (link, stat.S_IFLNK | 0o777, target.encode('utf-8'), 0))
            ino += 1

    out = io.BytesIO()
    current_ino = 1
    for name, mode, data, mtime in entries:
        out.write(cpio_entry(name, mode, data, current_ino, mtime))
        current_ino += 1
    out.write(cpio_entry('TRAILER!!!', 0, b'', current_ino))

    compressed = gzip.compress(out.getvalue(), compresslevel=9, mtime=0)
    with open(out_path, 'wb') as f:
        f.write(compressed)
    print('wrote %s (%d bytes cpio, %d bytes gzip, %d entries)' %
          (out_path, len(out.getvalue()), len(compressed), len(entries)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
