# α6500 Ver.1.06 固件静态分析

## 固件来源与校验

- 官方固件：`Update_ILCE6500V106.exe`（Sony `support.d-imaging.sony.co.jp/download/IMT/...`，fm=cn）
- 大小：293,234,872 字节；SHA256：`9832A5597A1EB8AE495157EF476E0210AF40B5B8999C45C0DC0E5929BA32F3FC`
- fwtool 输出 `config.yaml`：`model: 0x61030035`，`version: '1.06'`，`crypterName: CXD90014`
- 解包方式：updater exe 在偏移 `0x6ED72` 内嵌 DAT 固件（`\x89UFU\r\n\x1a\n`），切片后用 `fwtool.py unpack` 解出 `firmware.tar` 与 `updater.img`。

## 分区布局（partinf.conf，已证实）

| 分区 | 大小 | 用途 |
| --- | --- | --- |
| nflasha1 | 6MB | SYSTEM (Updater) |
| nflasha2 | 13MB | SYSTEM (Setting, vfat) |
| nflasha3 | 20MB | SYSTEM (Main, raw) → `av-cam.bin` / `vmlinux.bin` / `initrd.img` / `bonobo.bin` |
| nflasha5 | 60MB | Warm Boot Image (wbi) |
| nflasha7 | 4MB | Rootfs (raw) → busybox + `dmac.ko` / `lld.ko` / `nand.ko` |
| nflasha15 | 110MB | User (cramfs) → 相机应用层、`sabin/`、`beaune/`、`scenario/`、`kmod/` |
| nflasha16 | 82.75MB | Android system |
| nflasha17 | 99.75MB | Android data |
| nflasha18 | 20MB | LensData |

## 模块索引

- 已生成：`firmware/manifests/module_index_v106.csv` / `.json`（1758 个文件，含 size / magic / SHA256）。
- 字符串转储：`firmware/manifests/strings_av-cam.txt`、`strings_libObj.txt`、`strings_libmpr.txt`、`strings_beaune.txt`、`strings_sabin.txt`、`strings_scenario_vmlinux.txt`。

## 关键二进制

| 文件 | 格式 | 说明 |
| --- | --- | --- |
| `nflasha3/av-cam.bin` (13.9MB) | 裸 ARM 小端 | 主 AV/相机 µITRON 固件（首字节 ARM 分支指令） |
| `nflasha3/vmlinux.bin` (4MB) | 裸 ARM | Linux 内核（`mach-cxd90014`） |
| `nflasha15/lib/libObj.so` (18.3MB) | ARM ELF | 相机对象/AVBB 库 |
| `nflasha15/lib/libmpr.so` (11.9MB) | ARM ELF | MPR 录像/播放库 |
| `nflasha15/beaune/firmware.bin` (2.9MB) | 自定义（`SW_VER_`） | Beaune 4K 编解码器固件 |
| `nflasha15/sabin/*.bin` | SA DSP 自定义 | sabin 程序（spica / dcv / dfdet / integenc / star ...） |
| `nflasha15/scenario/CAMERA_SCN_EXTERNAL_RAW_RECORD.so` | ARM ELF | RAW 外部输出场景 |

## 高价值线索（按证据分级）

### 已证实（固件内符号/字符串）

1. **RAW 外部输出场景**：`CAMERA_SCN_EXTERNAL_RAW_RECORD.so`
   - 符号：`cam_scn_raw_output_common(Camera::RAW_EXTERNAL_OUTPUT, CAM_SCN_RAW_FUNC_ID, ...)`
   - `cam_scn_raw_output_on/off`、`cam_scn_raw_device_acquire/release`、`cam_scn_raw_ulogio_record_{1,2,4}byte`、`st_cam_scn_raw_ulogio_frm`、`cam_scn_external_raw_record_mtx_tbl`
   - 源码名：`camera_external_raw_record.cpp`
2. **av-cam.bin 参数**：`raw_external_output`、`SET_RAW_EXTERNAL_OUTPUT[%d][%d][0x%x]`、`SET_RAW_EXTERNAL_OUTPUT_COMP[0x%x]`、`CheckSetRAWExternalOutput`、`stl_raw_format`
3. **SDI RAW 接口**（libObj.so）：
   - `OBJAVBBCBASECLASS::SdiCh::setRawResolution(SDI::SDI_PRM_SDIOUT_SET_RAW_RESOLUTION)`
   - `SdiCh::setYcRecTrigger(SDI_PRM_SDIOUT_SET_YC_REC_TRIGGER)`、`SdiCh::setDefinition`
