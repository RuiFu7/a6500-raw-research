# DFE RAW 传输阶段函数审计（2026-09-05）

## 输入

- `analysis_out/ghidra_raw_stage_funcs_full_20260905.txt`
- `analysis_out/ghidra_raw_stage_xrefs_20260905.tsv`
- α6500 V1.06 `av-cam.bin` 的已有 Ghidra 项目

本次只读执行 Ghidra headless 分析，没有接触相机。

## 关键升级

### `FUN_0028d388`

该函数对应 `Stage_DfeRawTrans` 字符串引用的实际代码函数，直接 caller 为 `0x006a43d8` 和 `0x006a4502`。

静态行为：

- 允许的内部状态为 `2/4/5/6/7/8`，其他状态直接返回。
- 每轮传输准备时设置：
  - `local_40 = context + 0x559c`
  - `local_34 = context + 0x558c`
  - `local_3c = *(context + 0x5206)`
- 调用共享处理函数 `FUN_0028c514(context, local_48)`。
- 在完成分支中，读取 RAW 内存管理对象的字段并写入下游全局结构：

```text
context + 0x5594 -> DAT_000020f0 + iVar12
context + 0x5598 -> DAT_000020f4 + iVar12
context + 0x559c -> DAT_000020f8 + iVar12
context + 0x55a0 -> DAT_000020fc + iVar12
```

随后调用：

```text
FUN_006859ec(DAT_00002070 + iVar12, context + 0x1f8)
```

并清除 `context + 0x5206` 的句柄状态。

**结论**：已证实 RAW 内存管理对象中的四个字段会进入 DFE RAW 传输阶段的下游描述结构。这个结论比“只看到 RAW 字符串”更强，但字段的物理含义仍未完全命名，不能直接写成“像素地址、大小、stride”。

### `FUN_0028d8c8`

该函数包含 `dmm_info_raw` 的代码引用，且在处理前会：

- 根据状态选择 `context + 0x558c`、`context + 0x55ac` 或其他 DMM/句柄信息。
- 读取 `context + 0x5204` 相关句柄。
- 调用 `FUN_0028c514(context, &local_30)`。
- 后续执行资源清理和状态回收。

它说明 DMM/RAW 信息也参与另一条读执行/传输准备路径，但当前函数导出没有把 `dmm_info_raw` 的字段映射到实际 DMA 寄存器。

### `FUN_0028ec78`

该函数对应 `Stage_DfeRawTransSnrBranch` 字符串引用，实际行为更像序列/资源编排：

- 仅在 `context + 0x72c == 2` 时继续。
- 复制 `+0x5226`、`+0x5204` 等句柄/序列字段。
- 根据 `context + 0x1f0` 调整 `+0x52be` 的计数/分支值。
- 调用 `FUN_00298364`、`FUN_005a3cfc`、`FUN_0029f348` 等准备/处理函数。
- 在此函数体内没有直接调用 `FUN_002c2088`、`FUN_006a7d6a` 或明显的 DMA 寄存器写入。

**结论**：这个 SNR 分支是 RAW 传输流程的一部分，但当前导出不足以证明它自己分配或产生像素数据。

### `FUN_0028b1a8`

该函数包含 DualRec/Bayer 几何和曝光相关的参数准备：

- 读取 `context + 0x5204` 句柄。
- 调用 `FUN_002c1d08`、`FUN_002c1f38` 等资源/参数函数。
- 组装多个 RAW/YC 尺寸、偏移和区域字段。
- 代码中出现 `0x3000/0x3800/0x4400/0x4800` 等内部参数常量。
- 最终经 `FUN_004477d0` 等函数继续处理。

它支持“DualRec/Bayer 阶段存在完整的几何参数结构”，但没有在该函数内闭合到传感器 DMA 目标。

### `FUN_005c9e64`

该函数与 `ringBufferWrapper RawSize==0`、`m_rawCountMax==0` 的字符串引用相关：

- 通过 `FUN_001df4f4` 获取资源对象。
- 通过 `FUN_00690324`、`FUN_001dd0a4`、`FUN_001def94` 准备资源/缓冲状态。
- 将输入参数保存到 `param_1[1]`、`param_1[2]`、`param_1[3]`。
- 构造 0x30 字节局部结构并调用 `FUN_001dd460`。

**结论**：这里可以确认环形资源初始化/提交逻辑存在，但不能从当前函数直接推出 RAW 帧的内存布局或每帧大小。

