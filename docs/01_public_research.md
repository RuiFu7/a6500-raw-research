# α6500 公开逆向资料知识库

> 结论分级：已证实 / 高可信推测 / 未证实 / 否定。本文件只整理公开资料与本仓库已归档源码，固件内证据另见 `02_static_analysis.md`。

## 1. SoC 结构

- 已证实：α6500 使用 Sony BIONZ X 处理器，型号 **CXD90014**（fwtool.py `devices.yml`：`ILCE-6500: arch: CXD90014, model: 0x61030035, apps: '2.17'`）。
- 已证实：CXD90014 为 4x ARM Cortex-A5，代号 Musashi/Kojiro，2013-10 起用于 ILCE-7 / ILCE-6000 / ILCE-6500 等（OpenMemories-Docs `hardware.rst`）。
- 已证实：CXD90014 上同时运行 Linux 与 AV 实时操作系统（µITRON RTOS）（OpenMemories-Docs `hardware.rst`）。
- 已证实：固件内 Linux 源码路径包含 `arch/arm/mach-cxd90014/`（`vmlinux.bin` 字符串），与公开资料一致。

## 2. Sensor 相关

- 高可信推测：α6500 使用 24.2MP APS-C Exmor CMOS（公开规格为 IMX350 类），但本阶段固件字符串未直接给出传感器型号。
- 未证实：固件中 `sabin/dcv_psf_table_*.bin` 头部分别含 `IMX210`、`SAL50_CenGch_3`，该表来自 RX100M5（IMX210）同一代码基线；不能据此判定 α6500 传感器型号。
- 已扫描（补充）：对 av-cam.bin、libObj/libmpr、sabin、Beaune、vmlinux 的全部 ASCII 字符串做了 `IMX*`/`SAL*` 检索，除 `IMX210`/`SAL50_*`（共享基线）外未发现 α6500 传感器型号字符串；传感器标识可能只存在于二进制配置表或运行时寄存器，不作为“未发现即否定”的证据。
- 已证实：固件存在 `spica_musashi_*`（SA DSP 图像处理程序）、`ApiSpicaEffect` / `ModuleSpica.cpp`（av-cam.bin），Spica 为 BIONZ 图像处理流水线代号。

## 3. DFE / Secondary Image Processor

- 高可信推测：CXD90014 相机存在 DFE 驱动代码：av-cam.bin 含 `api_dfe.cpp`、`AllocDfeMemForDfe2Pass()`、`FreeDfeMemForDfe2Pass()`、`/usr/dfe/dfe.bin`、`DFECore::getDramTicket/returnDramTicket`、`Dfe Imager::SetSleepOn/Off`。
- 未证实：α6500 主板上是否实际焊接 DFE 芯片（OpenMemories `hardware.rst` 只把 CXD90027 Regulus 列到 ILCE-7 / ILCE-6000，未列 α6500）；需要 Service Manual 或运行时探测确认。
- 未证实：`Resource/CoreResource/Leo/dfeCoreResource.cpp` 字符串暗示代码基线含 Leo DFE，但 Leo 在公开资料中对应 ILCE-7M3 等后续机型；α6500 是否使用 Leo 资源未证实。

## 4. BIONZ X（CXD90014）

- 已证实：BIONZ X 运行 Linux（`vmlinux.bin`、Android 2.3.7 风格 system 分区）与 µITRON AV 固件（`av-cam.bin`）。
- 已证实：固件存在主相机应用库 `libObj.so`、录像控制库 `libmpr.so`、场景脚本 `scenario/*.so`，通过 `dataflowInfraFramework.so` 与 `libosal_uipc.so` 通信。

## 5. SA DSP

- 已证实：SA DSP 在片上、与 ARM 共享内存、执行 "sabin" 程序（OpenMemories-Docs `hardware.rst`）。
- 已证实：α6500 固件带大量 `sabin/*.bin`：`sa_spica.bin`（SPC_PRE/MAP/POST）、`sa_dcv.bin`、`sa_dfdet.bin`、`sa_integenc.bin`、`sa_avcd/avce_*.bin`、`sa_star.bin` 等。
- 已证实：`spica_musashi_dualrec_4k_*` / `mov_4k_*` 程序表明 4K 录像使用 Spica+Musashi 流水线。

## 6. DRAM

- 未证实：α6500 DRAM 容量/带宽。公开资料称 BIONZ 用 MCP/PoP 封装（OpenMemories-Docs），但 α6500 具体容量未在公开资料中给出。
- 已证实：av-cam.bin 有 `DFECore::DdrPowerSaveOn/Off`、`getDramTicket/returnDramTicket` 等 DRAM 管理调用；Linux 侧有 `dmm.ko`、`dmm` 相关驱动。

## 7. DMA

- 已证实：内核源码路径含 `arch/arm/mach-cxd90014/bam.c`、`cxd90014.uart_dma_bitmap`，初始化日志含 `amba_device_register(dmac_devs[...])`、`platform_device_register bam failed`；即 CXD90014 有 DMAC 与 BAM。
- 已证实：rootfs 内核模块含 `kmod/dmac.ko`、`kmod/lld.ko`（nflasha7 rootfs），用户分区含 `kmod/dmm.ko`、`kmod/stream.ko`、`kmod/stream2.ko`、`kmod/mmcioWrapper.ko`。
- 已证实：av-cam.bin 含 `ringBufferWrapper RawSize==0`、`m_rawCountMax==0` 等环形缓冲调试串。

## 8. Movie pipeline

