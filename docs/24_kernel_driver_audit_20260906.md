# α6500 内核 DMM / XDMAC 驱动离线审计（2026-09-06）

## 范围

只分析解包固件中的内核模块，不接触相机。重点文件：

- `firmware/unpacked/ilce6500-v106/.../nflasha15_unpacked_unpacked/kmod/dmm.ko`
- `firmware/unpacked/ilce6500-v106/.../nflasha7_unpacked_unpacked/kmod/dmac.ko`
- `firmware/unpacked/ilce6500-v106/.../nflasha15_unpacked_unpacked/kmod/stream2.ko`

## DMM 单元管理

`dmm.ko` 的 ELF 符号已经明确包含：

```text
dmm_ctrl_OpenUnitHdlr
dmm_ctrl_GetUnitInfoHdlr
dmm_ctrl_AllocUnitNewHdlr
dmm_ctrl_AllocUnitReuseHdlr
dmm_ctrl_AllocUnitRendezvousHdlr
dmm_ctrl_FreeUnitHdlr
dmm_ctrl_CloseUnitHdlr
dmm_ctrl_GetUnitAttrHdlr
dmm_ctrl_GetUnitSizeHdlr
dmm_unit_ctrl_Alloc
dmm_unit_ctrl_Open
dmm_unit_ctrl_Close
dmm_unit_ctrl_GetUnitInfo
dmm_unit_ctrl_GetUnitType
dmm_unit_ctrl_GetUnitSize
dmm_unit_ctrl_GetUnitTop
dmm_ext_ctrl_AllocExtent
dmm_ext_ctrl_GetExtentSize
dmm_unit_tbl_GetUnitTbl
```

### Unit 表结构

- 单个 unit 表项大小为 `0x188`。
- handle 低 10 位是单元索引，高 6 位可能表示单元类别/kind。
- 代码频繁访问：
  - `+0x618`：unit type 或关键分配值
  - `+0x620`：status
  - `+0x621`：open count
  - `+0x622`：预留/状态
  - `+0x623`：kind
  - `+0x628`：extent 数量
  - `+0x62c`：extent 指针表
- `dmm_unit_ctrl_GetUnitInfo` 会返回 unit type、open count、extent 数量，并把各 extent 的 `+0xc` 字段累加到一个输出值。该输出最可能是总大小/字节数，尚未最终确认。
- `dmm_unit_ctrl_Open` 在 extent 循环中输出成对字段：
  - 第一项为 `extentA+4 + extentB+8`
  - 第二项为 `extentA+0xc`
  - 该布局高度符合 `{物理地址, 大小}` 或 `{基址+偏移, 长度}`，但“物理地址”名称仍是静态推断。
- `dmm_ext_ctrl_GetExtentSize`、`dmm_extent_ctrl_GetExtentAttribute` 存在，说明 extent 表有独立的尺寸和属性元数据。

### 分配流程

`dmm_ctrl_AllocUnitNewHdlr` 的静态流程表明：

1. 读取请求中的 unit type、extent 数量等字段。
2. 调用 DMM 分配函数。
3. 分配成功后继续调用 `dmm_unit_ctrl_Open/GetUnitInfo` 一类接口，把 unit 信息填入响应。
4. 响应包含 handle、状态、extent 数量，并可能含有物理地址/大小。

这与 av-cam 中 `FUN_002c2088` 保存的 `+0x5594/+0x5598/+0x559c/+0x55a0` 是同一层数据接口的候选，但目前仍没有静态证据证明两者使用同一条消息。

## XDMAC 硬件驱动

`dmac.ko` 的 ELF 符号明确包含：

```text
dmac_ioctl
dmac_mem_transfer_async
boss_hw_dmac_init
boss_hw_dmac_start_transfer
boss_hw_dmac_start_wait
boss_hw_dmac_write_reg
boss_hw_dmac_proc_setbuf_reg_unit
boss_hw_dmac_proc_setbuf_reg_ch
boss_hw_dmac_process
boss_hw_dmac_get_state
boss_lld_get_base_addr_dmac
boss_lld_get_base_addr_dmac_ch
```

