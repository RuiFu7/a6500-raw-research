# α6500 静态审计报告（2026-09-05）

## 范围

本报告只使用 α6500 V1.06 解包文件、已有 Ghidra 导出和此前已归档的运行时结果。没有执行 PMCA、ADB、Zadig、`ioctl`、`mmap`、RAM patch，也没有写入相机。

唯一 canonical workspace：`<workspace>`

自动化产物：

- `analysis_out/static_audit_20260905.json`
- `docs/evidence_ledger.tsv`
- `tools/static_audit.py`

关键输入文件及 SHA256 已写入 JSON；本报告不把文件名、字符串或函数名直接当成功能证据。

## 当前结论

1. 固件里确实存在拍照 RAW/DFE/DualRec 相关的内存管理、阶段名和消息接口。
2. `FUN_002c1ab0` 根据内部状态选择 `0x236/0x1df/0x23e/0x2b3`，`FUN_002c2088` 再通过 DMM 分配并保存句柄和两个 DMM 返回字段。这证明了 RAW 相关内存管理链存在，不证明分配内容就是 Bayer 像素。
3. α6500 独有的 `AllocDfeMemForDfe2Pass` 会以 `0x324` 调用 DMM 请求构造器，并记录资源状态。这是 DFE 2-pass 资源证据，不是连续 RAW 视频证据。
4. `CAMERA_SCN_EXTERNAL_RAW_RECORD.so` 只构造 0x14 字节 OSAL 消息并交给 AV 消息系统；该场景 ELF 没有 `open/write/ioctl` 等直接文件或设备导入。真正的下游接收者和输出设备尚未静态闭合。
5. `libmpr.so` 的 `stream2` 路径能把物理范围注册后 `mmap` 到进程，但它是通用映射能力；没有证据表明某个 Movie RAW producer 必然使用它。
6. `SetRecVideoBitDepth`、`StmCh::rawparse`、`SdiCh::setRawResolution` 都是配置/控制/解析接口，当前没有证据证明它们产生 10-bit Bayer 视频。
7. `PlayStill` 的 `RawDevelopInfo` 明确打印 `rawMainSrcDataArea.unitType/unitHandle/unitPhyAddr/offset/virtTopAddr/size`，说明静态 RAW 播放链使用结构化 RAW 缓冲描述符；它属于静态图像播放路径，不能直接外推为 Movie RAW producer。
8. 4K 24/25/30 的固件字符串和编码参数表存在，但当前导出没有传感器 readout、crop、row timing、pixel clock 数值，因此 4K25 与 4K30 的传感器差异仍未证实。
9. 之前的 Movie 候选缓冲和 `0x1df` 抓取都没有得到通过 Bayer/unpack/debayer/场景响应验证的像素帧。`0x1df` 当前只能记为动态分配候选，不能记为 RAW 帧。

## 候选路径图

```text
拍摄状态 param+0x1f0
        |
        v
FUN_002c1ab0  -- 选择 DMM unit type: 0x236 / 0x1df / 0x23e / 0x2b3
        |
        v
FUN_002c2088  -- DMM allocate/reuse
        |
        +--> handle -> object +0x5208
        +--> unit type -> object +0x5598
        +--> DMM 返回字段 -> object +0x559c / +0x55a0
        +--> 0x1df 特殊派生字段 -> object +0x5594
        |
        +--> 后续 producer / DMA / consumer：尚未闭合

DFE 状态/资源
        |
        v
FUN_005a2618  -- 条件满足时构造 2-pass 资源请求
        |
        +--> FUN_002e7300(0x324, 1, 0, &out, 5)
        +--> FUN_0001cfe4 发送请求
        +--> 记录句柄和资源状态
        |
        +--> 0x324 的实际内容/所有权：未证实

External RAW scenario
        |
        v
0x14-byte OSAL message -> AV message receiver -> 下游动作未知

MPR stream2
        |
        v
{phys,size}[] -> ioctl 0xC0047805 -> mmap -> 通用物理区访问
```

## 函数级证据

### RAW unit selector

`firmware/manifests/ghidra_avcam_rawunit_func.txt:002c1ab0`：

- `param+0x1f0` 被比较为 `0xa`、`0x1b`、`0x9`。
- 返回指令出现 `0x236`、`0x1df`、`0x23e`、`0x2b3`。
- 直接 caller 是 `0x002c20ba`，即 RAW 内存管理函数调用它取得 unit type。

这里只能确认“状态到 DMM 类型的选择逻辑”，不能确认像素格式、行宽、位深或 producer。

### RAW memory manager

`firmware/manifests/ghidra_avcam_rawmem_func.txt:002c2088`：

- `0x002c20ba` 调用 unit selector。
- 普通路径调用 `0x006a7d6a(unit_type, 0, 1, 0xffffffff, &out)`。
- 特殊复用路径调用 `0x006a7c84(0x1df, previous_handle, 1, &out)`。
- 成功后写入对象偏移 `+0x5208`、`+0x5594`、`+0x5598`、`+0x559c`、`+0x55a0`。
- 直接 caller 为 `0x006b751c`、`0x006b6b86`、`0x002cfb22`。