- 已证实：α6500 固件包含 **Beaune 编解码器固件**：`beaune/firmware.bin`（约 2.9MB，头部 `SW_VER_`）与 `beaune/ipl.bin`；构建路径字符串 `Beaune4KLong/20160408_00_ZX_RC2`，内含 AVC/MPEG2 编码器源码路径与 `DMA ERROR` 断言。
- 已证实：av-cam.bin 有 `[EXCODECENC] setVRCS_Params = &m_SetVRCS_ParamData_24P_3840x2160_100Mbps / 60Mbps / 25P / 30P` 等 4K XAVC 码率参数表。
- 已证实：av-cam.bin 有 `Stream Property : 3840x2160@24p / 30/25p / 60/50p` 字符串。
- 已证实：`SET_MOVIE_FORMAT[size, fr, asp, sizeh, proxy, proxysize, proxyfr, raw, rawsize]` 与 `SET_MOVIE_EE_INIT` 参数存在于 av-cam.bin；`raw/rawsize` 含义未证实。
- 已证实：MPR 库存在 `SetRecVideoBitDepth`、`CnvVideoBitDepth`、`CnvVideoDepthMBtoMPR`、`PubCodec::VideoBitDepth` 接口。
- 未证实：原生 10-bit 视频编码/10-bit RAW 视频通路是否存在。

## 9. LiveView pipeline

- 未证实：本阶段未对 LiveView 数据流做专门逆向；已知 `sabin/dcv_psf_table_movie/still` 与 `sa_dfdet`、`sa_star` 等与显示/对焦相关。

## 10. SD pipeline

- 已证实：内核模块含 `mmc_core.ko`、`mmc_drv.ko`、`sd_mod.ko`、`mmcioWrapper.ko`、`usb-storage.ko`；用户态含 `libsdcom.so`。
- 未证实：SD 实际持续写带宽（需实机测试）。

## 11. HDMI pipeline

- 已证实：av-cam.bin 有大量 ADF HDMI 串（`[ADF][OUT]HDMI ON/OFF`、`ProcPinCtrlHdmiAudio`、`HdmiPinExec`、`SetHdmiFormat`）；`libObj.so` 有 `HdmiCh::setDefinition`；内核有 `hdmi.ko`。
- 未证实：HDMI 输出位深/是否支持 RAW 输出。

## 12. 已知地址/函数/寄存器

- 已证实（符号/字符串级）：见 `02_static_analysis.md` 的“候选地址与符号表”。本阶段尚未建立完整地址-函数映射，`OpenMemories-Symbols/known_files.yaml` 不含 α6500 条目。
- 未证实：传感器初始化寄存器、readout 模式寄存器、DMA descriptor 布局。

## 13-15. 结论矩阵

| 项目 | 分级 |
| --- | --- |
| SoC=CXD90014、4x Cortex-A5、Linux+µITRON | 已证实 |
| 固件含 DFE 驱动代码 | 已证实 |
| 主板焊接 DFE 芯片 | 未证实 |
| Beaune 4K 编解码器固件存在 | 已证实 |
| SA DSP sabin 程序存在 | 已证实 |
| CXD90014 有 DMAC/BAM | 已证实 |
| 外部 RAW 输出场景存在（tethered RAW 拍摄） | 已证实 |
| 原生 10-bit RAW 视频通路存在 | 未证实（当前无证据） |
| α6500 传感器型号来自固件 | 未证实（仅公开规格） |
| 10-bit Log/4:2:2 视频 | 未证实 |

## 16. RAW 可能入口

1. `CAMERA_SCN_EXTERNAL_RAW_RECORD.so`：固件内已存在的 RAW 外部输出场景（函数：`cam_scn_raw_output_on/off`、`cam_scn_raw_device_acquire/release`、`CAM_SCN_RAW_FUNC_ID`、`RAW_EXTERNAL_OUTPUT`）。
2. `OBJAVBBCBASECLASS::SdiCh::setRawResolution`、`setYcRecTrigger`、`setDefinition`：SDI 通道 RAW 分辨率/YC 触发接口。
3. `OBJAVBBCBASECLASS::StmCh::rawparse`（`PARAM_COMP_RAW_PARSE` / `PARAM_REQ_RAW_PARSE`）：RAW 解析接口。
4. `MPR_SCN_INSTALL_MAP_DEMOMOVIE.so` 中的 `G_IDT_GET_MINIRAW`、`A_LM_MINIRAW_DATA`、`C_GET_LM_MINIRAW`：MINIRAW（低分辨率 RAW 预览）数据流。
5. av-cam.bin 中 `SET_RAW_EXTERNAL_OUTPUT[%d][%d][0x%x]`、`SET_RAW_EXTERNAL_OUTPUT_COMP[0x%x]`、`raw_external_output` 参数。

## 17. Sensor readout 相关代码

- 已证实：av-cam.bin 含 `[DFE] SensVDMask doesn't support SensVDMaskNum=%d`、`Dfe Imager::SyncInitial/SetSleepOn/Off`、`SetSyncParam Error`。
- 未证实：readout 模式/裁剪/合并/像素时钟/帧时序的具体寄存器与表。

## 18. 4K25 与 4K30 差异

- 已证实：固件同时含 24P/25P/30P 3840x2160 编码参数（100/60 Mbps）与 24p/30/25p 流属性字符串。
- 未证实：读取区域/超采样/裁切差异（原厂菜单宣称 4K24/25 使用更大读取区域；需要静态或运行时证据）。

## 19. 推荐的第一个无风险实验

见 `03_runtime_experiments.md`。原则：只读优先，不写相机；先验证“能否抓取一帧真实 Bayer 数据”。
