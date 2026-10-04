# α6500 候选运行时入口映射

本文件只描述离线证据如何指导后续只读观察。静态字符串地址是 `av-cam.bin` 文件偏移/代码地址锚点，不是可直接读取的物理 RAM 地址。

## 1. 已确认的静态锚点

| 层 | 静态锚点 | 证据 | 运行时用途 |
| --- | --- | --- | --- |
| DualRec 参数 | `RawHsize`、`RawHofs`、`YcHsize`、`YcVsize` | `firmware/manifests/ghidra_dualrec_xrefs.tsv` | 识别 RAW/YC 窗口字段的变化 |
| SA Bayer | `sa_func_DUALREC_BAYER_acquire/release/exit` | `firmware/manifests/ghidra_dualrec_xrefs.tsv` | 过滤 Bayer SA 阶段日志/调用 |
| SA mailbox | `DUALREC_BAYER_start_mbx.cha_mbx0..3` | 同上 | 记录启动消息四个参数，不主动构造消息 |
| DualRec 阶段 | `Stage_DualRec.cpp`、`StartSA_Bayer` | 同上 | 识别抓拍阶段边界 |
| DFE 传输 | `Stage_DfeRawTrans`、`Stage_DfeRawTransSnrBranch` | `firmware/manifests/ghidra_dfe_raw_xrefs.tsv` | 识别 RAW 传输阶段 |
| DFE 输出对象 | `p_raw_out_dmm_info`、`dmm_info_raw` | 同上 | 追踪输出描述符和尺寸/偏移元数据 |
| α6500 连续资源 | `AllocDfeMemForDfe2Pass`、`SetSyncParamRawBuffering`、`ringBufferWrapper RawSize==0` | `firmware/manifests/a6300_a6500_comparison.json` | 作为 α6500 特有连续缓冲线索 |
| Movie 参数 | `PARAMID_RAW_OUTPUT_MODE`、`PARAMID_MOVIE_RAW_SIZE` | 同一 JSON 的 `libObj.so` markers | 确认 Movie 参数结构，不等于 RAW 已启用 |

## 2. 推荐观察顺序

### 阶段 A：连接和基线

只读取并归档：

```sh
uname -a
cat /proc/cmdline
cat /proc/meminfo
cat /proc/iomem
cat /proc/modules
cat /proc/devices
ls -la /dev
ls -la /sys/class
```

记录文件哈希。没有完成这一步，不进入候选内存读取。

### 阶段 B：运行时日志和节点确认

只读取：

- `/proc/modules` 中 DFE、DMM、stream、DMA 相关模块是否实际加载。
- `/proc/devices` 中主设备号是否与节点对应。
- `/dev/stream*`、`/dev/dmac`、`/dev/dmm*`、`/dev/uipc` 是否存在。
- `dmesg` 中是否出现 `DualRec`、`DfeRawTrans`、`RawHsize` 或 DFE 错误。

节点存在、模块存在或日志出现字符串，都只能升级为“高可信候选”，不能证明像素数据已获取。

### 阶段 C：候选缓冲读取

只有阶段 A/B 通过后，才设计单独的只读读取实验。每次读取必须固定：

- 起始地址和地址来源
- 读取长度
- 读取频率
- 是否跨越保留区
- 停止条件
- 本地输出文件和 SHA256

第一轮建议从小范围、低频率开始；不扫描整个 DRAM，不读取未知 MMIO，不向 `/dev/mem` 写入，不调用 `devmem` 写模式。

## 3. 证据升级规则

| 观察结果 | 结论等级 |
| --- | --- |
| 只有静态字符串/函数名 | 未证实 |
| 运行时出现对应阶段日志或消息，但无像素验证 | 高可信推测 |
| 候选区域在不同画面、ISO、快门下稳定变化 | 高可信推测 |
| 通过 unpack、Bayer pattern、Debayer 且图像合理 | 已证实：获得一帧 Bayer |
| 连续帧有稳定间隔并完成带宽测量 | 已证实：连续数据流 |
| 读取结果固定、全零、明显是 YUV/JPEG 或无法重复 | 否定该候选，不否定整个 RAW 假设 |

## 4. 当前禁止的越级动作

- 不主动发送 `SET_MOVIE_FORMAT` 或 `SET_RAW_EXTERNAL_OUTPUT`。
- 不构造 `DUALREC_BAYER_start_mbx` 消息。
- 不调用 gdb/gdbserver，不做 RAM patch。
- 不加载/卸载驱动，不写 `/setting`，不写固件。

## 5. 证据来源

- `docs/02_static_analysis.md`
- `docs/08_a6300_a6500_comparison.md`
- `firmware/manifests/ghidra_dualrec_xrefs.tsv`
- `firmware/manifests/ghidra_dfe_raw_xrefs.tsv`
- `firmware/manifests/a6300_a6500_comparison.json`
- `scripts/probe_readonly.sh`

**版本**：2026-09-01

## 6. stream2 物理映射通道（2026-09-01 新增）

- 已还原：`libmpr.so` `FUN_006c7424` + `FUN_006c81d0` 用 `ioctl(/dev/stream2, 0xC0047805, {phys,size}[] )` 注册物理表，再 `mmap` 到用户态。
- `stream2.ko` 实现：每进程最多 5 项 `{phys,size}`，mmap 逐段 `remap_pfn_range`。
- 含义：官方存在受控的物理 DRAM 映射路径，可用于后续只读抓取候选缓冲；不属于 `/dev/mem` 裸读。
- 现状：尚未实机执行 ioctl/mmap；是否触发、如何回滚需单独设计。

详见 `docs/13_stream2_dmm_path.md`。

## 7. DFE 资源编号与 2-pass 分配（2026-09-01 新增）

- `FUN_00690242` 模式→DFE 资源编号映射已还原（0x22/0x23/0x24/0x25/0x2a/0x2e/0x2f/0x37/0x38）。
- `AllocDfeMemForDfe2Pass` 以 0x324 调用 DMM 请求构造例程（`FUN_002e7300`），成功后记录句柄/u32。
- 高可信推测：0x324 是 DFE 2-pass RAW 缓冲的 DMM 单元类型，需运行时确认。

详见 `docs/14_dfe_resource_allocation.md`。

## 8. RAW DMM 单元类型（2026-09-01 新增）

- `GetRawUnitTypeBase_Normal`（FUN_002c1ab0）已还原：RAW 主缓冲单元类型为 `0x236/0x1df/0x23e/0x2b3`。
- RAW 内存管理器把句柄写 `+0x5208`、unit_type 写 `+0x5598`、物理信息写 `+0x559c/+0x55a0`。
- 运行时读 `/proc/udm/dmm_units` 查找上述 unit_type，再经 stream2 只读映射。

详见 `docs/15_raw_dmm_unit_types.md`。

## 9. 实机 DMM 分配表基线（2026-09-01 实测）

- `/proc/udm/dmm_info|dmm_units|dmm_extents|dmm_reserve|dmm_rule` 实机可读。
- `dmm_units` 表头含 `address size`；地址位于 0x80000000-0xbfffffff。
- 唯一出现的 RAW 候选 unit type：`0x2b3` extent `0069`，物理 `bde76000`，大小 `0xc000`（48KB）。
- `0x236/0x1df/0x23e` 未在 idle 状态出现，预期在拍摄/DualRec 时动态分配。

记录见 `experiments/readonly/20260901_a6500_dmm_baseline/`。
