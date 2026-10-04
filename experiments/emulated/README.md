# CXD90014 QEMU 模拟结果

运行方式：`tools/vendor/a6300_updater_emu_full/run.py`（bundled Python，Windows QEMU）。

镜像来源：`BI2QFA/a6300_updater_emu`（经 ghproxy 镜像完整下载），内容为 α6300（ILCE-6300，CXD90014）更新器 Linux 内核与 cramfs initrd，通过 ma1co 的 QEMU fork 在 `cxd90014` machine 上启动。

已确认可进入 BusyBox root shell，并读取 `/proc/iomem`、`/proc/meminfo`、`/proc/cmdline`、`/dev`、`uname`。

注意：这是 a6300 更新器内核，与 α6500 同 SoC 但非同一固件；用于 CXD90014 内存布局与设备节点证据，α6500 实机仍需运行时确认。

补充：更新器内核的 `/proc/devices` 未注册 248-252 等索尼私有主设备号（`/dev/stream`、`/dev/dmac`、`/dev/uipc` 等是静态 MAKEDEV 节点）；这些主设备号应由完整相机系统加载驱动后注册。真机实验应以 `/proc/devices` 与 `ls -la /dev` 实测为准。

### α6500 内核基址（已推导）

用 OpenMemories-CI 的 `runner/kernel_patch.getKernelBase()` 对 α6500 `vmlinux.bin` 反推，得到内核加载基址 `0x40038000`，与模拟器 a6300 更新器内核一致（同一 CXD90014 内核布局）。

### α6500 完整内核启动尝试（未成功）

`run_a6500_kernel.py` 用 QEMU cxd90014 machine + α6500 `vmlinux.bin`/`initrd.img`（含完整 cmdline）启动，90 秒无串口输出。原因未定（疑似需要 4 核/完整 Loader 启动链或额外设备）；该尝试不构成否定证据。完整相机系统模拟需要 OpenMemories-CI 的 Loader2/Loader3 启动链与对应固件 dump。

补充（2026-08-29）：α6500 `initrd.img` 被 fwtool 识别为 **ext2 文件系统**（superblock magic `0xEF53` 位于偏移 `0x438`），不是 cramfs/cpio；它内含多处 gzip 流属于 ext2 内的文件数据。QEMU `-initrd` 直接加载 ext2 镜像仍无输出，可能原因包括内核未启用 ext2-on-ramdisk 或需要 Loader 启动链。fwtool 已成功解包出 `init`、`sbin`、`lib` 等文件，下一步可用 `writeCramfs` 重建索尼兼容 cramfs 再试。

再试（2026-08-29，仍未成功）：依次尝试了 `patchConsoleEnable` 补丁内核、用 `writeCramfs` 重建的 cramfs initrd、补上 `bionz_hibari`/`bionz_piroshki` 两个模拟设备，以及换用 a6300 更新器 cramfs initrd 做隔离测试，QEMU 串口仍 0 字节输出。结论：问题定位在 α6500 内核与现有 QEMU machine 的兼容性，而不是 initrd 格式。工具已入库：`tools/build_initrd_cramfs.py`、`tools/patch_kernel_qemu.py`、`tools/unpack_patch_kernel.py`、`experiments/emulated/run_a6500_kernel_cramfs.py`。剩余阻塞点最可能是完整 Loader2/Loader3 启动链或 QEMU machine 缺设备。

Loader2/Loader3 尝试（2026-08-29）：已按 OpenMemories-CI `test_cxd90014.py` 配方写好 `tools/build_a6500_nand.py`，可把 α6500 内核 + nflasha7 rootfs cramfs 打包进 NAND。但 CI 的 `firmware/DSC-RX100M5/*.enc` 是 OpenSSL `Salted__` AES 加密（`ci.yml` 用 GitHub Secret `FIRMWARE_KEY` 解密），仓库内没有口令，因此无法取得 boot1/boot5/bootrom 解密镜像，Loader2/3 启动暂时阻塞。

### a6300 内核 + α6500 rootfs：完整 shell（2026-08-29）

`run_a6300_kernel_a6500_rootfs.py` 用 a6300 更新器内核启动 α6500 `nflasha7` cramfs rootfs，已进入 BusyBox shell。`tools/build_initrd_cramfs.py` 现在会补回解包时丢失的 busybox applet 符号链接（`/bin/cat`、`/bin/ls`、`/bin/mount`、`/sbin/insmod` 等，均指向 `busybox`/`../bin/busybox`）。

实测结果：

- `/proc/iomem` 可读，得到 CXD90014 内存布局（arm7sram `0x00000000`、nandreg `0x00020000`、nandc `0x10000000`、System RAM `0x80000000-0xbfffffff`、uart0 `0xf2000000` 等）。
- `/proc/devices` 没有 248-252 等索尼私有主设备号；`/dev` 中也没有 `stream`、`dmac`、`uipc`、`hdmi`、`nflasha` 节点。
- `insmod /kmod/devno.ko` 成功（仅 taint 内核），但 dmac/nand/ldec/lld 均因缺少内核导出符号失败：`__bug_noarg`、`mumin_devif_*`、`PNAND_*`、`boss_hw_dmac_*`、`mem_section`、`boss_hw_ldec_lock`、`boss_lld_get_base_addr_ldec` 等。
- 结论：这些索尼私有符号应由完整 α6500 相机内核提供；a6300 更新器内核缺少它们，因此该组合只能做 rootfs/内存布局验证，不能作为完整驱动运行环境。

### α6500 完整内核 panic 定位（2026-08-29）

α6500 `vmlinux.bin` 在 QEMU `cxd90014` machine 上仍无串口输出，但通过 QEMU monitor 读取物理内存拿到了 panic 原因：

```
ERROR: Failed to allocate 0x1000 bytes below 0x0.
```

方法：启动时加 `-monitor telnet::<port>,server,nowait`，先连串口再连 monitor；panic 后 `xp /64cb 0x8042b710` 读出 `panic()` 的格式化缓冲（虚拟 `0x4042b710` 对应物理 `0x8042b710`）。

该消息对应内核字符串 `"ERROR: Failed to allocate 0x%llx bytes below 0x%llx.\n"`（vmlinux 文件偏移 `0x33b100`），同一字符串区域还有 `"Please increase the size of NR_BANKS in arch/arm/include/asm/setup.h"`，指向 mach-cxd90014 内存 bank 初始化。已建立独立 Ghidra 项目 `firmware/ghidra_projects/a6500_kernel`（base `0x40038000`）用于精确定位调用点。

调试辅助：`tools/patch_panic_uart.py` 可在 panic 路径的 printk 处插入 44 字节 UART dump 例程（`.text` 间隙 `0x402e3bc0`）；目前该 UART 在 panic 时尚未完成 MMIO 映射，实测仍需 monitor 内存读法。
