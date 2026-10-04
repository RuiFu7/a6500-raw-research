# α6500 只读运行时实验协议

> 执行阶梯：**离线分析 → 只读 → 运行时读取 → RAM patch → 可恢复实验 → 永久固件修改**。
> 当前只允许建立连接和读取基线；不修改相机状态，不写相机文件，不读写内存映射。

## 1. 目标

第一轮只读实验只回答三个问题：

1. 相机是否能稳定建立 root shell/ADB 连接。
2. 实机的内存布局、驱动和设备节点是什么。
3. 运行环境是否具备后续运行时读取的前置条件。

第一轮**不判定**是否已经获得 Bayer RAW。RAW 判定要等后续单独编号的运行时读取实验。

## 2. 硬性禁止项

在完成只读基线前禁止：

- 刷写、修改或替换固件
- 写入 `/setting`、`/sdcard` 或任何相机路径
- `insmod` / `rmmod`
- `devmem`、`/dev/mem` 或任何物理内存读取
- 发送 `SET_*` 命令或修改 Movie/RAW 参数
- 触发 DualRec、调用 gdb/gdbserver 或注入代码
- 通过 shell 创建临时文件

输出必须由电脑侧接收和保存。

## 3. 连接前准备

- 相机电池充足。
- 取下重要 SD 卡，或使用专门的实验卡。
- 记录机身型号、固件版本、镜头、电池状态和连接方式。
- 电脑安装 `adb`，在工作区 `<workspace>` 打开 PowerShell。
- 连接后先运行 `adb devices`，只确认设备枚举，不运行写命令。

## 4. 第一轮执行

推荐使用电脑侧包装脚本：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/capture_readonly_probe.ps1
```

指定设备序列号：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/capture_readonly_probe.ps1 -Serial <serial>
```

脚本执行过程：

- 电脑侧创建 `experiments/readonly/a6500_<时间>/`。
- 通过 `adb shell sh -s` 把 `scripts/probe_readonly.sh` 送入 stdin。
- 相机侧脚本只读取 `/proc`、`/sys`、`/dev` 列表和可读设置。
- stdout、stderr、主机元数据全部保存到电脑侧。

## 5. 第一轮输出验收

检查归档目录：

- `probe.stdout.txt`
- `probe.stderr.txt`
- `host_metadata.txt`

在电脑侧计算并记录：

```powershell
Get-FileHash experiments/readonly/a6500_<时间>/probe.stdout.txt -Algorithm SHA256
```

重点查看：

- `/proc/cmdline`：启动参数和内存范围
- `/proc/meminfo`、`/proc/iomem`：DRAM 与保留区
- `/proc/modules`、`/proc/devices`：驱动和主设备号
- `/dev/stream*`、`/dev/dmac`、`/dev/uipc`、`/dev/dmm*` 等节点
- `/setting/mode/dmode`、`/setting/updater/mode` 是否可读

节点存在只能证明节点存在，不能证明节点能输出 Bayer RAW。

## 6. 只读基线记录

复制 `experiments/templates/20260901_a6500_readonly/` 到新的实验目录，并填写：

- `setup.md`
- `commands.txt`
- `conclusion.md`

结论只能写成：`已证实 / 高可信推测 / 未证实 / 否定`。本轮没有 Bayer dump 时，RAW 结论必须保持 `未证实`。

## 7. 后续运行时读取门槛

只有满足以下条件，才另行设计运行时读取实验：

- 只读输出已归档且可重复获取。
- `probe.stderr.txt` 没有未解释的写入或权限副作用。
- 已确认 root shell、实际 DRAM 范围和可用设备节点。
- 已确定实验停止条件和恢复方案。

后续候选线索来自离线固件：

- `sa_func_DUALREC_BAYER_acquire/release/start`
- `Stage_DualRec.cpp`
- `Stage_DfeRawTrans`
- `Stage_DfeRawTransSnrBranch`
- `RawHsize`、`RawHofs`、`YcHsize`、`YcVsize`
- α6500 独有的 `AllocDfeMemForDfe2Pass`、`SetSyncParamRawBuffering`、`ringBufferWrapper`

这些只是候选入口，不是已经确认的地址，也不授权当前阶段主动调用。

## 8. RAW 验收标准（后续阶段）

只有同一候选数据同时满足以下条件，才能把结论升级为“已证实抓到 RAW”：

- 不同画面导致数据稳定变化。
- ISO、快门、光圈变化导致数值分布符合曝光变化。
- 能识别 RGGB、GRBG、GBRG 或 BGGR pattern。
- 能正确解析 8/10/12/14-bit 及 packing、stride。
- Debayer 后图像内容合理。
- 连续抓取时帧间有稳定时序。

任一条件失败，结论降级为“未证实”。

**协议版本**：2026-09-01  
**基线脚本**：`scripts/probe_readonly.sh`、`scripts/capture_readonly_probe.ps1`  
**前置清单**：`docs/10_readonly_preflight.md`