4. **RAW 解析**（libObj.so）：`OBJAVBBCBASECLASS::StmCh::rawparse(STM::PARAM_COMP_RAW_PARSE, PARAM_REQ_RAW_PARSE)`
5. **MINIRAW 数据流**：`G_IDT_GET_MINIRAW`、`C_IDT_MINIRAW_MON`、`A_LM_MINIRAW_DATA`、`C_GET_LM_MINIRAW`（MPR_SCN_INSTALL_MAP_DEMOMOVIE.so 共享数据流定义）
6. **DFE 驱动**（av-cam.bin）：`api_dfe.cpp`、`AllocDfeMemForDfe2Pass/FreeDfeMemForDfe2Pass`、`/usr/dfe/dfe.bin`、`DFECore::getDramTicket/returnDramTicket`、`Dfe Imager::SetSleepOn/Off`、`[DFE] SensVDMask...`、`Resource/CoreResource/Leo/dfeCoreResource.cpp`
7. **4K 编码**：`[EXCODECENC] setVRCS_Params = &m_SetVRCS_ParamData_{24P,25P,30P}_3840x2160_{100,60}Mbps`；`Stream Property : 3840x2160@24p / 30/25p / 60/50p`
8. **Beaune**：`firmware.bin` 头部 `SW_VER_`，构建路径 `Beaune4KLong/20160408_00_ZX_RC2`，含 `Video::VideoEnc`、`venc_*_avc.cxx`、`DMA ERROR.` 等
9. **录像位深接口**（libmpr.so）：`MprIf::SetRecVideoBitDepth`、`MprMonCtrl::CnvVideoBitDepth`、`mxfIfo_CommonSequence::CnvVideoDepthMBtoMPR`、`PubCodec::VideoBitDepth`
10. **DMA**：vmlinux 字符串 `arch/arm/mach-cxd90014/bam.c`、`amba_device_register(dmac_devs[...])`；rootfs `kmod/dmac.ko`；用户区 `kmod/dmm.ko`、`kmod/stream.ko`、`kmod/stream2.ko`
11. **Spica 流水线**：`ModuleSpica.cpp`、`ApiSpicaEffect`、`WrapSpicaOpen/Close`、`sa_spica.bin`（SPC_PRE/MAP/POST）、`spica_musashi_{still,mov,dualrec}_{4k_,}*` tap 程序

### 高可信推测

- `CAMERA_SCN_EXTERNAL_RAW_RECORD` 对应 PC Remote/tethered RAW 静拍（α6500 官方支持 PC Remote RAW 拍摄）；其函数同时是了解“RAW 从 Sensor 到哪一块内存/经哪条 DMA”的入口。
- SDI 通道（SdiCh）很可能是 SoC 与外部（HDMI 或编解码器）之间的数据接口；`setRawResolution` 提示存在 RAW 分辨率配置。
- `raw`/`rawsize` 出现在 `SET_MOVIE_FORMAT` 中，可能表示录像同时记录 RAW 旁路（如 DualRec 或 RAW 静帧），未证实。

### 未证实 / 待验证

- 10-bit Bayer 视频通路是否存在；现有证据只证明 RAW 相关代码存在于固件。
- α6500 是否有 DFE 芯片；`dfe.bin` 未出现在更新包文件树（av-cam 引用 `/usr/dfe/dfe.bin` 但文件不在本次解包产物中，可能在运行时分区或由另一分区提供）。
- SDI 的物理实现（HDMI？芯片间串行口？）；`setRawResolution` 的参数格式与位深。
- 4K25 与 4K30 的读取区域/裁切差异。
- DRAM 容量/带宽。

## 与公开符号库的差距

- `OpenMemories-Symbols/known_files.yaml` 目前没有 ILCE-6500 条目；地址级符号映射需自行建立。
- 建议后续用 Ghidra（需 JDK 17+，当前机器只有 JDK 8）或 capstone 从 av-cam.bin / libObj.so / libmpr.so 建立函数级索引，再对 RAW 场景函数做交叉引用分析。

## 结论

