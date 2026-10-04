# 结论矩阵（截至 2026-09-06）

等级：`已证实` / `高可信推测` / `未证实` / `否定`。本表只把证据支持到的范围写入结论。

| # | 结论 | 等级 | 关键证据 |
| --- | --- | --- | --- |
| 1 | α6500 官方 V1.06 固件已获取、解包并建立模块索引 | 已证实 | `firmware/raw/Update_ILCE6500V106.exe`、`module_index_v106.json` |
| 2 | α6300 官方 V2.01 固件已获取、解包并建立模块索引 | 已证实 | `firmware/a6300-raw/Update_ILCE6300V201.exe`、`module_index_a6300_v201.csv.json` |
| 3 | α6300/α6500 有 1587 个共同路径、1076 个字节级相同文件 | 已证实 | `firmware/manifests/a6300_a6500_comparison.json` |
| 4 | 两版固件都含 DualRec/Bayer/DFE RAW 相关字符串和代码线索 | 已证实 | `docs/01_public_research.md`、`docs/08_a6300_a6500_comparison.md` |
| 5 | α6500 含 `GetRawUnitTypeBase_Normal` 逻辑，候选 unit type 为 `0x236/0x1df/0x23e/0x2b3` | 已证实 | `ghidra_avcam_rawunit_func.txt` |
| 6 | RAW 内存管理函数会调用 DMM 分配/复用并保存句柄和 DMM 返回字段 | 已证实 | `ghidra_avcam_rawmem_func.txt` |
| 7 | RAW 内存管理函数的直接 caller 为 `0x006b751c`、`0x006b6b86`、`0x002cfb22` | 已证实 | `ghidra_avcam_rawmem_func.txt` |
| 8 | α6500 含 DFE 2-pass 分配函数，并以 `0x324` 构造 DMM 请求 | 已证实 | `ghidra_avcam_dfe_alloc_funcs.txt` |
| 9 | `0x324` 就是可读 Bayer 像素缓冲 | 未证实 | 只有请求参数证据，没有内容/所有权验证 |
| 10 | α6500 含 `SetSyncParamRawBuffering`、`ringBufferWrapper`、`STORE_RAW/TRANS_RAW` 字符串 | 已证实 | `av-cam.bin` 字符串和固件对比索引 |
| 11 | 上述 α6500 独有字符串已经形成可用连续 Movie RAW producer | 未证实 | 尚未闭合函数、DMA 目标、consumer 和帧时序 |
| 12 | External RAW scenario 存在 on/off/acquire/release 消息协议 | 已证实 | `CAMERA_SCN_EXTERNAL_RAW_RECORD.so` ELF 符号/反汇编 |
| 13 | External RAW scenario 自己直接写 USB/SD | 否定 | 场景 ELF 没有直接 `open/write/ioctl/mmap` 导入；可能由下游任务处理 |
| 14 | `libmpr`/`stream2` 存在物理范围注册与 `mmap` 机制 | 已证实（离线） | `ghidra_mpr_stream2_funcs.txt`、`stream2.ko` |
| 15 | `stream2` 映射机制已经定位到 RAW 像素 producer | 未证实 | 仍缺 unit ownership 和 producer 关联 |
| 16 | `MprIf::SetRecVideoBitDepth` 是 10-bit RAW 视频出口 | 未证实 | 当前反汇编显示为录像参数配置链 |
| 17 | `StmCh::rawparse` 是传感器 RAW producer | 未证实 | 当前反汇编显示为 STM/dataflow 解析请求 |
| 18 | `SdiCh::setRawResolution` 是 RAW 内存读取接口 | 未证实 | 当前反汇编显示为 SDI/dataflow 控制请求 |
| 19 | `PlayStill::RawDevelopInfo` 使用 RAW 区域描述符 | 已证实 | `libmpr.so` 符号、日志字段：unitType/handle/phyAddr/offset/virtTopAddr/size |
| 20 | 静态图像 RAW 描述符可直接外推为 Movie RAW producer | 否定 | 所在调用链属于 `PlayStill` |
| 21 | 固件有 4K24/25/30 编码参数表和时钟类型 | 已证实 | `ghidra_4k25_30_xrefs.tsv` |
| 22 | 当前静态资料已证明 4K25/4K30 的 Sensor crop/readout 差异 | 未证实 | 缺少传感器寄存器/row timing/pixel clock 数值 |
| 23 | 录像态大缓冲已通过常见解释验证为 Bayer 帧 | 否定（当前抓取/解释） | `docs/17_runtime_movie_dump.md` |
| 24 | `0x1df` 已通过 Bayer、unpack、debayer 和场景响应验收 | 否定（当前抓取/解释） | `docs/18_runtime_raw_1df.md`、`docs/19_runtime_raw_controls.md` |
| 25 | `0x1df` 动态分配/读取链路曾在实机出现 | 已证实 | DMM 实测和 `docs/18-19` |
| 26 | 当前已获得 10-bit Bayer 视频 | 否定 | 没有通过像素验证 |
| 27 | 当前已获得连续 24/25fps RAW 帧序列 | 否定 | 没有稳定帧间时序和完整帧验证 |
| 28 | 3K/10-bit/25fps 已实测压到 50–70 MB/s | 否定 | 现有压缩结果来自合成数据，不是真实 RAW |
| 29 | α6500 实机约 1GB DRAM、DMM/stream/stream2/dmac 节点可读 | 已证实 | `experiments/readonly/20260901_a6500_baseline/` |
| 30 | 已执行 RAM patch、永久固件修改或写入固件分区 | 否定 | 当前记录没有这些操作 |
| 31 | `FUN_0028d388` 会读取 RAW 管理对象字段并打包到下游传输描述结构 | 已证实 | `analysis_out/ghidra_raw_stage_funcs_full_20260905.txt` |
| 32 | `FUN_006859ec`、`FUN_006a686a`、`FUN_006a687e` 是描述符复制/setter/getter，而非已确认的 DMA 发起器 | 已证实 | `analysis_out/avcam_descriptor_copy_setters_20260905.txt` |
| 33 | `unit type -> allocator -> Stage_DfeRawTrans` 的静态字段流已闭合到描述符层 | 已证实 | `docs/22_dfe_raw_transfer_audit_20260905.md` |
| 34 | 描述符之后的真实 DMA target、producer、consumer 已定位 | 未证实 | 仍缺下游函数语义和硬件寄存器关联 |
| 35 | `FUN_006a4394` 读取 `+0x23` 作为事件键，`FUN_006a43b2`/`FUN_006a44a0` 可进入 `FUN_0028d388` | 已证实 | `analysis_out/ghidra_stage_consumer_funcs_20260906.txt`、`ghidra_dispatch_enum_20260906.txt` |
| 36 | `FUN_00296884` 包含 DFE/RAW 缓冲大小计算：调用 `FUN_0068281e`、按 `6/8` 缩放并对齐 0x80 | 已证实 | `analysis_out/avcam_internal_handlers_20260906.txt`、`avcam_size_helpers_20260906.txt` |
| 37 | `FUN_00298b34` 构造描述符并交给 `FUN_00743b52` | 已证实 | `analysis_out/avcam_internal_handlers_20260906.txt` |
| 38 | `FUN_00743b52` 已确认是硬件 DMA kick 或 MMIO 写 | 未证实 | 只见到软件调用边界，未确认内层动作 |
| 39 | 6/8 乘数已确认是像素位深、bytes-per-pixel 或通道数 | 未证实 | 尚未解析 `FUN_00682796` 返回对象字段语义 |
| 40 | `FUN_00743b52 -> FUN_00743f54 -> FUN_001dd460` 是高层参数/对象 API，不是直接 MMIO 或 DMA kick | 已证实 | `analysis_out/avcam_dfe_core_api_20260906.txt`、`avcam_object_api_20260906.txt` |
| 41 | `FUN_001dd460` 是 DFE 硬件驱动直接写寄存器 | 未证实 | 只看到对象查询、浮点计算和后续 API 调用 |
| 42 | 已找到可验证的 Bayer 像素帧 | 否定 | 当前只找到描述符/参数路径，没有像素验证 |
| 43 | `FUN_001df4f4` 遍历全局对象表并调用 `FUN_00690324` 查找资源 | 已证实 | `analysis_out/avcam_api_expanded_20260906.txt`、`avcam_literal_map_20260906.txt` |
| 44 | 已确认底层最终硬件 DMA target | 未证实 | 回调链和 DFE 硬件 API 尚未追踪到硬件层 |
| 45 | `dmm.ko` 使用 0x188 字节 unit 表并可通过 extent 元数据获得候选物理地址/长度 | 已证实（驱动层） | `analysis_out/dmm_dmm_unit_ctrl_GetUnitInfo_20260906.txt`、`dmm_dmm_unit_ctrl_Open_20260906.txt` |
| 46 | `dmac.ko` 包含 XDMAC 寄存器/描述符写入和启动等待函数 | 已证实（驱动层） | `analysis_out/dmac_start_transfer_20260906.txt`、`dmac_start_wait_20260906.txt`、`dmac_setbuf_ch_20260906.txt` |
| 47 | Stage_DfeRawTrans 到 dmac_ioctl/XDMAC 的直接调用关系已闭合 | 未证实 | 应用层当前停在软 DFE/对象 API，驱动层未连接为同一调用图 |
| 48 | DMM 分配响应包含 handle、extent 数量、extent 地址和大小：偏移 +0x04/+0x08/+0x10/+0x14 | 已证实（离线） | `analysis_out/avcam_dmm_call_helpers_20260906.txt`、`avcam_dmm_sync_helpers_20260906.txt` |
| 49 | `libmpr.so` 明确使用 `/dev/dmac` 并提交 DMAC 请求，具有描述符构建、ioctl 和等待路径 | 已证实（离线） | `analysis_out/mpr_dmac_xrefs_20260906.tsv`、`mpr_dmac_core_20260906.txt` |
| 50 | `Still Stream RAW Main` 或 `Stage_DfeRawTrans` 已证明由该 MPR DMAC 路径消费 | 未证实 | 仍缺少 MPR 内存表索引与调用者归属；当前只证明基础设施存在 |
| 51 | MPR area type `0x53` 对应 `Still Stream RAW Main`，表实际地址 `0xb59738` | 已证实（离线） | `analysis_out/mpr_area_table_20260906.json`、`tools/mpr_area_map.py`、`mpr_area_label_helpers_20260906.txt` |
| 52 | DFE RAW 传输已闭合到 DFE 内部 HDMAC 入口：`FUN_0028d388 -> FUN_0028c514 -> FUN_0072d4ce/d558 -> FUN_0072d226 -> FUN_0072dd40 -> FUN_00482180 -> FUN_0068db2c -> FUN_001d9554` | 已证实（离线） | `analysis_out/ghidra_stage_consumer_funcs_20260906.txt`、`avcam_hdmac_functions_20260906.txt`、`avcam_hdmac_refs_20260906.txt` |
| 53 | DFE HDMAC 与内核 `dmac.ko` 的 XDMAC 已证明是同一硬件 | 未证实 | DFE HDMAC 使用 `0xfc000000+0x1d000+...` 寄存器布局；`dmac.ko` 从平台资源取得基址，尚无静态桥接证明 |
| 54 | 内核 `dmac` 平台设备项为 `0x403f49f4`，资源表为 `0x403f5588`，含 8 个 `dmac_ch0..7` 项 | 已证实 | `analysis_out/ghidra_kernel_udif_platform_words_20260906.txt`、`ghidra_kernel_dmac_resources_20260906.txt` |
| 55 | XDMAC ch0-3 基址为 `0xf0000000`，ch4-7 为 `0xf0010000`，组内步长 `0x30` | 已证实 | `dmac_probe` 读取 `resource+0x10` 并存入全局表；`boss_lld_get_base_addr_dmac_ch` 返回 `base+0x30*ch+0x10` |
| 56 | DFE HDMAC 与 `/dev/dmac` XDMAC 是同一控制器 | 否定（当前证据） | 地址窗口不同（`0xfc000000` vs `0xf0000000/f0010000`），通道步长不同（`0x10` vs `0x30`） |
| 57 | XDMAC 与 DFE HDMAC 一定属于完全无关的硬件 | 高可信推测 | 现有静态证据已排除同一直接基址路径，但仍不能排除 SoC 内部地址别名/转换 |
| 58 | DFE 对象初始化使用固定内部基址 `0xf3000000`，并填充 `+0x4bc/+0x4c8/+0x4d4/...` 字段 | 已证实 | `FUN_002bd864 -> FUN_001d2598(...,0xf3000000)`；`analysis_out/avcam_dfe_mem_init_caller_20260906.txt` |
| 59 | DMM 分配的 extent 字段保存在 RAW 管理对象 `+0x5594/+0x5598/+0x559c/+0x55a0`，与 DFE 内部对象字段分离 | 已证实 | `FUN_002c2088` 读取 DMM 响应后保存；`FUN_0028d388` 再读取这些字段 |
| 60 | DMM extent 已证明作为 `FUN_001d9554` 描述符的直接源地址 | 未证实 | 当前只看到 `FUN_00298b34`/`FUN_001dd460` 构造描述符，尚未解析参数到 `FUN_001d9554` 的字段映射 |
| 61 | `0xf3000000` 已证明包含 Bayer 像素 | 未证实 | 当前证据只证明 DFE 对象布局和 HDMAC 读取 `+0x4c8` 字段 |
| 62 | `FUN_0072d226 -> FUN_001e9710` 构造的是 DFE 全局配置/帧描述表对象 | 已证实 | `FUN_001e9710` 调用 `FUN_00693ac8/FUN_00693716/FUN_00692292`，未直接读取 `+0x5594..+0x55a0` DMM 字段 |
| 63 | DFE HDMAC 路径已经证明会向 Linux `/dev/dmac` 提交请求 | 否定（当前证据） | `FUN_001d9554` 使用 `0xfc000000`；`dmac.ko` 资源为 `0xf0000000/0xf0010000`，二者不同 |
| 64 | `MPR -> /dev/dmac -> XDMAC` 与 `Stage_DfeRawTrans -> DFE HDMAC` 应作为两条独立证据链 | 高可信推测 | DFE HDMAC 描述符由内部配置表构造；MPR 路径明确打开 `/dev/dmac` 并提交 ioctl |
| 65 | `PlayJpegThum/PlayStill::CopyReadStillStream` 通过 `0x23a` 分配 DMM 单元并映射到 `/dev/stream2` | 已证实（静态） | `00387da4` 设置 `0x23a`，调用 `FUN_006c8ca0`；`FUN_006c8a2c -> FUN_006c5658 -> FUN_006c5484 -> FUN_006c7424` |
| 66 | `0x23a` 就是已证实 Bayer RAW 的连续视频源 | 未证实 | 只是 `Still Stream RAW Main` 的静态候选；尚未验证内容/时序 |
| 67 | `CopyReadStillStream` 的 `0x23a` 路径使用 `/dev/dmac` | 否定（当前证据） | 调用图进入 DMM/stream2 mmap 和 `FUN_001828e0`，未进入 `FUN_006c3dec/006c3c84` |
| 68 | `FUN_0028c514` 通过 `param_1+0x5594..+0x55a0` 直接读取 DMM extent 并写入 HDMAC | 否定（当前证据） | `FUN_0028c514` 正文没有读取 DMM 字段；它接收的是 `FUN_006a5004` 初始化的模式/句柄结构 |
| 69 | `FUN_0028d388` 在 `FUN_0028c514` 返回后调用 `FUN_002c12b4` 对 DMM 字段做环形缓冲轮转 | 已证实 | `FUN_0028d388` 在 Stage 调用后调用 `FUN_002c12b4`；后者读取 +0x559c/+0x55a0 等并交换槽位 |
| 70 | `Stage_DfeRawTrans -> DMM -> XDMAC` 已形成一条连续静态调用链 | 否定（当前证据） | DFE HDMAC 使用内部对象；DMM 是环形生命周期管理；MPR Still RAW 使用 stream2/memcpy；MP4 DMAC 未绑定 RAW extent |
| 71 | DFE、DMM、XDMAC 当前应作为三条独立证据链维护 | 高可信推测 | 已排除绝大多数直接调用路径，剩余风险是未解析的间接 callback/vtable 关联 |
| 72 | MP4 Mux 通过 `FUN_00552390 -> FUN_006c4020 -> FUN_006c3c84` 构建 `/dev/dmac` 对象 | 已证实 | `FUN_006c4020` 打开 `/dev/dmac`，用 `base/size/offset` 初始化对象；`FUN_00552390` 从 `linkListAreaAdr` 等字段传入 |
| 73 | MPR 内存区域地址已证明是 RAW 单元 `0x23a` 的 DMM extent | 未证实 | 只证明通用 memory-area-to-DMAC 桥，尚未建立 `0x23a` 到 `linkListAreaAdr` 的字段关联 |
| 74 | `0x23a` 的已验证调用者属于 `PlayJpegThum::CopyReadStillStream` / `PlayStill::CopyReadStillStream` 播放链路 | 已证实 | 函数符号与 RTTI 字符串确认；`docs/32_offline_state_audit_20260906.md` |
| 75 | `0x23a` 是 Sensor 拍摄 RAW 视频的候选路径 | 否定（当前证据） | 播放类调用者不证明拍摄；`0x23a` 还出现在通用调试扫描与 DMM/stream2 基础设施中 |
| 76 | `FUN_005c4080` / `FUN_00366ea4` 属于 `Mp4MovieWriterFilter` / `DubPlayRecToMp4` | 已证实 | RTTI/字符串和 vtable 指针表；`analysis_out/mpr_dub_vtable_words_20260906.txt` |
| 77 | `0x1df` 是唯一的 Movie RAW unit | 否定（当前证据） | `FUN_002c1b78` 把 `0x1df` 作为多个状态的回退值；`state=7` 另有 `0x12d/0x132`，`state=5` 另有 `0x2f5` |
| 78 | `context+0x1f0` 是 CaptureManager 的 CapMode | 已证实 | `FUN_002808e0` 从运行时配置表写入该字段；`CaptureManager.cpp` 字符串和 `FUN_0027f57c/2c1ab0` 调用；`docs/32_offline_state_audit_20260906.md` |
| 79 | CapMode 数值到静拍/Movie/DualRec 名称的映射 | 未证实 | 已导出状态表 `avcam_capmode_tables_20260906.json`，但配置表在 BSS/运行时区域，未找到枚举名 |

## 当前阶段门槛

继续留在离线静态分析阶段，直到至少闭合以下关系：

```text
unit type -> allocator -> buffer ownership -> DMA target -> producer -> consumer
```

未闭合前，不进入 RAM patch，不把任意 DMM 单元当作像素帧，不要求用户重新录像。
