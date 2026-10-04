# α6300 ↔ α6500 官方固件同构性对比分析报告

> 本报告基于离线固件分析，不涉及任何相机运行时操作。所有结论按 `已证实 / 高可信推测 / 未证实 / 否定` 分级。

## 1. 固件版本与来源

| 型号 | 固件版本 | 文件 | 哈希 (SHA256) |
|------|----------|------|---------------|
| α6300 (ILCE-6300) | Ver.2.01 | `firmware/a6300-raw/Update_ILCE6300V201.exe` | `0677B93F7BA550BD33C9C8732B20FB3D3302C14E943436F22B60AE8264188942` |
| α6500 (ILCE-6500) | Ver.1.06 | `firmware/raw/Update_ILCE6500V106.exe` | `9832A5597A1EB8AE495157EF476E0210AF40B5B8999C45C0DC0E5929BA32F3FC` |

两者均通过 fwtool 成功解包，建立了完整模块索引（α6300 1626 个文件，α6500 1758 个文件）。

## 2. 整体同构性统计

| 指标 | 数值 |
|------|------|
| 共同文件路径 | 1587 |
| 字节级完全相同 | 1076 |
| 内容不同但路径相同 | 511 |
| α6300 独有 | 39 |
| α6500 独有 | 171 |
| 不同文件中大小相同（仅为内容差异） | 208 |

**结论**：两个固件共享极高的代码基线，超过 67% 的共同文件完全一致。差异集中在驱动层、功能表以及部分核心库的版本升级。

## 3. 关键模块同构性

### 3.1 Bayer RAW 通路核心符号

以下关键符号在 α6300 和 α6500 中同时存在，且字符串出现次数一致：

| 符号 | α6300 | α6500 |
|------|-------|-------|
| `sa_func_DUALREC_BAYER_acquire` | 2 | 2 |
| `sa_func_DUALREC_BAYER_release` | 1 | 1 |
| `sa_func_DUALREC_BAYER_exit` | 2 | 2 |
| `sa_func_DUALREC_BAYER_start` | 1 | 1 |
| `Stage_DualRec.cpp` | 1 | 1 |
| `Stage_DfeRawTrans` | 2 | 2 |
| `Stage_DfeRawTransSnrBranch` | 1 | 1 |
| `RawHsize` / `RawHofs` | 各 2 | 各 2 |
| `YcHsize` / `YcVsize` | 4 / 2 | 4 / 2 |
| `StartSA_Bayer` | 1 | 1 |
| `StartSA_ClearVid` | 1 | 1 |
| `p_raw_out_dmm_info` | 1 | 1 |
| `DualRecParamErr` | 7 | 7 |
| `SetDualRecParam()` | 1 | 1 |
| `CheckSetMovieFormat` | 1 | 1 |
| `CheckSetRAWExternalOutput` | 1 | 1 |
| `CheckSetImagerFrameSize` | 1 | 1 |

**结论**：Bayer 抓拍的底层框架（DualRec 阶段、DFE RAW 传输、邮箱消息结构）在 α6300 和 α6500 中完全一致。**已证实**。

### 3.2 Movie RAW 参数脚手架

以下参数 ID 和回调在 `libObj.so` 中同时存在：

| 符号 | α6300 | α6500 |
|------|-------|-------|
| `PARAMID_RAW_OUTPUT_MODE` | 6 | 6 |
| `PARAMID_MOVIE_RAW_SIZE` | 5 | 5 |
| `VALUEID_RAW_OUTPUT_ON` | 1 | 1 |
| `VALUEID_RAW_OUTPUT_OFF` | 1 | 1 |
| `VALUEID_MOVIE_RAW_2K` | 1 | 1 |
| `VALUEID_MOVIE_RAW_4K` | 1 | 1 |
| `MSGID_SET_MOVIE_FORMAT` | 6 | 6 |
| `SequencePinOpenMovieFormatInfoRaw` | 7 | 7 |
| `SequencePinNotifyMovieFormatInfoRaw` | 7 | 7 |
| `N9OBJSCALAR19SequenceHapiCmdBase...REQ_SEQUENCE_RAW_CAPTURE` | 16 | 16 |
| `GetStdMovieFormatInfo` | 9 | 9 |

`SET_MOVIE_FORMAT` 完整字符串（含 `raw:%d rawsize:%d`）在两个 `av-cam.bin` 中完全相同。

**结论**：Movie 模式下设置 RAW 输出格式的协议栈在两个型号中同构。**已证实**。

### 3.3 DFE 控制与 DDR 管理

两者共享大量 DFE 控制字符串（`DFE DDR`、`DFECore::`、`dfeImagerPowerCtrl` 等），但 α6500 引入了额外的连续缓冲管理函数：