本阶段（离线）确认：α6500 固件内含 RAW 外部输出、SDI RAW 配置、RAW 解析、MINIRAW、DFE 驱动、Beaune 4K 编码器、SA DSP Spica 流水线与 DMAC/BAM 驱动。**尚未证实**这些通路能输出 10-bit Bayer 视频；下一步应以只读运行时实验验证候选入口。

## 附：RAW 场景函数级反汇编

目标：`scenario/CAMERA_SCN_EXTERNAL_RAW_RECORD.so`（ARM Thumb-2，ET_DYN；以下地址为 ELF 虚拟地址）。

### 入口 `scenario_run`（0x959）

- 场景命令 ID 必须为 `0xC`，否则返回 -1。
- 从参数缓冲区取 cmd（`*(u32*)param`）；cmd 0..4 走跳转表，对应五个函数。
- 调用前取 `param+4`（1 字节）与 `param+8`（32 位）作为参数，结果写回 `param[0]`。

### 消息协议 `cam_scn_raw_output_common`（0x7ed）

签名：`(Camera::RAW_EXTERNAL_OUTPUT, CAM_SCN_RAW_FUNC_ID, h, m)`。流程（PLT 导入已解析）：

1. `osal_valloc_msg_wait(0x14)` 分配消息；
2. `osal_set_msg_src(msg, 0xDC0000)`；
3. 消息填充：`[0]=5`，`[2..3]=0x40BD`（LE），`[8]=RAW_EXTERNAL_OUTPUT`，`[9]=h`，`[0xa..0xd]=m`；
4. `osal_snd_msg(msg)`；
5. `osal_rcv_msg_tmo(0xDC0000, reply, 5000)` 等待应答；
6. 校验 `reply[0]==1 && reply[2..3]==0x40BD`；
7. `osal_free_msg`，失败路径用 `cam_scn_raw_ulogio_record_*` 写日志。

### 四个封装

| 函数 | 类型值 | FUNC_ID | 语义（推测） |
| --- | --- | --- | --- |
| `cam_scn_raw_output_on`（0x935） | 0 | 1 | RAW 输出开 |
| `cam_scn_raw_output_off`（0x911） | 1 | 2 | RAW 输出关 |
| `cam_scn_raw_device_acquire`（0x8ed） | 2 | 3 | 设备占用 |
| `cam_scn_raw_device_release`（0x8c9） | 3 | 4 | 设备释放 |
| `cam_scn_raw_rsvhm`（0x7bd） | - | - | 保留/预留 |

### 结论

这是一个完整的“命令-应答”RAW 外部输出协议（目标组件收到命令后回 `0x40BD` 完成码）。结合 α6500 官方支持 PC Remote RAW 静拍，高可信推测该场景用于 tethered RAW 静拍（Sensor → RAW → USB），而不是视频。其消息协议与 `0xDC0000` 源地址可作为运行时只读探测的入口线索。

### SDI / STM RAW 解析链路（libBizFw.so / libStm.so / dataflowInfraFramework.so）

`libObj.so` 中的 `SdiCh`/`StmCh` 方法只是导入，实现位于 `libBizFw.so`：

- `SdiCh::setRawResolution`（0x3f16c）：通过 `DataflowInfraCh`（`OSALID_AUTO_FREE_MOD`）构造数据流消息，命令字 `0x2008`、子命令 `0x106`，读取通道 ID（`this+0x24`）后发送。
- `StmCh::rawparse`（0x42a34）：参数校验后转发到 STM，应答首字节置 `0xB`，结构体大小 `0x58`。
- `STM::rawparseImageInstance`（libStm.so 0x4394）：创建 `C_DataflowInfra_StdData_YC`，发送异步消息命令 `0x5017`（rawparse）/ `0x5012`（extract）调用 `extractImageInstance`，把返回的 0x58 字节图像实例元数据拷贝到 `PARAM_COMP_RAW_PARSE`。
- `C_DataflowInfra_StdData_YC`（dataflowInfraFramework.so）含 `Set/GetEntry_RawInfo`（0x1d814 / 0x1d808），另有 ImageSizeInfo、MovieEncInfo、MovieQualityInfo、YcStateInfo 等条目。

证据分级：

