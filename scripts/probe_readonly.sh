#!/bin/sh
# Read-only probe for Sony alpha6500 Linux/Android side.
# stdout only: no camera files, settings, module loads, or memory access.
set -u
section() { echo; echo "=== $1 ==="; }
read_file() { if [ -r "$1" ]; then cat "$1"; else echo "[unavailable] $1"; fi; }
read_optional_file() { if [ -r "$1" ]; then echo "--- $1 ---"; cat "$1"; else echo "[unavailable] $1"; fi; }
section probe_metadata
echo 'probe_version: 2026-09-01-readonly-v3'
date -u 2>/dev/null || true
id 2>/dev/null || true
section system
uname -a 2>/dev/null || true
read_optional_file /proc/version
read_optional_file /proc/cmdline
read_optional_file /proc/uptime
section memory_and_devices
read_file /proc/meminfo
read_file /proc/iomem
read_file /proc/interrupts
read_file /proc/modules
read_file /proc/devices
read_file /proc/misc
read_file /proc/partitions
read_file /proc/mounts
read_file /proc/filesystems
section loaded_modules
if [ -x /bin/busybox ]; then /bin/busybox lsmod 2>/dev/null || true; else echo '[unavailable] lsmod'; fi
section kernel_log_tail
if [ -x /bin/busybox ]; then dmesg 2>/dev/null | /bin/busybox tail -n 200 || true; else echo '[unavailable] busybox'; fi
section device_nodes
ls -la /dev 2>/dev/null || true
ls -la /dev/block 2>/dev/null || true
section sysfs_topology
ls -la /sys/class 2>/dev/null || true
ls -la /sys/bus 2>/dev/null || true
if [ -x /bin/busybox ]; then /bin/busybox find /sys -maxdepth 4 \( -iname '*stream*' -o -iname '*dmm*' -o -iname '*beaune*' -o -iname '*sen*' -o -iname '*codec*' -o -iname '*dmac*' \) -print 2>/dev/null || true; fi
section expected_nodes
for node in /dev/stream /dev/stream2 /dev/dmm /dev/dmac /dev/uipc /dev/mcmn /dev/ldec /dev/hdmi /dev/hdmi0 /dev/hdmi1 /dev/mmca1 /dev/ms1 /dev/dnflasha16; do
    if [ -e "$node" ]; then ls -la "$node" 2>/dev/null || true; else echo "[absent] $node"; fi
done
section settings_read_only
read_optional_file /setting/mode/dmode
read_optional_file /setting/updater/mode
section android_properties
if [ -x /bin/busybox ]; then getprop 2>/dev/null | /bin/busybox head -n 100 || true; else echo '[unavailable] getprop'; fi
section probe_end
echo 'camera_writes: none'
echo 'module_loads: none'
echo 'memory_writes: none'