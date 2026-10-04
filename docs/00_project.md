# 项目定义与分级标准

## 目标

- 验证 α6500 视频链路中是否存在可访问的 Sensor Bayer RAW 数据通路。
- 若能获得 RAW：先验证一帧真实 Bayer 数据（640x480 / 1fps / 8-12bit 即算成功），再逐步推进到 3K/10-bit/24-25fps，并以轻量预测+熵编码压缩到 50-70 MB/s。
- 若不能获得 RAW：再评估 10-bit Log / 10-bit 4:2:2 视频通路。
- 30fps 非硬性要求；10-bit、≥3K 有效画质、低 Rolling Shutter、少裁切优先。

## 证据分级

- 已证实：有可复现实验/可交叉验证的确定性证据。
- 高可信推测：多个独立线索指向同一结论，但缺最终实验验证。
- 未证实：有候选线索，但证据不足。
- 否定：实验或权威资料证明不成立。

## 第一阶段范围（当前）

只做离线工作：公开资料整理、固件获取与解包、模块索引、静态逆向分析、工具脚本。
不接触相机，不刷机，不改写相机固件。

## 当前进度（2026-08-29）

- 已完成：α6500 Ver.1.06 固件获取/解包、模块索引、Ghidra 分析、DFE/DualRec 通路定位、AutoDualRec 调度与 10 张上限确认、结论矩阵。
- 已完成：`tools/` 下的 unpack/Bayer/debayer/压缩/Ghidra 脚本，自测 8/8 通过。
- 未完成：真实 Bayer buffer 验证、`SET_MOVIE_FORMAT` handler、4K25/4K30 sensor 寄存器映射、AutoDualRec 间隔秒数。
- 当前阻塞：QEMU 完整 α6500 系统启动未成功（见 `experiments/emulated/README.md`）；Loader2/3 启动链缺少可用的 boot1/boot5 解密镜像（OpenMemories-CI 固件由 GitHub Secret `FIRMWARE_KEY` 加密），下一步需真机只读、数据线，或可用的解密 boot/dump。

## 当前进度（2026-08-30）

- 新增：α6300 Ver.2.01 固件获取/解包，与 α6500 进行同构性对比，产出 `docs/08_a6300_a6500_comparison.md`。
- 新增：α6500 只读运行时实验协议 `docs/09_runtime_protocol_a6500.md`。
- 更新结论矩阵 `docs/07_conclusion_matrix.md`，新增 12 项对比结论。


## 当前进度（2026-09-01）

- 数据线已到，已准备相机侧只读探测脚本 `scripts/probe_readonly.sh`。
- 新增电脑侧 ADB 归档脚本 `scripts/capture_readonly_probe.ps1`。
- 新增连接前边界清单 `docs/10_readonly_preflight.md`、PMCA USB 路线 `docs/11_pmca_usb_shell.md` 和实验模板 `experiments/templates/20260901_a6500_readonly/`。
- 第一轮仍未连接相机，未执行运行时读取、RAM patch 或固件写入。

## 当前进度（2026-09-05）

- canonical workspace 已确定为 `<workspace>`；α6500 V1.06 的真实解包二进制和 α6300 对照资料均以此目录为准。
- 新增 `docs/21_static_audit_20260905.md`：重新审计 RAW unit selector、DMM manager、DFE 2-pass、External RAW scenario、stream2、录像位深/RAW parse/SDI RAW 接口。
- 新增 `docs/22_dfe_raw_transfer_audit_20260905.md`：通过 Ghidra 完整函数导出，确认 `FUN_0028d388` 会读取 RAW 管理字段并建立下游描述符；进一步确认 `FUN_006859ec` 是复制函数，`FUN_006a686a/FUN_006a687e` 是 setter/getter，不是已确认的 DMA 发起器。
- 新增 `docs/evidence_ledger.tsv`、`analysis_out/static_audit_20260905.json`，记录输入文件哈希、反汇编产物哈希、证据等级和限制条件。
- 新增 `tools/static_audit.py`、`tools/avcam_range.py`，用于生成结构化审计和裸 ARM 指令范围。
- 当前最强结论：`unit type -> DMM allocator -> Stage_DfeRawTrans -> descriptor` 的静态字段流已闭合到描述符层；真实 DMA target、Movie producer、consumer、位深/packing、连续帧仍未证实。
- 之前的 Movie 大缓冲和 `0x1df` 读取结果已降级：只证明候选分配/读取或录像态活动，不证明 Bayer 像素；未开始 RAM patch 或永久固件修改。

