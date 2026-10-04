# GPT-SOL -> DeepSeek 研究交接（2026-09-05）

## 目标与硬边界

研究目标仍是：在不刷写、不修改相机固件的前提下，判断 α6500 是否存在可访问的高位深 Bayer RAW 视频通路，并按 3K/10-bit/24-25fps 优先级推进。

当前阶段重新回到：**离线资料与固件静态分析**。

禁止事项：

- 不连接、操作或修改相机状态
- 不执行 `/dev/mem`、`ioctl`、`mmap`、RAM patch
- 不写 `/setting`、SD 卡或任何相机分区
- 不加载/卸载模块
- 不修改 bootloader、DFE 固件或永久固件

## 当前事实

### 已证实

1. α6500 V1.06 与 α6300 V2.01 固件已获取、解包并建立模块索引。
2. 两版固件有大量同构代码，均包含 DualRec/Bayer/RAW 相关字符串和函数。
3. α6500 含 `AllocDfeMemForDfe2Pass`、`SetSyncParamRawBuffering`、`ringBufferWrapper`、`RESOURCE_IMAGER0_STORE_RAW` 等静态线索。
4. α6500 存在 `CAMERA_SCN_EXTERNAL_RAW_RECORD.so`，含 RAW external output 的 on/off/acquire/release 命令协议；这更像静态 RAW/外部输出路径线索，不等于 RAW 视频已可用。
5. `GetRawUnitTypeBase_Normal` 静态返回的候选 DMM 类型包括 `0x236`、`0x1df`、`0x23e`、`0x2b3`。
6. 过去的实机只读会话确认了 1GB DRAM、DMM procfs、stream/stream2/dmac 等节点存在；这些只是运行时环境证据。
7. 过去的实机实验曾观察到 `0x1df` 瞬态分配约 48MB，并能从相机读出一段数据；这只证明单元分配和读取链路，不证明读取内容是 Bayer 像素。

### 不得当作结论

1. `0x1df` 单元类型不等于真实 RAW 像素缓冲。
2. `w=3000`、u16 平滑、2 行周期、`0x5555` 等旧分析结果不能单独证明 Bayer、位深或测试图案。
3. `RGM0/RGM1/RC0/RC1` 的场景标签和抓取时序没有独立日志证明，不能把它们写成“全黑/亮画面/ISO 对照”的确定事实。
4. 目前没有已证实的 10-bit Bayer 视频输出、连续帧时序、3K/25fps 数据流或 50-70MB/s 写入结果。
5. Movie 期间的 `0x321/0x311/0x2d7/0x8125b/0x2bd` 只能称为录像态候选缓冲；在已测试解释下未确认是像素帧，但不能据此否定整个 RAW 路径。

## 工作目录纪律

原始计划指定 `<workspace>`。当前任务可能运行在：

`<workspace>`

切换模型前必须确认当前目录。不要在两个目录分别产生结论；先比较 `git status` 和关键文件哈希，选一个 canonical workspace，再把修改集中到那里。

当前 worktree 已有 `docs/17_runtime_movie_dump.md`、`docs/18_runtime_raw_1df.md`、`docs/19_runtime_raw_controls.md`，但缺少旧目录中的部分 `docs/13-16` 副本。缺少的文件不能被默认为当前工作区证据。

## GPT-SOL 当前任务

1. 审计并修正 `docs/07_conclusion_matrix.md`、`docs/17-19`：把“抓到 RAW”降为“观察到 RAW 候选单元分配”，删除没有独立证据的场景标签和过强结论。
2. 建立 `docs/evidence_ledger.tsv` 或 JSON：每条结论记录来源文件、命令/地址、原始输出、证据等级、是否可复现。
3. 静态追踪 `GetRawUnitTypeBase_Normal` 的全部 caller，确认 mode/state 到 unit type 的映射，不只看函数名。
4. 静态追踪 `FUN_002c2088` 及其后续字段 `+0x5208`、`+0x5598`、`+0x559c`、`+0x55a0` 的用途，区分分配、DMA 目标、元数据和释放。
5. 反查 `Stage_DfeRawTrans`、`p_raw_out_dmm_info`、`dmm_info_raw`、`AllocDfeMemForDfe2Pass`、`SetSyncParamRawBuffering` 的调用图和结构体字段。
6. 分析 `CAMERA_SCN_EXTERNAL_RAW_RECORD.so` 的调用者、消息接收端、实际输出设备和 buffer 归属；只做静态分析。
7. 对比 `libmpr.so` 的 `SetRecVideoBitDepth`、RAW parse、SDI raw resolution 与 Movie format 参数，确认它们是否只是播放/外部录制接口。
8. 写脚本时使用动态字段解析和结构化输出，禁止硬编码某次运行的物理地址。

GPT-SOL 的交付门槛：

- 一张清理后的候选路径图
- 一张 unit type -> caller -> DMM allocator -> DMA target -> consumer 表
- 一份“已证实/高可信推测/未证实/否定”矩阵
- 所有修改文件和可复现命令
- 明确列出不能从静态资料推出的事项

## DeepSeek 后续任务

切回 DeepSeek 后，只执行以下离线任务：

1. 阅读本文件、`goal-objective.md`、`README.md`、`docs/02_static_analysis.md`、`docs/07_conclusion_matrix.md`、`docs/08_a6300_a6500_comparison.md`、`docs/12_candidate_runtime_map.md`、`docs/17-19`。
2. 独立复核 GPT-SOL 的 unit type/caller/DMA 表，不接受未经反汇编或原始输出支持的结论。
3. 对 α6500 和 α6300 的 `av-cam.bin`、`libObj.so`、`libmpr.so`、RAW scenario 做函数/XREF 对照，输出 TSV/JSON。
4. 重点找真实的 stride、pixel packing、buffer ownership、frame counter 和 producer/consumer 关系。
5. 检查 `CAMERA_SCN_EXTERNAL_RAW_RECORD.so` 是否有明确的 USB/SD 输出路径，以及是否只支持静态外部 RAW。
6. 运行现有离线脚本和单元测试；失败时修脚本，不修改相机。
7. 输出一份独立审计报告，指出 GPT-SOL 的每个过度推断。

DeepSeek 禁止：

- 不要求用户重新录像或按快门
- 不运行 PMCA、Zadig、服务模式、ADB、telnet
- 不读取/写入相机内存或 SD
- 不把“字符串存在”写成“功能已实现”

## 后续实验门槛

只有静态分析确认了候选 producer、buffer ownership、stride/packing 线索，并且准备好完整可恢复方案后，才讨论运行时只读实验。

运行时实验仍按：

离线分析 -> 只读 -> 运行时读取 -> RAM patch -> 可恢复实验 -> 永久固件修改

永久固件修改不是当前目标。
