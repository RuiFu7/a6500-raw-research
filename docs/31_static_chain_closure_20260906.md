# DFE / DMM / XDMAC 静态调用链闭合审计（2026-09-06）

## 目标

验证是否能把：

```text
DFE RAW Stage
  -> DMM extent
  -> XDMAC / /dev/dmac
```

作为一条可复核的连续调用链闭合。

## 审计结论

当前静态证据不能证明上述顺序链存在。更准确的结构是：

```text
DFE RAW Stage -> DFE HDMAC（内部）
DMM allocator  -> DFE buffer lifecycle（相邻，非传入 HDMAC）
MPR Still RAW -> DMM -> stream2 -> memcpy（无 DMAC）
MPR MP4 Mux -> DMAC / /dev/dmac（无 RAW 单元证据）
```

因此：

| 假设 | 等级 |
| --- | --- |
| `Stage_DfeRawTrans` 直接接收 DMM extent 并交给 HDMAC | 否定（当前证据） |
| `MPR Still RAW 0x23a` 使用 `/dev/dmac` | 否定（当前证据） |
| `MP4 Mux` 使用 `/dev/dmac` | 已证实 |
| `MP4 Mux` 的缓冲区已被证明是 DMM `0x23a`/RAW extent | 未证实 |
| DFE HDMAC 与内核 XDMAC 同一硬件 | 否定（当前证据） |

## 一、DMM 分配

`FUN_002c2088` 是 RAW 内存管理器：

```text
unit type
  -> FUN_006a7d6a / FUN_006a7c84
  -> DMM request
  -> response handle + extent
  -> +0x5598 = unit type
  -> +0x559c = extent 首址
  -> +0x55a0 = extent 大小
  -> +0x5594 = 0x1df 的 align(size/2, 0x80)
```

该路径已闭合到 DMM 驱动层。

## 二、DFE Stage 与 DMM 的关系

`FUN_0028d388` 执行顺序：

```text
FUN_006a5004(local_48)
FUN_0029d828 / FUN_0029d944
FUN_0028bcd4
FUN_0028c514(param_1, local_48)
FUN_002c12b4(param_1, 1)
```

关键点是：

1. `FUN_0028c514` 收到的 `local_48` 被 `FUN_006a5004` 初始化为模式/句柄结构，字段为 0 或 `-1`。
2. `FUN_0028c514` 内部没有读取 `param_1 + 0x5594/+0x5598/+0x559c/+0x55a0`。
3. `FUN_0028c514` 通过 `FUN_0072d4ce -> FUN_0072d226 -> FUN_0072dd40 -> FUN_00482180 -> FUN_001d9554` 启动 DFE HDMAC。
4. DMM 字段在 `FUN_0028c514` 返回后才由 `FUN_002c12b4` 读取、轮转和释放。

因此 DFE HDMAC 的输入描述符来自 DFE 内部对象，不是直接来自 DMM extent。DMM 是相邻的生命周期管理路径，而不是 HDMAC 的源地址参数。

## 三、DMM 生命周期

`FUN_002c12b4(param_1, 1/2)` 读取：

```text
+0x5594
+0x5598
+0x559c
+0x55a0
+0x5584
+0x5588
+0x558c
+0x5590
```

然后与环形槽 `(param_1 + 0x2900 + index*2 + 4)` 交换，更新：

```text
+0x22c
+0x230
+0x5204
```

`FUN_006adb10` 在对应槽位完成后清零 DMM 字段并调用 `FUN_006a7cbc`。

这证明 DMM 的主要角色是“多帧缓冲/环回管理”，不是作为 DMA 源写入 DFE HDMAC。

## 四、MPR Still RAW 与 DMAC

`PlayJpegThum/PlayStill::CopyReadStillStream` 调用：

```text
FUN_006c8ca0(0x23a)
  -> FUN_006cb85c
  -> DMM open/alloc
  -> FUN_006c8a2c
  -> FUN_006c5658
  -> FUN_006c5484
  -> FUN_006c7424
  -> /dev/stream2 ioctl + mmap
FUN_006c89a4
FUN_001828e0 -> memcpy
```

`FUN_001828e0` 已确认是 `memcpy`。`CopyReadStillStream` 没有直接或间接调用：

```text
FUN_006c3c84
FUN_006c3dec
FUN_006c4bf2
```