- 已证实：SDI 通道通过数据流消息配置 RAW 分辨率；STD_YC 数据结构包含 RawInfo 条目；STM 提供 image instance 的提取/解析接口。
- 高可信推测：`rawparse` 操作的是 YC/StdData 图像实例元数据（含 RawInfo），并非直接暴露 Sensor Bayer 数据。
- 未证实：RawInfo 条目是否携带 Bayer 原始数据指针/位深信息；SDI 通道物理端（HDMI/芯片间）。

这些地址与消息命令（`0x2008/0x106`、`0x5012/0x5017`、`0xDC0000`、`0x40BD`）可作为运行时只读探测的断点/消息过滤候选。

### RawInfo 结构（dataflowInfraFramework.so，已证实）

`C_DataflowInfra_Entry_RawInfo` 数据区从 `+0x14` 起共 24 字节（`PIN_YC_RAW_INFO`），由访问器函数确认字段：

| 偏移 | 字段 | 说明 |
| --- | --- | --- |
| +0x14 | UnitID | u32 |
| +0x18 | OutputFrameRate | u32（`PIN_YC_RAW_OUTPUT_FRAME_RATE` 枚举） |
| +0x1c | MetadataOffset | u32 |
| +0x20 | MetadataSize | u32 |
| +0x24 | RecTriggerOffset | u32 |
| +0x28 | RecTriggerSize | u32 |

`SetData_All/GetData_All`（0x20278/0x20290）整体拷贝这 24 字节。

`MprCnv::Exchg_RawInfo`（libmprctrl.so 0x22458）做的是文件元数据交换：`MPR::RawInfo+0x60/+0x6c/+0xb4/+0xc0` 与 `DefStruct::RawInfo+0x80/+0x90/+0xf0/+0x100` 之间的字符串拷贝（`StrUtil::StrCat` 类调用），并先做时区转换。

结论分级更新：

- 已证实：本固件中所有名为 RawInfo 的数据结构都是**元数据**（流内 RAW 元数据的偏移/大小/触发信息，以及 RAW 文件的 EXIF/开发信息字符串），**不含 Bayer 像素缓冲、位深或 pattern 字段**。
- 未证实：Sensor Bayer 像素数据在哪个缓冲区/数据结构中流动；10-bit Bayer 视频通路仍无证据。

### av-cam.bin 加载基址状态

- 已证实：`av-cam.bin` 主体为 Thumb-2 代码；0x0 处为 ARM 异常向量（`b 0x30`），0x30 起为启动桩，随后 `blx` 切换到 Thumb。
- 高可信推测：代码区文件偏移即可作为虚拟地址使用（0x1c020、0x5c9f68 等文件偏移处反汇编得到自洽 Thumb-2 函数，且 0x5c9f6a 出现与 `SdiCh::setRawResolution` 相同的子命令 `0x106`）。
- 已证实（补充）：0x3A810C 起存在字符串指针表，条目直接等于字符串的文件偏移（如 `0x8E5D96` → `"PCPCTRLIF ]Err!!!"`、`0x8B12F0` → `"ReceiveLastIndexInfo2"`）；即 **av-cam.bin 数据指针按文件偏移编址，加载基址为 0x00000000**。
- 已证实（补充）：代码是位置无关的（PIC）Thumb-2，字符串经 `ldr rN,[pc,#imm]` / `adr` 类 PC 相对引用计算。
- 已证实（Ghidra 12.1.3，2026-08-28）：`SET_RAW_EXTERNAL_OUTPUT[%d] [%d] [0x%x]`（0x90a24b）由 `0x00505100` 引用，位于 `FUN_005050c4`；`SET_RAW_EXTERNAL_OUTPUT_COMP[0x%x]`（0x908e28）由 `0x005016f0` 引用，COMP 处理器入口在 `0x005016c4`。
- 已证实：`FUN_005050c4` 只把消息偏移 +8（u8）、+9（u8）、+10..+13（u32）写入全局状态 +0x610/+0x614/+0x618，随后调用共享 setter `FUN_005047dc`（参数为 +2 的 u16、+4 的 u32、目标结构 0x005016c5）；它不接触像素缓冲、不返回 RAW 数据。
- 已证实：COMP 处理器（0x005016c4）比较全局 +0x610 与对象 +0x388，相等时向应答 +8 写入 `0xf000` 并返回 `0xc`，否则返回 0。
- 已证实：`FUN_005047dc` 是多个 SET_* 命令共用的“首次设置即生效”状态写入器；同族处理器包括 `SET_SPOT_METER_FOCUS`（0x504b28）、`SET_NOTIFY_MODE`（0x504c58）、`SET_CUSTOM_WB_SAVE`（0x504d18）等。
- 未证实：SET_* 处理器的间接分发表与命令字（整个二进制未找到这些函数地址的直接 32 位指针，疑似经 RAM 中动态注册/相对表分发）。
- 已完成（替代旧启发式）：`analyzeHeadless` 以 base 0 / `ARM:LE:32:v7` 完成全量分析（约 387s）；脚本与导出见 `tools/ghidra_scripts/` 与 `firmware/manifests/ghidra_*.{tsv,txt}`。