## 静态数据流闭合程度

```text
状态 param+0x1f0
  -> FUN_002c1ab0
  -> unit type 0x236/0x1df/0x23e/0x2b3
  -> FUN_002c2088
  -> DMM allocate/reuse
  -> context +0x5594/+0x5598/+0x559c/+0x55a0
  -> FUN_0028d388 (Stage_DfeRawTrans)
  -> DAT_000020f0..DAT_000020fc
  -> FUN_006859ec
  -> 下游处理/写入：函数语义尚未闭合
```

当前已闭合：

- unit selector 到 DMM manager：已证实
- DMM manager 到 Stage_DfeRawTrans 描述字段：已证实
- Stage_DfeRawTrans 到最终像素 producer/DMA/consumer：未证实
- RAW 位深、packing、stride、真实 Bayer 内容：未证实
- Movie 连续帧和 24/25fps：未证实

## 结论调整

可升级为：

> α6500 固件存在一条可追踪的 RAW 相关内存描述流：状态选择 DMM unit，RAW 内存管理器分配/复用并保存字段，DFE RAW 传输阶段再把这些字段打包进入下游处理结构。

不可升级为：

- 已找到 Bayer 像素 buffer。
- 已找到 10-bit/12-bit packing。
- 已找到 Movie 连续 RAW producer。
- 已找到 SD/USB 直接输出。
- 已证明 3K/25fps 可行。

## 下一步离线任务

1. 导出 `FUN_006859ec`、`FUN_006a686a`、`FUN_002975e0`、`FUN_00296884`、`FUN_00298b34` 的完整函数，确定 `DAT_000020f0..fc` 的下游消费者。
2. 沿 `FUN_0028d388` 的两个 caller `0x006a43d8`、`0x006a4502` 反查调度状态，确认是否有 Movie 状态进入。
3. 对 `FUN_002c2088` 保存字段和 `PlayStill::RawDevelopInfo` 的 `unitPhyAddr/size/offset` 做交叉结构比对，寻找共同的 DMM descriptor 格式。
4. 继续找 `stride/width/height/bit depth/packing` 的字段读写；在找到之前，不安排新的相机实验。
## 下游辅助函数复核

### `FUN_006859ec`

裸 ARM 反汇编（`analysis_out/avcam_descriptor_copy_setters_20260905.txt`）显示它是结构复制函数：

```text
src +0x60 -> dst +0x60
src +0x68..+0x6f -> dst +0x68..+0x6f
src +0x70..+0x77 -> dst +0x70..+0x77
src +0x78 -> dst +0x78
```

调用形式为 `FUN_006859ec(destination, source)`。它没有出现设备寄存器、DMA kick 或文件写入；当前更适合命名为“描述/图像参数复制”，不能命名为“RAW 搬运器”。

### `FUN_006a686a` / `FUN_006a687e`

反汇编显示这是一对四字段 setter/getter：

```text
FUN_006a686a(object, field1, field2, field3, field4):
    object +0x250 = field1
    object +0x254 = field2
    object +0x258 = field4
    object +0x25c = field3

FUN_006a687e(object, out):
    out[0] = object +0x250
    out[1] = object +0x254
    out[2] = object +0x258
    out[3] = object +0x25c
```

`FUN_0028d388` 的完成分支调用 `FUN_006a686a` 时传入句柄、两个上下文字段和计算出的字节数，因此可以确认它在建立一个下游四字段描述符。该函数本身不是 DMA 发起器。

这使静态链条进一步明确为：

```text
RAW DMM unit/metadata
  -> Stage_DfeRawTrans
  -> descriptor setter/copy
  -> 后续消费者（仍未定位）
```

## 当前最强但仍有限的结论

已证实：

- RAW unit selector 存在。
- RAW memory manager 通过 DMM 分配/复用并保存相关字段。
- `FUN_0028d388` 会消费这些字段并建立下游描述符。
- 描述符复制/setter 不等于像素搬运；目前没有从这些函数看到 DMA kick、Sensor Bayer packing 或 SD 写入。

仍未证实：

- 描述符字段中哪个是物理地址、哪个是长度、哪个是 offset/stride。
- 下游消费者是否属于静态 RAW、DualRec、Movie 或其他捕获模式。
- 是否存在可连续刷新的 Movie Bayer producer。