`+0x559c/+0x55a0` 是 DMM 返回的两个字段；在没有结构体定义和运行时对应关系前，不把它们命名为“物理地址/大小”。

### DFE 2-pass

`firmware/manifests/ghidra_avcam_dfe_alloc_funcs.txt:005a2618`：

- 先通过 `0x00743ef2` 下发/校验 DFE 参数。
- 条件满足时，`r0=0x324`、`r1=1`、`r3=&out`、栈参数为 `5`，调用 `FUN_002e7300`。
- 成功后保存返回字段和句柄，并按驱动类型写入资源状态槽。
- 直接 caller 为 `0x002718ba`、`0x00271964`、`0x002a6d9a`。

这条链支持“存在 DFE 2-pass 资源申请”，不支持“0x324 是 RAW 像素帧”或“已经有连续 Movie RAW”。

### External RAW scenario

对 `CAMERA_SCN_EXTERNAL_RAW_RECORD.so` 进行 ELF 符号和反汇编复核：

- `cam_scn_raw_output_on/off`、`cam_scn_raw_device_acquire/release` 都进入同一个 `raw_output_common`。
- `raw_output_common` 分配并初始化 0x14 字节消息，设置消息源 `0xdc0000`，填入函数 ID、设备/参数字段，然后同步发送。
- ELF 动态导入是 OSAL 消息函数、`memset` 等，没有直接 `open`、`write`、`ioctl`、`mmap`。

因此更准确的表述是“外部 RAW 场景向 AV 任务发送 RAW 控制消息”，而不是“该场景自己把 RAW 写到 USB/SD”。

### Movie 位深、RAW parse、SDI RAW

- `MprIf::SetRecVideoBitDepth -> FeaIf::SetRecVideoBitDepth -> FeaCore::SetRecVideoBitDepth`：最终更新录像对象中的位深参数并返回状态，没有在该函数链中看到 Sensor/DFE/DMA buffer 生产调用。
- `StmCh::rawparse`：构造 RAW parse 请求并发给 STM/dataflow 对象，属于解析命令接口；没有在该函数中看到传感器读取或 Movie 帧生产。
- `SdiCh::setRawResolution` / `setYcRecTrigger`：构造 SDI/dataflow 控制请求，属于外部输出/通道控制；没有直接返回 RAW 像素内存。
- `PlayStill::GetRawMakerNote` 和 `GetRawMainSrcData`：属于 `PlayStill`，读取静态图像播放所需的 RAW 区域描述。其日志字段明确包含 unit type、handle、physical address、offset、virtual address、size。

## 4K25/4K30

`firmware/manifests/ghidra_4k25_30_xrefs.tsv` 和 `av-cam.bin` 中可以确认：

- 编码器参数表分别出现 24P、25P、30P 的 3840x2160 60/100 Mbps 配置。
- 存在 24P/25P/30P clock 类型和当前 clock 日志。
- 这属于编码器/系统时钟配置证据。

当前不能从这些字符串推出：

- Sensor 实际 readout 区域
- crop/APS-C 模式
- binning/subsampling
- row timing 或 pixel clock 数值
- 4K25 与 4K30 的真实 Bayer 数据源

所以“4K30 裁切更小、4K25 读取区域更大”目前只能保留为外部资料/待验证假设，不能写入静态结论。

## 运行时结果如何影响静态判断

- 录像态 `0x321/0x311/0x2d7/0x8125b/0x2bd` 已确认会分配并可读，但已测试窗口没有形成干净像素帧；具体是 YUV、编码中间态、流数据还是其他结构仍未完全证实。
- `0x1df` 已确认在拍摄相关会话中出现过约 48 MiB 的动态分配，并可读回 16 MiB；但控制实验中多份文件逐字节一致，另有文件高度模式化，未通过自然场景/Bayer/debayer 验收。
- 因此当前最准确的结论是：**已证实 RAW 相关内存管理与动态分配候选；未证实真实 Bayer 像素；未证实 Movie 连续 RAW。**

## 下一步仍可离线完成

1. 用已有 Ghidra 项目导出 `0x006b751c`、`0x006b6b86`、`0x002cfb22` 的完整函数块，确认三个 caller 分别属于静态图像、DualRec 还是其他捕获阶段。
2. 导出所有引用 `p_raw_out_dmm_info`、`dmm_info_raw`、`Stage_DfeRawTrans` 的函数块，寻找结构体字段复制、DMA 参数和释放点。
3. 对 `SetSyncParamRawBuffering`、`ringBufferWrapper` 做实际函数/XREF 定位，不再只依据字符串。
4. 对 `libmpr.so` 中 `RawDevelopInfo` 和 DMM 接口做字段偏移表，区分静态播放 RAW 描述符与拍摄 RAW 分配对象。
5. 补充 α6300/α6500 对应 `av-cam.bin` 的同地址函数反汇编对照，确认 α6500 独有的 2-pass 代码是否真正进入 Movie 状态。

在这些工作完成前，不进入 RAM patch，也不要求重新录像或按快门。