该状态不影响已完成的 ELF 级分析（scenario/libBizFw/libStm/dataflowInfraFramework 均有完整符号），且基址 0 已为 Ghidra/capstone 地址级分析铺平道路。

### SET_* 命令名表与 PC 相对引用修正

- 已证实：0x909c02-0x90a2f6 是连续 `SET_*` 命令名表（`SET_ZM_DRIVE`、`SET_MOVREC_MODE`、`SET_MOVIE_EE_INIT`、`SET_MOVIE_FORMAT`、`SET_SELF_TIMER`、`SET_SPOT_METER_FOCUS`、`SET_CRANK_CONTROL_MODE`、`SET_RAW_EXTERNAL_OUTPUT` 等），中间无空洞；这解释了 `SET_MOVIE_FORMAT` 等字符串找不到直接指针的原因（表按序号引用）。
- 已证实：PIC `add rN, pc` 的 PC 基址是 `指令地址+4`（不做 4 字节对齐）；修正后确认 `0x504bdc` = `SET_CRANK_CONTROL_MODE`、`0x504d80` = `SET_TOUCH_SPOT_COLOR`，与 `0x504b28` = `SET_SPOT_METER_FOCUS`、`0x504c58` = `SET_NOTIFY_MODE`、`0x504d18` = `SET_CUSTOM_WB_SAVE`、`0x5050c4` = `SET_RAW_EXTERNAL_OUTPUT` 构成同一 SET_* handler 族。
- `CheckSetImagerFrameSize`、`CheckSetAPSCMode`、`SetImagerFrameSize[%d]`、`SetAPSCMode[%d]` 同属命令名表（0x909c02 起），无直接代码引用；4K25/4K30 的 imager frame size / APSC crop 寄存器映射仍需运行时确认。
- 未证实：`SET_MOVIE_FORMAT` 对应 handler。已尝试：直接 32 位指针、16 位名字偏移序列（前 13 项）、6 个已知 handler 的相对偏移序列，以及 Ghidra 函数内 `ldr+add rN,pc` / `movw/movt` / `adr` 全量扫描（用已知 `SET_RAW_EXTERNAL_OUTPUT`/COMP 引用验证过脚本有效）均未命中；基本排除普通 PIC 字符串引用，仅剩名字表序号访问，需运行时消息过滤。

### DFE RAW 与 DualRec Bayer 通路（av-cam.bin，新发现）

`av-cam.bin` 内含完整 DFE 控制代码，源码串包括 `DfeLeo.cpp`、`dfeImagerPowerCtrl.cpp`、`api_dfe.cpp`，并有 `Camera::Imager::C_Imager::Dfe_Reg_Access(Camera::Imager::PARAM_DFE_REG_ACCESS*)` 符号串。

DFE RAW 传输相关证据：

- 阶段名 `Stage_DfeRawTrans`（0x8bb42c）与 `Stage_DfeRawTransSnrBranch`（0x8badde）位于 capture 序列字符串池；同池出现 `p_raw_out_dmm_info NULL err`、`p_raw_in_image_info NULL err`、`SetDmmInfo -> special_seq_param->dmm_info_raw`、`[DFE] DdrPowerOn Error`、`ReadExecuteBase`、`TDPreReviewBranchSetting` 等。
- `AllocDfeMemForDfe2Pass()`（0x005a2618）与 `FreeDfeMemForDfe2Pass()`（0x005a1dd4）已定位；调用者包括资源分派函数 `FUN_00270f60`、释放函数 `FUN_002706b8`、DFE 对象析构 `FUN_002a6958`。
- DFE 资源日志 `getDfeCoreResouces unknown : driveMode(%d) Zaf(%d) Snr(%d) Store(%d) Trans(%d)` 由 `FUN_001df528` 使用，表明 DFE core 资源按 drive/Zaf/Snr/Store/Trans 五维建模。

