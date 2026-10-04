# Stage_DfeRawTrans 调用链与内部描述符审计（2026-09-06）

## 范围

本轮只读分析 α6500 V1.06 `av-cam.bin` 已有 Ghidra 项目，没有操作相机、没有执行 PMCA/ADB/ioctl/mmap、没有 RAM patch、没有写入固件。

## 新增证据

### 1. 事件分派器

`FUN_006a4394(int param_1)` 反编译结果：

```c
return *(undefined1 *)(param_1 + 0x23);
```

即它只是返回对象 `+0x23` 的字节，作为分派键。

### 2. 两个分派器都会进入 Stage

`FUN_006a43b2`：

```c
uVar7 = FUN_006a4394();
switch(uVar7) {
case 0: ...
case 1:
    uVar7 = FUN_0028d388(param_1);
    return uVar7;
...
}
```

`FUN_006a44a0`：

```c
uVar8 = FUN_006a4394();
switch(uVar8) {
...
case 5:
    uVar8 = FUN_0028d388(param_1);
    return uVar8;
...
}
```

结论：`Stage_DfeRawTrans` 可以由不同事件路径进入；`+0x23` 的字节决定调用哪个阶段。

### 3. 阶段调用者初始化传输对象

`FUN_006a43b2` 的普通路径中：

```c
*(char *)(iVar2 + 0x52be) = *(char *)(iVar6 + 0x52be) + 1;
*(undefined4 *)(iVar2 + 0x5774) = 1;
*(int *)(iVar2 + 0x5778) = iVar6 + 0x52dc;
```

因此 `context+0x5778` 指向 `context+0x52dc`，`context+0x5774` 被置为 1。这为后续描述符 setter 提供了明确的传输对象地址。

### 4. `FUN_0028d388` 的关键描述符操作

在 `(`Stage_DfeRawTrans`)` 的完成分支中：

```text
FUN_006859ec(&DAT_00002070 + iVar12, context + 0x1f8);
```

并在另一分支中：

```text
FUN_006a686a(
    *(context + 0x5778),
    *(context + 0x5204),
    *(context + 0x5584),
    *(context + 0x5588),
    *(context + 0x1fc) * *(context + 0x200) * iVar10);
```

`FUN_006a686a` 原始反汇编是一个简单的四字段 setter：

```text
obj+0x250 = field1
obj+0x254 = field2
obj+0x258 = field4
obj+0x25c = field3
```

所以此处确实在把句柄、两个上下文字段和计算出的长度写入下游对象。该函数本身不是 DMA 发起器。

### 5. `FUN_00296884`：对齐大小计算

裸 ARM 反汇编显示：

```text
bl 0x0068281e
...
ldr r0, [sp+0x50]
muls r0, r7, r0
bl 0x00683038
```

其中 `r7` 在当前分支为 `6` 或 `8`，`FUN_00683038(r0, 0x80)` 是：

```c
(r0 + 0x80 - 1) & ~(0x80 - 1)
```

即 128 字节对齐。结果写入：

```text
context+0x5594 或 context+0x5584
```

并更新 `[r6+0x34]`、`[r6+0x38]`。

这是 RAW/DFE 传输大小或缓冲预算计算；当前仍未确认 `6/8` 乘数的精确单位，不能直接称为像素位深或 stride。

`FUN_0068281e` 内部调用 `FUN_00682796`，后者读取一个对象并返回：

```text
[out+0x00] = from object + 0xbc
[out+0x04] = from object + 0xbe
```

该对象类型和字段语义仍未确定。

### 6. `FUN_00298b34`：传输描述符构造

裸 ARM 反汇编显示它构建一个结构并提交：

```text
[r5+0x00] = context + 0x724
[r5+0x04] = 1
[r5+0x05] = ...
[r5+0x08] = 0
[r5+0x0c] = 0
[r5+0x10] = from [r7] or [r8]
[r5+0x14] = certain mode/type value
```

随后调用：

```text
FUN_00743b52(context + 0x52d8, context + 0x574 + 4, r5, ...)
```

这位于阶段内部函数中，是当前静态链离真实 DFE 控制 API 最近的一层。`FUN_00743b52` 是动作边界；尚未确认它内部是 MMIO 写、DMA kick 还是软件队列消息。

## 当前静态链