| 差异项 | α6300 | α6500 |
|--------|-------|-------|
| `AllocDfeMemForDfe2Pass` | 无 | 有（1 次） |
| `FreeDfeMemForDfe2Pass` | 无 | 有（1 次） |
| `SetSyncParamRawBuffering` | 无 | 有（1 次） |
| `ringBufferWrapper RawSize==0` | 无 | 有（1 次） |
| `DualRecJpegTarget` | 1 | 2（重复出现） |
| `SuperSlowManagerDfe` | 无 | 有（2 次） |
| `Stage_TDReadExecute` | 无 | 有（1 次） |
| `Stage_BolTDReadExecute` | 无 | 有（3 次） |
| `RESOURCE_IMAGER0_STORE_RAW` | 无 | 有（1 次） |
| `RESOURCE_IMAGER0_TRANS_RAW` | 无 | 有（1 次） |

**结论**：α6500 的 DFE 驱动支持 2-pass 连续 RAW 缓冲、环形缓冲区包装、以及专门的 TD（传输）读取阶段，这些是 α6300 不具备的。这暗示 α6500 具备更高阶的 RAW 流式能力，但具体可用性仍需运行时验证。**高可信推测**。

### 3.4 其他显著差异

- **α6300 独有的调试/工厂字符串**：大量 `DFE DDR Check`、`CPU APB : DFECAM*`、`SubLVDS` 相关字符串，表明 α6300 固件包含更详尽的硬件测试路径。
- **α6500 独有的传感器 OLC 调试字符串**：`OLC_0 Sensor OFF cnt R/Gb/Gr/B` 等，表明 α6500 有更细致的传感器输出监控。
- **编译路径差异**：α6300 使用 `161H.DSLR.DX.reco.LATEST`，α6500 使用 `161H.DSLR.DMHH1.reco.LATEST`，说明平台代号不同。

## 4. 对 α6500 只读实验的启示

1. **Bayer 抓取入口点完全可用**：α6300 和 α6500 共享相同的 `sa_func_DUALREC_BAYER_*`、`Stage_DualRec.cpp` 和邮箱参数，因此从 α6500 抓取一帧 Bayer 的机制与 α6300 理论上是同一套。
2. **连续 RAW 缓冲有工程基础**：α6500 独有的 DFE 2-pass、`ringBufferWrapper` 等代码表明索尼已经为连续 RAW 输出埋下了伏笔，但这不等于开箱即用，必须通过运行时实验验证。
3. **α6300 先验**：由于 α6300 缺失连续缓冲相关代码，它更适合作为“能否获得一帧 Bayer”的验证平台；而 α6500 可能支持更高阶的连续抓取，但需要更精细的 RAM patch 实验。

## 5. 结论分级汇总

| 结论 | 等级 |
|------|------|
| α6300 与 α6500 固件共享 Bayer DualRec 通路框架 | 已证实 |
| Movie RAW 参数脚手架在两个型号中同构 | 已证实 |
| α6500 具备 DFE 2-pass 连续 RAW 缓冲相关代码 | 已证实 |
| α6500 拥有环形缓冲区 RAW 管理代码 | 已证实 |
| α6500 在运行时可直接启用连续 25fps RAW 输出 | 未证实 |
| 3K/10-bit/25fps 连续 RAW 写入 SD 卡可达 50–70 MB/s | 未证实 |
| α6300 可作为“一帧 Bayer 验证”先行平台 | 高可信推测 |

---

**报告生成时间**：2026-08-30  
**分析工具**：`tools/fw_extract.py`, `tools/index_modules.py`, `tools/strings_scan.py`, `rg`, `python` 内联脚本  
**工作区路径**：`<workspace>`

## 6. 可复现产物

对比统计和关键文件 marker 由以下命令生成：

```powershell
python.exe tools/compare_firmware_manifests.py firmware/manifests/module_index_a6300_v201.csv.json firmware/manifests/module_index_v106.json --output firmware/manifests/a6300_a6500_comparison.json --csv-output firmware/manifests/a6300_a6500_comparison.csv
```

- `firmware/manifests/a6300_a6500_comparison.json`：统计、共同/独有路径、关键文件哈希和 marker 计数。
- `firmware/manifests/a6300_a6500_comparison.csv`：逐路径状态与两边大小/哈希。
- `firmware/manifests/module_index_a6300_v201.csv.json`：α6300 解包模块索引。
- `firmware/manifests/module_index_v106.json`：α6500 解包模块索引。

路径键统一为相对 `0700_part_image/...` 形式；α6500 manifest 的 `firmware.tar_unpacked/` 前缀由工具在读取时规范化，但原始输入路径保留在 JSON 的 `key_files` 中。
