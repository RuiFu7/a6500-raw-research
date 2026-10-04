# 相机接入后的 DMM 只读读取协议

> 目标：从 α6500 实机读取 DMM 分配表，定位 RAW/DFE 缓冲的物理地址与大小。
> 全部为只读操作：cat /proc、cat /sys；不写文件、不加载模块、不读 /dev/mem、不触发 ioctl/mmap。

## 1. 背景（离线已确认）

- RAW 主缓冲单元类型：`0x236 / 0x1df / 0x23e / 0x2b3`（见 `docs/15_raw_dmm_unit_types.md`）。
- DMM 分配表：`/proc/udm/dmm_units`（含 `address size` 列）、`/proc/udm/dmm_extents`、`/proc/udm/dmm_info`。
- 物理映射通道：`/dev/stream2` ioctl `0xC0047805` + mmap（见 `docs/13_stream2_dmm_path.md`）。
- a6300 与 a6500 的 dmm.ko procfs 路径完全一致；a6300 av-cam.bin 也含同样的 RAW 单元类型逻辑。

## 2. 前置

1. 相机开机，USB 设为 Mass Storage。
2. 电脑侧 PMCA 进入 service shell（`pmca-console.py serviceshell` → `shell`）。
3. 确认 shell 可用后，只执行下面只读命令。

## 3. 读取命令

进入相机 shell 后执行：

```sh
# 1) DMM 分配表全量
cat /proc/udm/dmm_info
cat /proc/udm/dmm_units
cat /proc/udm/dmm_units2
cat /proc/udm/dmm_extents
cat /proc/udm/dmm_reserve
cat /proc/udm/dmm_rule

# 2) 只看 RAW 相关单元类型（0x236/0x1df/0x23e/0x2b3）
cat /proc/udm/dmm_units | grep -E '236|1df|23e|2b3'
cat /proc/udm/dmm_extents | grep -E '236|1df|23e|2b3'

# 3) 系统/节点确认（只读）
cat /proc/modules | grep dmm
ls -la /dev/stream2 /dev/stream
```

注意：`dmm_units` 表头为 `handle type status alloc open rdv serial relation address size extent(suspend)`，其中 `address` 与 `size` 是定位 RAW 缓冲的关键列。

## 4. 记录

在电脑侧保存：

- `experiments/readonly/<日期>/dmm_info.txt`
- `experiments/readonly/<日期>/dmm_units.txt`
- `experiments/readonly/<日期>/dmm_extents.txt`
- `experiments/readonly/<日期>/dmm_raw_match.txt`（grep 结果）

计算 SHA256，并记录拍摄状态（是否在 Movie/DualRec 模式、ISO/快门等）。

## 5. 判读

- 若 `dmm_units` 中存在 `0x236/0x1df/0x23e/0x2b3` 且 `status` 为有效（非 0/free），记录其 `address` 与 `size`。
- 对比不同场景（静态/录像/触发 DualRec）下这些单元是否出现或变化。
- 找到候选后，下一步再设计 stream2 只读映射（属于运行时读取，需单独确认恢复方案）。

## 6. 禁止项

- 不写 `/proc`、不写 `/setting`、不加载/卸载模块。
- 不执行 `/dev/mem`、`devmem`、`mmap`、`ioctl`。
- 不触发 DualRec、不发送 `SET_*`。
- 任何命令提示写入/报错，立即停止并保留输出。