DualRec（JPEG+RAW 双记录）Bayer 通路：

- 源码名 `Stage_DualRec.cpp`；SA 函数 `sa_func_DUALREC_BAYER_acquire/release/exit`、`sa_func_DUALREC_CLEARVID_*` 存在。
- 参数错误串定义 `RawHsize/RawHofs/YcArea_H/YcHsize/YcHofs/YcVsize/YcArea_V/YcVofs`，即 DualRec 同时维护 RAW 与 YC 两个裁剪窗口。
- `StartSA_Bayer` / `end sa` 与 `DUALREC_BAYER_start_mbx.cha_mbx0..3` 表明 Bayer 数据经 SA DSP 邮箱消息启动/停止。

`libmprctrl.so`（Ghidra 地址 = ELF VA + 0x10000）中的 DualRec 配置函数：

- `MprCtrl::GetDualRecType`（0x24814）：读 EEPROM 字节，返回 0/1。
- `MprCtrl::GetDualRecCaptureCount`（0x236a0）：按类型查表，表值为 `[0xFF, 0x0A]`（.rodata 0x263d8），其他类型回退 10。
- `MprCtrl::GetDualRecMovieMaxBitrate`（0x24ec4）：读 EEPROM 字节，返回录像最高码率档。
- `MprCtrl::IsDualRecOver18Mbps`（0x244e8）与 `MprCtrl::IsDfeSupportDualRec`（0x24f9c）：读 EEPROM 标志位。
- `MprCtrl::PrintInfo`（0x277e4）会打印 DualRec 类型、张数、>18Mbps 标志。
- `MprCtrlStillMgr::GetDualRecStillMode`（0x2b248）在静止尺寸表里选择最大码率模式；`UtilStillSize::CnvDualRecSize`（0x33220）做 0..3 枚举映射。
- CautionConfig 有用户设置符号：`AutoDualRecOn/Off`、`AutoDualRecShootingFrequencyLow/Std/High`、`NumOfAutoDualRec*`、`DualRecImageSize{S1_7M..L17M}`、`TwoStreamDualRec*`。

`libObj.so`（Ghidra 地址 = ELF VA + 0x10000）中的 AutoDualRec 调度：

- `pvt_SetParamAutoDualRec`（`FUN_00441730`）：读参数 `0x4D1`（Mode）与 `0x4D4`（Frequency），经 `FUN_0044a3c8` / `FUN_0044a4bc` 转换后经 ObjMsg 参数 `0x9AC4` / `0x9AC5` 下发。
- 模式转换：`0 -> 0x54F`（Off）、`1 -> 0x550`（On）。频率转换：`0 -> 0x553`（Low）、`1 -> 0x552`（Std）、`2 -> 0x551`（High）。
- `FUN_009fb9b8`（CamMsgConv）读取 ObjMsg 参数 `0x9AC4`（Mode）与 `0x9AC5`（Frequency），把 `0x54F/0x550` 映射为内部 byte 0/1，把 `0x551/0x552/0x553` 映射为内部 byte 0/1/2，确认 App→Obj 的 AutoDualRec 消息转换。
- `pvt_CheckSetAutoDualRecValid`（`FUN_006d61b8`）：仅在特定相机状态（掩码 `0x71` 对应状态 0/4/5/6，即 Movie 录像相关状态）下有效；Id 不匹配、`+0xd6d` 标志、`FUN_00397054(+0x48)`、状态越界分别置无效位 `0x10/0x100/0x1000/0x10000`。
- `FUN_00875250`：当 `m_captureCnt > 10` 时日志 `!!!! DUAL REC Over 10 remain`，并按 `remaining = 10 - m_captureCnt` 发送 ObjMsg `0x3700/0x1035`（参数 `0x1001/0x1061/0x1057`），确认 **10 张抓拍上限**。
- 值 ID 与模型名：`VALUEID_CAP_RAW_DUALREC`、`VALUEID_DUALREC_CAPTURE_EXPAND_ON/OFF`、`DUALREC_SIZE_L/M/S/VGA`、`STILL_REC_DUAL_INTERVAL_REC`、`STILL_INTERVAL_REC_DUAL`、`MOVIE_REC_DUAL_INTERVAL_REC`、`INTERVAL_H/M/S/MS/NUMBER`。
- `VALUEID_CAP_RAW_DUALREC` 位于 libObj 值名指针表 `0x10CC300`，条目索引 `0x1F`（31）；对应枚举数值需运行时读取确认。