### 2026-09-06 Stage_DfeRawTrans 调用链

已确认事件分派器、共享处理函数、对齐大小计算和描述符提交边界；新增 docs/23_stage_consumer_audit_20260906.md 和 nalysis_out/static_audit_20260906.json。仍然未确认 FUN_00743b52 内部动作、DMA target、Bayer pattern 和 Movie 连续 producer。


### 2026-09-06 内核驱动层

新增 docs/24_kernel_driver_audit_20260906.md：DMM unit 表、extent 元数据和 XDMAC 硬件写入已确认；DMM→DMAC 调用关系和最终 DMA target 仍未证实。

### 2026-09-06 离线目标与 MPR DMAC 层

- 新增 `docs/25_offline_target_plan.md`：明确离线阶段目标、完成标准和后续只读实验中仍不能替代的验证项。
- 新增 `docs/26_mpr_dmac_audit_20260906.md`：确认 `libmpr.so` 打开 `/dev/dmac`、构建描述符、提交 ioctl、等待完成，且 MemInfo 可按 DMM unit handle 查询 extent。
- 新增工具 `tools/elf_reloc_disasm.py`：解析 ET_REL/ET_DYN 的重定位并标注调用符号。
- 新增工具 `tools/mpr_area_map.py`：从静态 `.data` 提取 MPR area type/label，确认 `Still Stream RAW Main` 为 area type `0x53`。
- 结论调整：DMM 与 DMAC 不再是两条孤立线索；已确认 MPR 库存在 DMAC 用户层，但 `Still Stream RAW Main` 和 `Stage_DfeRawTrans` 是否消费这条路径仍未证实。

### 2026-09-06 晚 DFE->HDMAC 闭合

- 新增 `docs/27_dfe_hdmac_chain_closed_20260906.md`。
- 已证实 `FUN_0028d388 (Stage_DfeRawTrans) -> FUN_0028c514 -> FUN_0072d4ce/d558 -> FUN_0072d226 -> FUN_0072dd40 -> FUN_00482180 -> FUN_0068db2c -> FUN_001d9554`。
- 最终 `FUN_001d9554` 直接调用 DFE HDMAC MMIO 辅助函数，因此静态链已经到达寄存器级目标。
- 仍未证实：HDMAC 传输内容是否为 Bayer、位深、packing、连续帧时序。

### 2026-09-06 离线目标修正

- 新增 `docs/32_offline_state_audit_20260906.md`，修正三个误判：
  - `0x23a` 的已验证调用者是 `PlayJpegThum::CopyReadStillStream` 和 `PlayStill::CopyReadStillStream`，属于播放/回读，不构成 Movie RAW 拍摄证据。
  - `FUN_005c4080` / `FUN_00366ea4` 属于 `Mp4MovieWriterFilter` / `DubPlayRecToMp4`；MP4 Mux `/dev/dmac` 是通用输出桥，不是 RAW 主路径。
  - `0x1df` 在 `FUN_002c1b78` 中是默认/回退 unit，不能单凭它代表 Movie RAW。
- 下一目标改为完成 `context+0x1f0` 状态到 capture 流程的映射，并建立 `state -> unit -> DMM handle -> downstream` 矩阵。
- 新增 `docs/33_current_goal_20260906.md`，把当前目标、已完成项、未完成项和停手条件固定下来。
