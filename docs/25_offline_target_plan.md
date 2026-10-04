# 离线阶段目标与可交付成果

## 1. 目标

把“不接触相机、不写固件、不 RAM patch”的静态分析推到边界，最终得到一份可以指导下一阶段只读实验的、可复核的逆向证据链：

```text
RAW 单元选择
  -> DMM 分配/复用
  -> DMM extent 地址/大小
  -> DFE/MPR 描述符
  -> DMAC/XDMAC 请求
  -> 最终消费者
```

这个目标不把“看到 RAW 字符串”或“找到疑似 buffer”当作成功。只有字段语义、调用关系、数据路径和证据来源都闭合后，才升级结论等级。

## 2. 为什么把离线阶段当作一个独立目标

1. 当前还不应该继续做相机实验。已有实机抓取表明 `0x1df` 不是真实 Bayer RAW，若没有离线证据修正抓取窗口，继续抓只会增加误判。
2. 离线阶段可以缩小实验范围，把随机内存扫描变成几个可验证地址和一个明确的触发条件。
3. 所有离线结论都能保留在当前工作区，之后每次实机实验都可以重新回查。
4. 离线阶段并不依赖数据线、PMCA、Zadig、ADB、`/dev/mem` 或相机状态，因此可以先完成。

## 3. 硬性边界

- 只分析固件、ELF、Ghidra 项目和已有归档数据。
- 不连接相机做运行时读取。
- 不运行 PMCA、Zadig、ADB、telnet 或 QEMU 真机启动链。
- 不执行 `/dev/mem`、ioctl、mmap。
- 不写 `/setting`、SD 卡、固件分区或内核模块。
- 不 RAM patch，不修改永久固件。
- 如果不确定字段语义，只能写“高可信推测”或“未证实”。

## 4. 离线最终可以做到什么

### 4.1 可以做到

- 给出 DMM unit type 与 RAW/DFE 路径的完整映射表。
- 给出 DMM 分配请求的字段布局、返回值布局，以及 handle/unit type/extent 地址/大小的读取方式。
- 给出 DFE `Stage_DfeRawTrans` 的描述符字段流，并区分“描述符构造”和“硬件搬运”。
- 给出 `libmpr.so` 中 DMAC/XDMAC 的调用入口：`/dev/dmac`、`ioctl` 请求、描述符链表和等待路径。
- 给出 `/dev/stream2` 物理映射与 DMM extent 之间的对应，说明后续只读读取应使用哪个通道。
- 列出 4K25 与 4K30、拍照 RAW、DualRec、Movie 录像模式之间已经确认的差异。
- 生成可复现的 Ghidra/ELF 分析产物，并保留证据来源和 SHA256。
- 给出下一阶段第一个只读实验的候选地址、读取长度、抓取窗口和失败判据。

### 4.2 最终也许能得出的静态结论

- 能证明 α6500 固件中存在至少一条可追踪的 RAW 相关内存描述链。
- 能证明 DMM 管理的是物理 DRAM extent，而不是某个虚拟数组。
- 能证明 MPR 库确实通过 DMAC 进行内存搬运。
- 能证明 `Stage_DfeRawTrans` 是否与 MPR DMAC 路径共用同一种 DMM unit 类型。

### 4.3 离线阶段不能做到

- 不能证明候选 buffer 内容就是 Bayer RAW。
- 不能证明 10-bit/12-bit packing、Bayer pattern、stride 或帧时序。
- 不能证明 3K/25fps、30fps 或 50-70 MB/s 持续写入可行。
- 不能证明 DMM extent 在实机中的动态分配行为。
- 不能替代“对同一场景重复读取、改变 ISO/快门/光圈后数据变化”的验证。
- 不能证明一次抓取就是视频帧，仍然需要帧间时序验证。

## 5. 完成标准

- 至少闭合一条从“候选单位”到“DMM extent”再到“DMAC 请求”的静态路径，或者明确证明该路径不是 RAW 视频路径。
- 每个结论都有函数地址、文件路径、反汇编/反编译证据和“已证实/高可信推测/未证实/否定”等级。
- 下一个实验不再需要随机猜测地址；读什么、从哪里读、读多少、如何判断是否有意义，都有明确协议。
- 所有离线产物都写成中文 Markdown，并放在 `<workspace>\docs` 和 `analysis_out`。