结论分级：

- 已证实：av-cam 存在 DFE 寄存器访问、DFE RAW 传输阶段、DualRec Bayer SA 函数与 RAW/YC 双窗口参数。
- 已证实：α6500 固件包含 Movie 模式的 Auto Dual Rec 功能配置（拍摄频率 Low/Std/High、张数 10/255、最大录像码率档、DFE 支持标志），即**录像中可自动抓拍静止帧**，DualRec Bayer 通路可在 Movie 模式触发。
- 高可信推测：DualRec 抓拍保存 RAW 时即产生 Bayer 数据到 DRAM/SA DSP，是连续 RAW 视频最可行的复用入口；但单次抓拍与连续 RAW 视频之间的时序/数量限制仍需运行时验证。
- 未证实：`Stage_DfeRawTrans` 与 `Stage_DualRec` 的驱动函数地址（未找到直接 32 位指针；16 位相对偏移盲扫同样因大量伪命中未收敛，阶段表疑似运行时注册或使用更复杂的基址计算）；DualRec Bayer 位深/packing；触发频率是否可提高到 1fps 以上。

### Linux 侧内核与模块证据

- 已证实：内核版本 `3.0.27_nl-rt106+`，`SMP PREEMPT_RT ARMv7`，gcc 4.5.1（Sony CE Linux 8.2.2.x），构建主机 `jp10239@build-f-u12-791.cv.sony.co.jp`。
- 已证实：内核源码路径含 `arch/arm/mach-cxd90014/{bam,pcie,hwtimer,cpuid,wdt}.c`；初始化日志含 `amba_device_register(dmac_devs[...])`、`platform_device_register bam failed`。
- 模块元数据（`firmware/manifests/strings_kmod.txt`）：

| 模块 | 说明 | 相关通路 |
| --- | --- | --- |
| `beaune_drv.ko` | Beaune Driver | 4K 编解码器控制 |
| `stream.ko` / `stream2.ko` | Stream / Stream2 driver | 数据流 |
| `dmm.ko` | Sony Proprietary，参数 `DmmConfig` / `DmmConfigExtra` | DRAM 管理（对应 OpenMemories-CI 中的 DmmConfig.bin） |
| `osal_uipc.ko` / `osal_ulogio.ko` | uIPC / ulogio（参数 `ulogio_initfile`） | RAW 场景日志函数 `cam_scn_raw_ulogio_record_*` 同源 |
| `mmc_core.ko` / `mmc_drv.ko` / `mmcioWrapper.ko` / `ms_drv.ko` | SD/记忆棒 | SD 写入 |
| `hdmi.ko` | HDMI 驱动 | HDMI 输出 |
| `usbg_*.ko` | USB gadget（sen/stillimage/storage） | tethered RAW / PC Remote |

- 高可信推测：`stream.ko` / `stream2.ko` 是 BIONZ 内部视频/RAW 数据流设备，运行时可在 `/dev` 探测对应节点；`dmm.ko` 的 `DmmConfig` 参数指向 DRAM 分区配置文件，是后续内存布局分析的关键。

### 启动脚本确认的运行时入口

- `change_mode.sh`：appFw 支持 `3g`（target gdb）、`3s`（gdbserver）、`3k`（KMC ICE）、`3L`（LeakTracer）等调试模式；写入 `/setting/mode/dmode`，重启后生效。
- `s_start_android.sh`：Android system 挂载 `/dev/dnflasha16`、data 挂载 `/dev/nflasha17`；Android 进程 cgroup 内存上限 **113MB**（对 DRAM 总量是有用的下限线索）；启动后 `insmod /usr/kmod/usbg_adb.ko` 启用 ADB。
- `common.src`：SD 设备 `/dev/mmca1`、记忆棒 `/dev/ms1`；电源 IC 类型枚举（Charon/CA/Piroshki）。
- `up.sh`：updater 模式标志 `mode3` = Service mode，`mode5` = MS Crypt，`mode6` = Version Skip。

