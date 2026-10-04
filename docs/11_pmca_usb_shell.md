# PMCA USB 只读连接路线

## 推荐顺序

1. 相机正常开机并保持普通 USB/MTP 或大容量存储模式。
2. 电脑侧先运行 `pmca-console info`，只读取设备信息。
3. 如果设备支持服务模式，再运行 `pmca-console serviceshell`。
4. 在 PMCA 菜单中输入 `shell` 进入相机 shell。
5. 只执行 `scripts/probe_readonly.sh` 中的读取命令，或逐条执行本页的基线命令。
6. 用 `exit` 退出相机 shell，再用 `exit` 退出 PMCA。

`updatershell` 不用于第一轮基线：它涉及更新器启动路径和重启流程，留在后续阶段。

## Windows 命令

在 `<workspace>` 打开 PowerShell：

```powershell
python.exe tools/vendor/Sony-PMCA-RE/pmca-console.py info
python.exe tools/vendor/Sony-PMCA-RE/pmca-console.py serviceshell
```

进入 PMCA shell 后：

```text
shell
```

## 最小只读基线命令

这些命令只读取 stdout，不创建相机文件：

```sh
uname -a
cat /proc/cmdline
cat /proc/meminfo
cat /proc/iomem
cat /proc/modules
cat /proc/devices
cat /proc/partitions
cat /proc/mounts
ls -la /dev
ls -la /dev/block
ls -la /sys/class
cat /setting/mode/dmode
cat /setting/updater/mode
```

更完整的输出使用 `scripts/probe_readonly.sh`。由于 PMCA 的交互终端不是 ADB stdin 管道，第一轮可先逐条执行上面的最小命令并在电脑侧保存终端输出；不要把脚本 push 到相机。

## 驱动提示

`serviceshell` 在 Windows 上可能需要 libusb 驱动。驱动切换只影响电脑侧 USB 绑定，不要在相机上执行写入动作。若系统提示切换驱动或相机模式，先停止并记录提示，确认后再继续。

## 禁止项

- 不运行 `firmware`、`updatershell`、`install`、`push`、`bk w`、`bk patch`。
- 不使用 `devmem`、`/dev/mem`、`insmod`、`rmmod`。
- 不改变 `/setting`，不发送 `SET_*`，不触发 DualRec。
- 任何只读命令返回异常时，保留原始终端输出，不用替代命令猜测。

## 记录

把终端输出保存到电脑侧 `experiments/readonly/<日期>_<编号>/probe.stdout.txt`，并在 `setup.md` 记录型号、固件版本、连接模式和 PMCA 版本。节点存在不等于 Bayer RAW 已经可访问。
