# 当前离线目标（2026-09-06 夜间）

## 目标

完成一条可复核的静态证据链，或明确给出否定结论：

```text
CapMode / CaptureManager
  -> context + 0x1f0
  -> FUN_002c1ab0
  -> RAW DMM unit type
  -> FUN_002c2088 / DMM allocation
  -> Stage_DfeRawTrans
  -> downstream DFE / DMA / consumer
```

软性目标：把 CapMode 编号翻译成可读的捕获模式名称，并生成“状态 -> unit -> handle 槽位 -> 下游函数”矩阵。

## 已完成（2026-09-06）

1. `0x23a` / `Still Stream RAW Main` 已降级为播放/回读路径。
2. `Mp4MovieWriterFilter` / `DubPlayRecToMp4` / MP4 Mux `/dev/dmac` 已从 RAW 主候选移除。
3. `context + 0x1f0` 已确认是 CaptureManager 的 CapMode，并由 `FUN_002808e0` 初始化。
4. 已导出 `FUN_0027f57c` 的 CapMode 字表、`FUN_0027f668` 的模式字节表和 `FUN_0027f5ec` 的校验函数。
5. 已确认 `FUN_002c1ab0` 根据 CapMode 选择 `0x236 / 0x1df / 0x23e / 0x2b3`。
6. 已确认 `FUN_002c1b78` 把 `0x1df` 作为多个 CapMode 的默认/回退值。

## 未完成/验收线

- 未完成：CapMode 编号到模式名称的静态映射。
- 未完成：`Stage_DfeRawTrans` 下游描述符到 DFE HDMAC 源地址/目标地址的字段级证明。
- 未完成：真实 Bayer、位深、packing、stride、帧时序验证。
- 不把 `0x1df` 当成已证实 RAW 帧。
- 不进入 RAM patch、不写 SD、不写相机、不修改固件。

## 下一步行动

1. 继续搜索 `CaptureManager_ModeInfo.cpp` / `CaptureManager_FunctionIF.cpp` 附近的模式枚举和条件分支。
2. 搜索 `FUN_0027f57c` / `FUN_0027f668` 结果的消费者，确认它们是否控制 RAW buffer、DualRec、DFE 2-pass 或 Movie 通路。
3. 若静态无法完成，则把结论固定为“CapMode 枚举需要运行时只读观察”，并停止当前分支。

## 关键文件

- `docs/32_offline_state_audit_20260906.md`
- `analysis_out/avcam_capmode_tables_20260906.json`
- `analysis_out/avcam_capmode_string_refs_20260906.tsv`
- `analysis_out/avcam_state_helpers2_20260906.txt`
- `analysis_out/static_audit_20260906_night.json`
