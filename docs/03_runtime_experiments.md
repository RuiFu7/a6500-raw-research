# 运行时实验协议（后续阶段，不进入第一阶段）

## 执行阶梯

1. 离线分析（已完成第一阶段）
2. 只读
3. 运行时读取
4. RAM patch
5. 可恢复实验
6. 最后才考虑永久固件修改

只有上一级成功且具备完整备份/恢复方案时才进入下一级。永久固件修改不是目标。

## 前置条件

- 专门的 SD 卡（实验专用，不保存相机正常照片）。
- 完整固件备份与恢复方法（Sony 官方 updater 可恢复原厂，或 PMCA-RE `serviceshell`/`updatershell` 的 dump 流程）。
- 相机连接方式：先 WiFi telnet/ADB（OpenMemories Tweak），或 PMCA-RE USB service shell；两者均为公开既有能力。
- 记录基线：相机版本 `1.06`（与本次分析固件一致最理想）。

## 第一个无风险实验（只读）

目标：在不修改任何相机状态的前提下，判断能否观察到疑似 Bayer/RAW 内存区。

1. 在固定画面（例如均匀光照的色卡）下，通过 root shell 只读 dump 候选内存区（大小 1-16MB，地址候选来自 `02_static_analysis.md` 的入口函数与 DFE/RING BUFFER 相关代码）。
2. 用 `tools/raw_analyze.py` 分析 dump：
   - 直方图/数值分布、Bayer 周期自相关、位深猜测（8/10/12/14bit、packed/unpacked）
   - 尝试常见 Bayer pattern（RGGB/GRBG/GBRG/BGGR）与 stride
3. 变更场景（不同画面 / ISO / 快门 / 光圈 / 白平衡）重复 dump，比较变化区域。
4. 判定规则（严格）：
   - 只有数据随画面变化、可识别 Bayer pattern、可正确 unpack、Debayer 后得到合理图像、帧间有稳定时序，才标记“已证实抓到 RAW”。
   - ISO/快门变化时 RAW 应表现为增益/积分时间变化而非完全烘焙成最终图像。

## 后续只读实验

- 视频模式（Movie/LiveView）下扫描 DRAM 中连续大块缓冲，寻找随帧率刷新的候选 RAW 帧缓冲。
- 对比 4K24/25 与 4K30 的 readout 参数（通过 Sensor 寄存器读取或行为差异）。
- 测量 SD 卡实际持续写入带宽（50-70 MB/s 目标）与温度限制。

## 进入 RAM patch 的条件

- 已确认至少一个“未证实→高可信”的 RAW buffer 候选；
- 已建立该地址对应 DMA/缓冲管理的完整理解；
- 已备份全部关键分区；
- 实验可恢复（重启即还原，或一条命令还原）。

## 记录格式

每个实验写入 `experiments/<date>_<id>/`：
- `setup.txt`（相机设置、场景、SD 卡、固件版本）
- `commands.txt`（所用只读命令与时间戳）
- `dump/*.bin`（原始 dump，可选保留或只留 hash）
- `report.json`（`tools/raw_analyze.py` 输出）
- `conclusion.md`（分级结论：已证实/高可信推测/未证实/否定）

## 已确认的运行时入口（离线证据）

| 入口 | 证据 | 用法 |
| --- | --- | --- |
| appFw gdb/gdbserver | `change_mode.sh` 的 `3g` / `3s` 模式 | 写入 `/setting/mode/dmode` 后重启；用于对 appFw（AV 固件用户态）断点调试，进入前需备份 `/setting` |
| telnet/adb | OpenMemories Tweak + `usbg_adb.ko` | 相机 WiFi 下 root shell / adb connect |
| SD / 记忆棒节点 | `common.src` | `/dev/mmca1`、`/dev/ms1` |
| Android 系统分区 | `s_start_android.sh` | `/dev/dnflasha16`（ext2, ro）、`/dev/nflasha17`（data） |
| 内存大小线索 | `s_start_android.sh` cgroup `113M` | Android 侧上限 113MB；真实 DRAM 总量仍待运行时 `/proc/meminfo` 确认 |

注意：`change_mode.sh` 属于可逆的系统设置（改 `/setting` 文件），仍应按阶梯先备份再使用；gdb 模式用于只读观察，不修改固件。

## 只读探测脚本

`scripts/probe_readonly.sh`：相机侧 root shell 下运行，收集 `/proc/iomem`、`/proc/meminfo`、`/proc/modules`、`/dev`、`/sys` 设备节点、`dmesg`、启动模式文件与 Android 属性，全程不写相机状态。输出重定向到电脑端日志即可。

## 2026-09-01 实机只读基线

实验目录：`experiments/readonly/20260901_a6500_baseline/`。

已通过 PMCA 临时进入 service shell，读取到真实 α6500 V1.06 运行环境：

- `mem=1024M@0x80000000@0`，`/proc/iomem` 的 System RAM 为 `0x80000000-0xbfffffff`。
- Linux `3.0.27_nl-rt106+`，架构 `armv7l`。
- `/proc/modules` 确认 `dmm`、`stream`、`stream2`、`dmac`、`osal_uipc`、`ldec`、`nand`、`hdmi`、`usbg_sen` 等运行时模块。
- `/dev/stream`、`/dev/stream2`、`/dev/dmac`、`/dev/uipc`、`/dev/ldec`、`/dev/hdmi`、`/dev/dnflasha16` 等节点存在。

结论：**已证实**真实运行时环境与离线链路线索相符；**未证实**任何具体 Bayer buffer 或 RAW 像素输出。本轮未访问 `/dev/mem`、未读取未知 MMIO、未触发 DualRec、未发送 `SET_*`、未加载模块、未写入相机。