```text
param+0x23 event key
  -> FUN_006a4394
  -> FUN_006a43b2 / FUN_006a44a0 dispatcher
  -> FUN_0028d388 (Stage_DfeRawTrans)
  -> FUN_0028c514 (shared processing)
  -> FUN_00296884 (aligned size + context fields)
  -> FUN_00298b34 (descriptor / DFE command construction)
  -> FUN_00743b52 (DFE API boundary)
```

## 已证实

- `FUN_006a4394` 读取 `+0x23` 作为分派键。
- `FUN_006a43b2` 的 case 1 和 `FUN_006a44a0` 的 case 5 都进入 `FUN_0028d388`。
- `FUN_006a43b2` 会设置 `context+0x5774=1` 和 `context+0x5778=context+0x52dc`。
- `FUN_0028d388` 读取 `0x5594/0x5598/0x559c/0x55a0` 并建立描述符。
- `FUN_006a686a` 是四字段 setter，`FUN_006859ec` 是描述符复制函数。
- `FUN_00296884` 包含基于 `FUN_0068281e` 结果、按 `6/8` 相乘再 128 字节对齐的大小计算。
- `FUN_00298b34` 构造 0x14 字节左右的结构并交给 `FUN_00743b52`。

## 未证实

- `FUN_001d673c` / `FUN_00682796` 返回对象的精确定义。
- `6/8` 乘数是 bit depth、bytes-per-pixel、通道数还是其他单位。
- `FUN_00743b52` 是 DMA kick、MMIO 写、DFE 命令发送还是软件消息。
- `context+0x52dc` 是否就是 DMM/DMA 描述符。
- 真实 Bayer pattern、stride、packing、bit depth。
- 该链条是 Movie 连续 RAW 还是静拍/DualRec 专用。
- 是否已有帧时序、数据流和 SD/USB 输出证据。

## 产物

- `analysis_out/ghidra_stage_consumer_funcs_20260906.txt`
- `analysis_out/ghidra_dispatch_enum_20260906.txt`
- `analysis_out/avcam_internal_handlers_20260906.txt`
- `analysis_out/avcam_size_helpers_20260906.txt`
- `analysis_out/avcam_size_getter_20260906.txt`
- `docs/23_stage_consumer_audit_20260906.md`
## 补充：DFE API 边界（2026-09-06）

`FUN_00743b52` 反汇编显示它只是把参数转交给 `FUN_00743f54`。后者构造 0x30 字节参数结构，然后调用 `FUN_001dd460`。

`FUN_001dd460` 的反汇编包含：

- `FUN_001df4f4` 获取资源对象；
- `FUN_001dce70` / `FUN_001dceb0` 处理对象参数；
- `FUN_001dea5c`、`FUN_001dd204` 等后续对象/控制调用；
- 多个浮点除法与比率计算，例如 `r0 = [obj+0x30] / [obj+0x20]` 之类。

结论修正：

> 当前静态边界不是“DMA kick 已确认”，而是“DFE 描述符构造完成并交给高层 DFE/对象 API”。没有直接看到 MMIO 写或 DMA 控制寄存器访问。

因此本轮新增证据只能支持：

```text
RAW manager -> Stage_DfeRawTrans -> 156/256 对齐大小计算
            -> 描述符构造
            -> FUN_00743b52
            -> FUN_00743f54
            -> FUN_001dd460 (高层 API)
```

不能支持：

```text
... -> DMA target -> SD/USB
```

### 证据

- `analysis_out/avcam_dfe_submit_20260906.txt`
- `analysis_out/avcam_dfe_core_api_20260906.txt`
- `analysis_out/avcam_object_api_20260906.txt`

### 对象注册表复核

- `FUN_001df4f4` 遍历全局对象表（循环长度为 `0x5c`，按 4 字节步进），对每个槽调用 `FUN_00690324`，匹配后返回对象指针。
- `FUN_001dceb0` 的返回目标为 `0xb22f9e` 至 `0xb230d2` 附近的区域；这些区域在当前固件镜像中是全零 BSS/运行时槽，不是 MMIO 地址。
- 因此 `FUN_001dd460` 的底层动作更像对象表/资源 API，不是直接访问 DFE 硬件寄存器。

## 本轮新增产物

- `analysis_out/avcam_api_expanded_20260906.txt`
- `analysis_out/avcam_literal_map_20260906.txt`