## 6. 当前状态和下一步

当前最有价值的新证据是 `libmpr.so` 中存在独立的 DMAC 使用层，并且已经从静态数据表中定位到 `Still Stream RAW Main` 的 MPR area 类型：

- `FUN_006c3c84`：打开 `/dev/dmac`。
- `FUN_006c3dec`：向 `/dev/dmac` 提交 DMAC 请求，包含通道和描述符物理地址。
- `FUN_006c4bf2`：构造 0x20 字节条目、按 0x40000 字节分块并反复提交 DMAC。
- `FUN_006c3da0`：等待 DMAC 完成。
- `FUN_006c7718` / `FUN_006c89a4` / `FUN_006c8ca0`：按 DMM unit handle 查询 extent 地址/大小。
- `FUN_006c7424`：通过 `/dev/stream2` `ioctl 0xC0047805` 和 `mmap` 建立物理到虚拟映射。
- libmpr `.data` area 表：`Still Stream RAW Main` 的类型 ID 为 `0x53`，所在表起始地址为实际 `0xb59738`（Ghidra 显示 `0xb69738`），可由 `tools/mpr_area_map.py` 复现。
- `FUN_006c5484`：把 MPR area 描述符中的物理地址/大小数组交给 `FUN_006c7424`，后者注册到 `/dev/stream2` 并 mmap。
- `FUN_006c8a2c` / `FUN_006c5658`：组装 area 描述符并对每个物理 extent 调用上述 stream2 映射路径。
- `FUN_006c8ca0`：DMM 单元打开/分配包装层，是进入 MemInfo/MPR area 管理前的入口。

因此，原来的“DMM 和 DMAC 同时存在”已经升级为“MPR 库明确存在 DMAC、DMM 打开包装、stream2 映射和 `Still Stream RAW Main` 面积类型”。下一个不再需要猜名字：可以沿着 area type `0x53` 查找对应 DMM unit，再确认它是否进入 DMAC 路径。

## 7. 对后续阶段的意义

如果离线把这条链闭合，下一阶段就只需要做两类非常窄的验证：

1. 触发对应 DMM unit 分配，读出 extent 地址和大小。
2. 使用受控只读映射抓取候选区域，并把同一画面对照和帧间时序验证起来。

这会显著降低把“流中间数据”误认为 Bayer RAW 的风险，也会让每一步都从“猜测”变成“验证一个已有静态假设”。

## 8. 2026-09-06 夜间目标（已更新）

本次离线阶段把目标拆成以下可验收项：

1. 解决 `dmac.ko` XDMAC 与 av-cam DFE HDMAC 的硬件身份问题：已完成，证据见 `docs/28_xdmac_hdmac_identity_20260906.md`。
2. 区分 DFE 内部内存 `0xf3000000`、DFE HDMAC `0xfc000000` 和 DMM extent：已完成，证据见 `docs/29_dfe_internal_memory_and_dmm_separation_20260906.md`。
3. 找出 MPR 中最可控的静态 RAW 单元候选 `0x23a`：已完成静态链路，证据见 `docs/30_mpr_still_raw_candidate_20260906.md`。
4. 下一项可选目标：解析 `FUN_0028c514` 中 `+0x559c/+0x558c` 是如何进入 `FUN_001e9710` 或 `FUN_001dd460` 的。
5. 下一项可选目标：把 `Still Stream RAW Main` area type `0x53` 与 DMM unit `0x23a` 的运行时映射关系收窄。
6. 已补充最终静态闭合审计 `docs/31_static_chain_closure_20260906.md`：当前证据不支持 `DFE RAW Stage -> DMM -> XDMAC` 单链；DFE HDMAC、DMM 生命周期、MP4 DMAC 应作为独立证据链。

没有相机连接、没有 RAM patch、没有固件写入；所有新增结论都保留为“静态候选”或“已证实（代码级）”，不会把推测写成结论。