模块字符串还包含：

```text
XDMAC register dump start
XDMAC internal variable information dump start
XDMAC Descriptor information dump start
LAST lli_phys
dmac_base_addr
XDMAC:ch=%u:spurious
```

### 硬件写入特征

`boss_hw_dmac_start_transfer` 反汇编显示，它从一个源描述符结构向目标寄存器区连续复制 6 个 32 位字，并写入：

```text
register + 0x18 = 常量
register + 0x1c = 0x11
```

每次写入前后都有 `dsb sy` 和可选的 barrier 回调。这是典型的 DMA 描述符/寄存器提交模式，但我们尚未解析每个 32 位字段的语义。

`boss_hw_dmac_start_wait` 也复制 6 个 32 位字，设置状态字段并进入等待循环，最后读取错误/完成状态。

`boss_hw_dmac_proc_setbuf_reg_ch` 按 channel 连续写入 10 个寄存器段，循环参数包括传输大小、基址、长度等。`dmac_mem_transfer_async` 则把请求挂到异步队列。

结论：

> `dmm.ko` 提供物理 extent/unit 管理，`dmac.ko` 提供 XDMAC 硬件寄存器写入和描述符/等待路径。这两个驱动都存在，但它们之间的关系尚未通过静态调用图闭合。

## 当前静态语义

```text
Stage_DfeRawTrans
  -> DMM/DFE 高层对象 API（尚未直接连到 dmac）
  -> DMM unit/extent 元数据（候选物理地址/大小）
  -> XDMAC boss_hw_dmac_*（硬件寄存器写）
```

仍未证实：

- Stage 是否直接使用这条 DMM→DMAC 路径；
- DMM extent 输出字段中哪个是物理地址、哪个是大小；
- XDMAC 六个寄存器字段的精确语义；
- 该路径是否对应 Movie 连续 RAW 缓冲；
- Bayer/stride/packing 是否符合目标。

补充（2026-09-06 晚）：`libmpr.so` 已确认存在独立 DMAC 用户层，见 `docs/26_mpr_dmac_audit_20260906.md`。这不是“DMM 与 DMAC 直接连接”的证明，而是把断口从“两者无关”修正为“MPR 内存搬运基础设施存在，RAW producer 归属仍缺”。

补充（2026-09-06 晚，重大更新）：DFE 侧 HDMAC 硬件链已闭合，见 `docs/27_dfe_hdmac_chain_closed_20260906.md`。`Stage_DfeRawTrans` 不是停在软件 API，而是最终进入 DFE HDMAC 寄存器转移路径。

## 产物

- `analysis_out/dmm_ctrl_AllocUnitNewHdlr_20260906.txt`
- `analysis_out/dmm_ctrl_OpenUnitHdlr_20260906.txt`
- `analysis_out/dmm_ctrl_GetUnitInfoHdlr_20260906.txt`
- `analysis_out/dmm_dmm_unit_ctrl_GetUnitInfo_20260906.txt`
- `analysis_out/dmm_dmm_unit_ctrl_Open_20260906.txt`
- `analysis_out/dmm_dmm_unit_ctrl_Alloc_20260906.txt`
- `analysis_out/dmm_dmm_unit_ctrl_Reuse_20260906.txt`
- `analysis_out/dmm_dmm_unit_ctrl_GetUnitType_20260906.txt`
- `analysis_out/dmm_open_handler_20260906.txt`
- `analysis_out/dmm_extent_attr_20260906.txt`
- `analysis_out/dmac_ioctl_20260906.txt`
- `analysis_out/dmac_async_20260906.txt`
- `analysis_out/dmac_start_transfer_20260906.txt`
- `analysis_out/dmac_start_wait_20260906.txt`
- `analysis_out/dmac_setbuf_ch_20260906.txt`
- `analysis_out/dmac_process_20260906.txt`