所以 MPR `0x23a` Still RAW 候选是“DMM + stream2 + memcpy”路径，不是 XDMAC 路径。

## 五、MPR MP4 Mux 与 DMAC

`FUN_006c4bf2` 只有两个静态调用者：

```text
FUN_005519f4 (MP4 MultiplexFilter)
FUN_0055a254 (MP4 MultiplexFilter)
```

该类的原始 vtable 位于 `0x9a5390`，RTTI 字符串为 `MP4MultiplexFilter`；Ghidra 项目地址为 `0x9b5390`。

它们调用：

```text
FUN_006c4bf2
  -> FUN_006c3dec
  -> ioctl(/dev/dmac)
```

该路径围绕“写信息列表、视频写入信息、元数据写入”构建。它是确认的 `/dev/dmac` 消费路径，但当前没有字段级证据证明它消费 `0x23a`、`Still Stream RAW Main` 或 DMM RAW extent。

### 5.1 已发现的 DMM 内存区 -> `/dev/dmac` 通用桥

`FUN_00552390` 是 MP4 Mux 初始化函数，调用：

```text
FUN_00552390
  -> FUN_006c4020
  -> FUN_006c3c84 -> open("/dev/dmac")
```

`FUN_006c4020` 的第 2 个参数来自 `linkListAreaAdr`，第 3 个参数是 `linkListAreaSize`，并且：

```text
FUN_00346288(base, ..., offset) = base - offset
```

它把计算后的基址存到 DMAC 对象：

```text
param_1[0] = base
param_1[1] = base - offset
param_1[2] = size >> 5
```

`FUN_00552390` 的调用者位于原始 `libmpr.so` `0x00356f2e`（Ghidra 地址 `0x00366f2e`），初始化结构从 `obj+0x74` 的字段复制，包括：

```text
+0xa8
+0xb0
+0xb8
```

因此存在一条“内存区域地址 -> MP4 Mux DMAC 对象 -> `/dev/dmac`”的静态路径。该路径已闭合到驱动入口，但还不能证明该内存区域就是 DMM RAW 单元 `0x23a`。

这比“DMAC 只是未关联设施”更强：至少 DMM/MPR 内存区域和 XDMAC 的用户接口之间有一个已经定位的桥。

## 六、XDMAC 与 DFE HDMAC

内核平台设备表：

```text
"dmac"
  resources = 0x403f5588
  ch0..3     = 0xf0000000
  ch4..7     = 0xf0010000
  ch stride  = 0x30
```

DFE HDMAC：

```text
0xfc000000 + 0x1d000 + channel * 0x10
ch stride = 0x10
```

现有证据不能证明二者是同一控制器。

## 七、最终静态结论

如果“闭合”定义为证明一条连续调用链，则结果是 **否定**：

```text
DFE RAW Stage -> DMM -> XDMAC
```

不存在可复核的直接或间接静态证据链。当前证据把三部分分开：

```text
DFE 内部处理
DMM 多帧管理
MPR/MP4 DMAC 输出
```

这比“尚未找到中间调用”更进一步：我们已经能证明 DMM 字段不是 `FUN_0028c514` 的 HDMAC 入参，并证明 MPR 两条路径使用的是不同设施。

## 八、若目标改为 RAW 数据通路

下一步不应继续尝试把 DFE HDMAC 与 `/dev/dmac` 接起来。应按排序验证：

1. MPR `0x23a` / DMM + stream2 的静态可读区域。
2. MP4 DMAC 请求的描述符是否携带 `MemInfo` 的物理 extent。
3. DFE `0xf3000000` 内部缓冲区是否被另一个任务复制到 DMM。

当前阶段仍不接触相机、不做 RAM patch、不写固件。

## 产出

- `analysis_out/avcam_dmm_consumer_refs_20260906.txt`
- `analysis_out/avcam_dmm_lifecycle_20260906.txt`
- `analysis_out/mpr_copy_function_001828e0_20260906.txt`
- `analysis_out/mpr_dmm_dmac_refgraph_20260906.txt`
- `analysis_out/mpr_xavc_refs_20260906.txt`
- `analysis_out/mpr_dmac_function_contexts_20260906.txt`
- `analysis_out/ghidra_raw_stage_funcs_full_20260905.txt`
