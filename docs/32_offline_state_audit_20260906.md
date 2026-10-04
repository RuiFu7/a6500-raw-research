# 离线状态修正与下一阶段目标（2026-09-06）

## 结论摘要

本轮离线分析把“MPR `0x23a` / `Still Stream RAW Main` 是最有价值的运行时候选”这一判断降低为：

**它是回放/缩略图读取链路，不是已经证明的拍摄 RAW 视频通路。**

同时把 MP4 Mux 的 `/dev/dmac` 路径从主目标中移除。它属于通用 MP4 输出 / 复制到 MP4 链路，和 Sensor Bayer RAW 没有可复核的字段关联。

## 一、已证实：`0x23a` 的调用者属于播放链路

`libmpr.so` 中 `FUN_006c8ca0(0x23a, 0xffffffff, ...)` 的已验证调用者：

| 地址 | 函数/符号 | 语义 |
| --- | --- | --- |
| `00387d68` | `PlayJpegThum::CopyReadStillStream` | JPEG 缩略图读取 |
| `003a7e70` | `PlayStill::CopyReadStillStream` | Still 播放/回读 |

这两个函数名和字符串均来自 MPR 播放库；`CopyReadStillStream` 的含义是“复制读取 Still 流”，不是“从 Sensor 拍摄 RAW 视频”。

`FUN_006c8ca0` 还有两个通用调用者：

| 地址 | 函数 | 语义 |
| --- | --- | --- |
| `006c5980` | `FUN_006c5980` | 调试扫描 `unit 0x1e7..0x201`，读取后释放 |
| `006c606a` | 调试/测试入口 | 从参数字段选择 unit 并分配 |

因此 `DMM + stream2 + mmap` 是通用内存映射基础设施。不能因为 `0x23a` 的静态表标签包含 `RAW Main`，就认为它正在承载拍摄 Bayer 数据。

## 二、已证实：MP4 路径不是 RAW 主链路

`FUN_005c4080` 的 vtable/RTTI 是 `Mp4MovieWriterFilter`。

`FUN_00552390` 的源码字符串与日志是 `MP4 MUX InitParam`，其功能和地址：

- `linkListAreaAdr`
- `linkListAreaSize`
- `linkListAreaAdrOffset`
- `/dev/dmac`

`FUN_00366dc8` 构造 `Mp4MovieWriterFilter`；`FUN_00366ea4` 从外层对象 `+0x74` 读取参数并构造 MP4 Mux。该外层对象的 RTTI 名称是 `DubPlayRecToMp4`，即复制到 MP4 的处理对象，不是相机 RAW 拍摄对象。

因此把 `0x53` 当作“Still Stream RAW Main 的 MPR area ID”与 MP4 Mux 中的 `0x53` 合并是错误。MP4 中的 `0x53` 只是日志字段/对象字段索引。

## 三、已证实：DMM area 表和 MPR DMAC 只能作为通用桥

`FUN_006c8ca0` 的确切路径：

```text
unit type
  -> FUN_006cb85c
  -> FUN_006cb498 -> DMM message
  -> handle / extent
  -> FUN_006c8a2c
  -> FUN_006c5658
  -> FUN_006c5484
  -> FUN_006c7424
  -> /dev/stream2 ioctl + mmap
```

该路径没有调用 `/dev/dmac`。MPR 库中确实存在 `/dev/dmac` 路径，但主调用链是 MP4 Mux 的通用内存区 DMA 桥。当前不能把二者接成一条 RAW 数据链。

## 四、已证实：`0x1df` 是多个状态的回退 unit，不能单独代表 Movie

`FUN_002c1ab0` 的状态选择逻辑：

- 多数状态返回 `0x1df` 或 `0x236`；
- `state=0x1b` 返回 `0x23e`；
- `state=9` 根据其他字段返回 `0x1df / 0x236 / 0x2b3`；
- `state=10` 根据 `+0x1e8` 和全局字段返回 `0x1df / 0x236`。

`FUN_002c1b78` 进一步显示 `0x1df` 是默认/回退 unit：

- 很多状态直接返回 `0x1df`；
- `state=5` 时若 `+0x70 == 1` 返回 `0x2f5`，否则 `0x1df`；
- `state=7` 时按 `+0x5ae8` 返回 `0x12d / 0x132`。

所以不能把运行时曾经读到的 `0x1df` 直接解释为“Movie RAW buffer”。它可能是静拍、DualRec、调试、其他状态共用的 DMM RAW/DFE 缓冲。

## 五、当前结论矩阵修正

| 假设 | 等级 |
| --- | --- |
| `PlayJpegThum::CopyReadStillStream` 使用 DMM unit `0x23a` | 已证实 |
| `PlayStill::CopyReadStillStream` 使用 DMM unit `0x23a` | 已证实 |
| `0x23a` 已经证明是拍摄 RAW 视频源 | 否定（当前证据） |
| `Still Stream RAW Main` area ID `0x53` 等于 DMM unit `0x23a` | 未证实 |
| MP4 Mux 使用 `/dev/dmac` | 已证实 |
| MP4 Mux 的 DMA 缓冲区已经证明是 Sensor Bayer RAW | 否定（当前证据） |
| `FUN_005c4080` 是 `Mp4MovieWriterFilter` | 已证实 |
| `FUN_00366ea4` 属于 `DubPlayRecToMp4` | 已证实 |
| `Stage_DfeRawTrans` 的 `0x1df` 是唯一 Movie RAW unit | 否定（当前证据） |
| DMM / stream2 / `/dev/dmac` 是通用基础设施 | 已证实（静态） |

