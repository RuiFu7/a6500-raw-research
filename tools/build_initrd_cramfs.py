"""Rebuild a Sony-compatible cramfs from an unpacked initrd tree."""

import io
import os
import stat
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'vendor', 'fwtool.py'))

from fwtool.archive import UnixFile, cramfs  # noqa: E402


def main() -> int:
    shell_init = '--shell-init' in sys.argv
    args = [a for a in sys.argv[1:] if a != '--shell-init']
    if len(args) not in (2, 3):
        print("usage: build_initrd_cramfs.py <unpacked_root> <out.img> "
              "[strip_prefix] [--shell-init]")
        return 1
    root = os.path.abspath(args[0])
    out_path = args[1]
    strip = args[2] if len(args) == 3 else ''

    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = os.path.relpath(dirpath, root).replace('\\', '/')
        if strip and rel.startswith(strip):
            rel = rel[len(strip):].lstrip('/')
        path = '/' + rel if rel != '.' else ''
        st = os.stat(dirpath)
        files.append(UnixFile(
            path, st.st_size, int(st.st_mtime),
            stat.S_IFDIR | (st.st_mode & 0o7777), st.st_uid, st.st_gid, None))
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel_path = os.path.relpath(full, root).replace('\\', '/')
            if strip and rel_path.startswith(strip):
                rel_path = rel_path[len(strip):].lstrip('/')
            item_path = '/' + rel_path
            lst = os.lstat(full)
            if stat.S_ISLNK(lst.st_mode):
                target = os.readlink(full)
                files.append(UnixFile(
                    item_path, len(target), int(lst.st_mtime),
                    stat.S_IFLNK | 0o777, 0, 0,
                    io.BytesIO(target.encode('utf-8'))))
            elif stat.S_ISREG(lst.st_mode):
                file_mode = stat.S_IFREG | (lst.st_mode & 0o7777)
                if not (file_mode & 0o111):
                    with open(full, 'rb') as probe:
                        head = probe.read(4)
                    if head.startswith(b'\x7fELF') or name in ('init', 'busybox'):
                        file_mode |= 0o111
                files.append(UnixFile(
                    item_path, lst.st_size, int(lst.st_mtime), file_mode,
                    lst.st_uid, lst.st_gid, open(full, 'rb')))
            # device/socket nodes are intentionally skipped

    if not any(f.path == '/bin/sh' for f in files):
        files.append(UnixFile(
            '/bin/sh', 7, 0, stat.S_IFLNK | 0o777, 0, 0,
            io.BytesIO(b'busybox')))

    # The unpacked rootfs lost the original busybox applet symlinks.  Sony's
    # updater cramfs uses /bin/cat -> busybox style links, and the kernel's
    # cramfs driver resolves them, so recreate the common ones here.
    bin_applets = [
        'ash', 'cat', 'chgrp', 'chmod', 'chown', 'cp', 'cpio', 'cut',
        'date', 'dd', 'dmesg', 'echo', 'egrep', 'false', 'fgrep', 'grep',
        'gunzip', 'gzip', 'kill', 'ln', 'login', 'ls', 'md5sum', 'mkdir',
        'mkfifo', 'mknod', 'mktemp', 'mount', 'mv', 'pidof', 'ping',
        'ping6', 'pwd', 'rm', 'rmdir', 'sed', 'sleep', 'sync', 'tar',
        'tee', 'touch', 'true', 'umount', 'uname', 'usleep', 'wc',
        'xargs', 'zcat',
    ]
    sbin_applets = [
        'freeramdisk', 'getty', 'halt', 'ifconfig', 'insmod', 'lsmod',
        'mdev', 'modprobe', 'pivot_root', 'poweroff', 'reboot', 'rmmod',
        'swapoff', 'swapon',
    ]
    existing = {f.path for f in files}
    for name in bin_applets:
        path = '/bin/%s' % name
        if path not in existing:
            files.append(UnixFile(
                path, 7, 0, stat.S_IFLNK | 0o777, 0, 0,
                io.BytesIO(b'busybox')))
    for name in sbin_applets:
        path = '/sbin/%s' % name
        if path not in existing:
            files.append(UnixFile(
                path, 16, 0, stat.S_IFLNK | 0o777, 0, 0,
                io.BytesIO(b'../bin/busybox')))

    lib_links = {
        '/lib/ld-linux.so.3': 'ld-2.11.2.so',
        '/lib/libc.so.6': 'libc-2.11.2.so',
        '/lib/libdl.so.2': 'libdl-2.11.2.so',
        '/lib/libm.so.6': 'libm-2.11.2.so',
        '/lib/libpthread.so.0': 'libpthread-2.11.2.so',
        '/lib/librt.so.1': 'librt-2.11.2.so',
        '/lib/libnsl.so.1': 'libnsl-2.11.2.so',
        '/lib/libcrypt.so.1': 'libcrypt-2.11.2.so',
        '/lib/libresolv.so.2': 'libresolv-2.11.2.so',
        '/lib/libncurses.so.5': 'libncurses.so.5.7',
        '/lib/libproc.so.3': 'libproc-3.2.7.so',
        '/lib/libcom_err.so.2': 'libcom_err.so.2.1',
        '/lib/libe2p.so.2': 'libe2p.so.2.3',
        '/lib/libuuid.so.1': 'libuuid.so.1.3.0',
        '/lib/libstdc++.so.6': 'libstdc++.so.6.0.14',
    }
    for link, target in lib_links.items():
        if not any(f.path == link for f in files):
            target_bytes = target.encode('utf-8')
            files.append(UnixFile(
                link, len(target_bytes), 0, stat.S_IFLNK | 0o777, 0, 0,
                io.BytesIO(target_bytes)))

    if shell_init:
        script = (
            b'#!/bin/sh\n'
            b'mount -t proc proc /proc\n'
            b'mount -t sysfs sysfs /sys\n'
            b'mount -t devtmpfs devtmpfs /dev\n'
            b'while true; do sh; done\n'
        )
        busy = next(f for f in files if f.path == '/bin/busybox')
        busy.contents.seek(0)
        busy_data = busy.contents.read()
        files = [
            f._replace(
                mode=stat.S_IFREG | 0o755,
                size=len(script),
                contents=io.BytesIO(script))
            if f.path == '/sbin/init' else f
            for f in files
        ]
        files = [
            f._replace(
                mode=stat.S_IFREG | 0o777,
                size=len(busy_data),
                contents=io.BytesIO(busy_data))
            if f.path == '/bin/sh' else f
            for f in files
        ]

    with open(out_path, 'w+b') as out_file:
        cramfs.writeCramfs(files, out_file)
    for item in files:
        if item.contents is not None:
            item.contents.close()
    print('wrote %s (%d entries)' % (out_path, len(files)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