### sabin / Beaune 固件格式（已证实）

- SA DSP sabin 程序共用头部：魔数 `AA 0A 13 91`（LE `0x91130AAA`）、版本字 `04 00 00 05`、若干配置字段、8 字节保留，然后内嵌 ASCII 名称：
  - `sa_spica.bin` → `SA_SPICA`
  - `sa_dcv.bin` → `SA_DCV__0x13`
  - `sa_integenc.bin` → `ZM_A3E__0x00`
  - `sa_star.bin` → `SA_STAR_0x00`
- `spica_musashi_*.bin` 与 `star_kernel_param.bin` 为无头部的系数/参数数组（tap 表）。
- `dcv_psf_table_*.bin` 头部为 `IMX210` + `SAL50_...`（共享代码基线，非 α6500 传感器直接证据）。
- `beaune/firmware.bin`：版本串 `SW_VER_03_33_04`，随后 32 位字含加载地址 `0x80F88B20`、`0x80F88C20`（Beaune 私有地址空间）。
- `beaune/ipl.bin`：头部 `10 00 00 07` + `eSOL-eBinder-B`，证实 Beaune 使用 eSOL eBinder RTOS（与 OpenMemories-Docs codec 表一致）。

### nflasha5（WBI1 warm boot 镜像）

- 魔数 `WBI1`（偏移 0，第二个 WBI1 头在 0x280617）。
- 头部 32 位字段（LE）：`0x685`、`0x9`、`0x8005317C`、`0x20060224`、`0x200`、`0x032AA000`、`0x0F0F0F0F`、`0x0C046000`。
- 字符串含 `sabin/ssboot.`、`APPFW`、`boot_`/`version`/`entry` 等，判断为 ssboot/warm-boot 加载器区域，加载地址域为 `0x80000000`。
- 未在 nflasha5 中找到 av-cam.bin 二进制副本（无 `0A0000EA`+`ORIL` 头，也无 `SET_RAW_EXTERNAL_OUTPUT` 字符串）；它不直接提供 av-cam 加载地址。
- 否定（补充）：0x280617 处的第二个 `WBI1` 签名位于压缩/图像数据流内部；`APPFW` 字符串也出现在图像数据流而非描述表。从 nflasha5 直接解析 av-cam 加载地址的路线不成立，需改从 `warm.c`/`ssboot` 代码或运行时映射入手。

### CXD90014 QEMU 模拟（a6300 updater 内核，已证实）

- 通过 `a6300_updater_emu_full/run.py`（ghproxy 镜像取得完整仓库）在 `cxd90014` machine 上启动，成功进入 BusyBox shell。
- 已证实：CXD90014 物理 DRAM **1024MB @ 0x80000000-0xBFFFFFFF**（cmdline `mem=1024M@0x80000000@0`）。
- 已证实：保留区 `0x28000 @ 0x80000000`、`0x3D270000 @ 0x82D90000`；内核 `.text 0x40038000`、lowmem `0x40000000-0x80000000`、modules `0x3F000000-0x40000000`。
- 已证实：`/dev/stream`（249,7）、`/dev/stream2`（249,8）、`/dev/dmac`（251,205）、`/dev/uipc`（251,207）、`/dev/mcmn`、`/dev/ldec`、`/dev/hdmi*` 等设备节点存在（记录见 `experiments/emulated/`）。
- 说明：这是 a6300 更新器内核，用于 CXD90014 布局证据；α6500 实机布局仍需运行时确认（高可信推测同 SoC 同布局）。
- 已推导：用 OpenMemories-CI `kernel_patch.getKernelBase()` 对 α6500 `vmlinux.bin` 反推内核基址 `0x40038000`（与模拟器一致）。
- 未成功：α6500 完整内核 + initrd 在单核 cxd90014 machine 下 90 秒无输出；完整系统模拟需 Loader 启动链。
- 已证实（vmlinux 字符串）：内核内置 `arch/arm/common/warm.c`（WBI 温启动：`warm.mem_dst`、`wbi_cmpr.waddr`、`warm_boot_pm_*`）与 `kernel/power/ssboot/*`（SA DSP 启动、内存映射注册、优化器/镜像写入器）；这是 av-cam / ssboot 固件加载机制的一部分，后续地址分析可沿这些函数入手。