## 六、下一阶段目标（可验收）

1. 完成 `context+0x1f0` 状态枚举的静态映射，至少确认 `5 / 6 / 7 / 9 / 10 / 0x15 / 0x1b` 分别对应哪类捕获流程。
2. 对 `FUN_002c1d08` / `FUN_002c1f38` 返回的 unit 表建立“状态 -> unit -> DMM handle 槽位 -> 下游函数”矩阵。
3. 确认 `0x1df` 出现在哪些状态；若它被 Movie 捕获状态使用，则保留为运行时候选；否则降级为“共用 DFE 缓冲”。
4. 不再把 `0x23a`、`Mp4MovieWriterFilter`、`DubPlayRecToMp4`、MP4 Mux DMAC 作为 RAW 主候选。
5. 输出一个“可读但还未证明内容”的候选清单，并明确每个候选的失败判据：未能识别 Bayer、无法证明帧间更新、尺寸/stride 不自洽、模式控制不改变数据分布。

## 七、证据文件

- `analysis_out/mpr_023a_full_path_20260906.txt`
- `analysis_out/mpr_unknown_area_range_20260906.txt`
- `analysis_out/mpr_playback_raw_refs_20260906.tsv`
- `analysis_out/mpr_mp4_object_factory_20260906.txt`
- `analysis_out/mpr_dub_vtable_words_20260906.txt`
- `analysis_out/avcam_raw_caller_states_20260906.txt`
- `analysis_out/avcam_unit_selectors_20260906.txt`
- `analysis_out/avcam_raw_state_callers_20260906.txt`
- `analysis_out/avcam_super_slow_range_20260906.txt`
- `analysis_out/avcam_super_slow_data_words_20260906.txt`
- `analysis_out/avcam_state_writer_context_20260906.txt`
- `analysis_out/avcam_state_helpers2_20260906.txt`
- `analysis_out/avcam_settings_lookup_20260906.txt`
- `analysis_out/avcam_capmode_string_refs_20260906.tsv`
- `analysis_out/avcam_capmode_tables_20260906.json`

## 八、新增：`context + 0x1f0` 是 CaptureManager 的 CapMode

`FUN_002808e0` 是 `CaptureManager.cpp` 相关的 CaptureManager 初始化函数，它从运行时配置表读取 `context + 0x1f0`，并把该值传给 `FUN_002c1ab0`、`FUN_002c1b78` 等 RAW unit selector。后续 `FUN_002c1ab0` 再根据该 CapMode 选择 `0x236 / 0x1df / 0x23e / 0x2b3`。

已确认两个静态表：

`FUN_0027f57c` 索引表（32/33 项，表基址 `Ghidra 0x7a39b4`）：

| CapMode | 表值 |
| --- | --- |
| `1` | `1` |
| `0x13` | `1` |
| `0x1a` | `1` |
| `0x1f` | `1` |
| `0x20` | `1` |
| `0x21` | `1` |
| 其余 | `0` |

`FUN_0027f668` 字节表（状态 8..27，表基址 `Ghidra 0x8b8bdb`，位于 `CaptureManager.cpp` 字符串前）：

| CapMode | 表值 |
| --- | --- |
| `8` | `1` |
| `9` | `1` |
| `10` | `1` |
| `0x14` | `1` |
| `0x18` | `1` |
| `0x1b` | `1` |
| 其余 | `0` |

这两张表证明：`0x1f0` 不是随机对象字段，而是经过 CaptureManager 初始化的 CapMode；`0x1f0` 的值决定 RAW unit 选择。当前仍缺少将这些 CapMode 枚举值翻译成“静拍 / Movie / DualRec / Super Slow Motion”的静态证据，因为配置表在 BSS/运行时区域，不能从固件镜像直接读出常量。

## 九、当前最值得保留的静态候选

运行时候选不再按“名字像 RAW”排序，而是按“是否被 CaptureManager + DMM 链路实际选中”排序：

1. `0x1df`：在多个 CapMode 下作为 RAW unit 回退值，已有 DMM 分配代码和运行时读取记录；仍无 Bayer 内容验证。
2. `0x236`：默认 RAW unit，尚未单独验证。
3. `0x23e / 0x2b3`：仅在部分 CapMode 下出现，当前没有运行时候选优先级。
4. `0x23a`：已降级为播放 Still 回读路径，不再作为首选。
5. MP4 `/dev/dmac`：已降级为通用输出桥，不再作为首选。

下一轮离线优先任务仍是给 CapMode 编号找到可追溯的枚举名称或映射函数。
