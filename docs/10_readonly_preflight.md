# α6500 数据线到手后的只读前置清单

## 当前边界

本阶段只做：建立连接、读取系统信息、确认设备节点、归档输出。禁止：

- 刷写或修改固件
- 写入 `/setting`、`/sdcard` 或其他相机路径
- `insmod` / `rmmod`
- `devmem` 或 `/dev/mem` 访问
- 发送 `SET_*`、修改 Movie/RAW 参数
- 触发 DualRec、gdb 注入或 RAM patch

## 连接前检查

1. 相机电池充足，取下重要 SD 卡或确认使用实验卡。
2. 记录机身型号、固件版本、镜头、电池状态和连接方式。
3. 电脑侧准备 `adb`，运行 `adb devices`；此时只确认设备列表，不执行 shell 写命令。
4. 确认工作区为 `<workspace>`。

## 推荐命令

在工作区执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/capture_readonly_probe.ps1
```

指定设备序列号：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/capture_readonly_probe.ps1 -Serial <serial>
```

脚本只在电脑侧创建 `experiments/readonly/a6500_<时间>/`，向相机 stdin 发送 `probe_readonly.sh`，并把 stdout/stderr 写回电脑。相机侧探测脚本不创建文件、不加载模块、不打开 `/dev/mem`、不执行任何写操作。

## 输出验收

检查本地目录中的：

- `probe.stdout.txt`
- `probe.stderr.txt`
- `host_metadata.txt`

记录 `probe.stdout.txt` 的 SHA256。重点查看：

- `/proc/cmdline`：启动参数和内存范围
- `/proc/meminfo`、`/proc/iomem`：内存布局
- `/proc/modules`、`/proc/devices`：驱动与主设备号
- `/dev/stream*`、`/dev/dmac`、`/dev/uipc`、`/dev/dmm*` 等节点
- `/setting/mode/dmode` 和 `/setting/updater/mode` 是否可读

节点存在只能证明设备节点存在，不能证明能读取 Bayer RAW。

## 失败处理

- `adb devices` 无设备：只排查驱动、USB 模式和线缆，不改相机设置。
- shell 无 root：记录权限错误，停止，不尝试提权或加载模块。
- `/proc/iomem`、`/proc/devices` 不可读：记录为缺失证据，不进行猜测。
- 任何命令出现写入提示：立即停止并保留 stderr。

## 下一步门槛

只有只读基线归档完成、输出可重复获取、且未产生相机写入后，才讨论“运行时读取”。运行时读取仍需单独设计地址范围、读取长度、频率和恢复方案。
