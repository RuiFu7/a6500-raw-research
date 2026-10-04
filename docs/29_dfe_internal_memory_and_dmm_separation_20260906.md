# DFE 内部内存与 DMM 数据空间的分离（2026-09-06）

## 结论

α6500 固件里至少同时存在三类内存/IO 地址空间：

1. `0xf3000000`：DFE 对象初始化使用的一段内部内存基址。
2. `0xfc000000`：DFE HDMAC 硬件控制基址。
3. DMM 返回的动态 extents：由 `FUN_002c2088` 保存到 RAW 管理对象 `+0x5594/+0x5598/+0x559c/+0x55a0`。

`Stage_DfeRawTrans` 会读取 DMM 字段和 DFE 对象字段，并通过 `FUN_00298b34 -> FUN_00743b52 -> FUN_00743f54 -> FUN_001dd460` 构造后续 DFE 描述符；但 DFE HDMAC 本身的寄存器地址是 `0xfc000000`，不是 `/dev/dmac` 的资源地址 `0xf0000000/0xf0010000`。

## 已证实：DFE 对象使用 `0xf3000000`

`FUN_002c2234 @ 0x002c2234` 初始化大 DFE 上下文，随后调用：

```text
FUN_002bd864
```

`FUN_002bd864 @ 0x002bd864` 中：

```text
if (global_flag & 0x2):
    FUN_001d2598(dst, 1, 0xf3000000)
    FUN_001d1f40(dst + 0x?)
else:
    FUN_001d2598(dst)
```

`FUN_001d2598 @ 0x001d2598` 以第 3 参数作为对象基址，填充一组指针和长度：

| 对象偏移 | 赋值 | 长度 |
| --- | --- | --- |
| `+0x4bc` | `base` | `0x5c` |
| `+0x4c8` | `base + 0x5c` | `0x4c` |
| `+0x4d4` | `base + 0xa8` | `0x2a4` |
| `+0x4e0` | `base + 0x34c` | `0x84` |
| `+0x4f8` | `base + 0x49c` | `0x70` |
| `+0x504` | `base + 0x50c` | `0x8c` |

`FUN_0072d4ce @ 0x0072d4ce` 和 `FUN_0072d558 @ 0x0072d558` 在启动 HDMAC 前读取：

```text
*(param_1 + 0x4c8)
```

因此 `Stage_DfeRawTrans` 使用的 DFE 对象地址来自 `0xf3000000` 布局，不单纯来自 DMM 分配响应。

## 已证实：DMM 字段分别保存在 RAW 管理对象

`FUN_002c2088 @ 0x002c2088` 是 RAW 内存管理器：

```text
FUN_006a7d6a 或 FUN_006a7c84
-> DMM 请求
-> 返回 handle / extent
-> 保存到对象
```

保存关系：

```text
+0x5598 = unit type
+0x559c = extent 地址
+0x55a0 = extent 大小
+0x5594 = 对 0x1df 特殊计算 align(size/2, 0x80)
```

`FUN_0028d388 @ 0x0028d388` 在调用 `FUN_0028c514` 前读取这些字段，并把 `param_1+0x559c`、`param_1+0x558c` 放入局部描述符。因此 DMM 路径至少参与 Stage DFE RAW 描述符构造；不能把 DMM 字段和 DFE 内部字段混成同一个对象。

## 已证实：DFE HDMAC 与 DMM 不是同一个地址空间

DFE HDMAC 调用链：

```text
FUN_0028c514
  -> FUN_0072d4ce / FUN_0072d558
  -> FUN_0072d226
  -> FUN_0072dd40
  -> FUN_00482180
  -> FUN_0068db2c
  -> FUN_001d9554
  -> 0xfc000000 MMIO
```

`FUN_001d9554` 明确写 `0xfc000000`，并且通道基址按：

```text
0xfc000000 + 0x1d000 + channel * 0x10
```

DMM extent 实测地址是类似 `0xa6000000` 的动态 DRAM 区域；DFE 内部基址是 `0xf3000000`；因此三者不能视为同一个连续缓冲。

## 还未证实

- DMM extent 地址是否直接作为 `FUN_001d9554` 描述符的源地址。
- `0xf3000000` 是否包含 Bayer 像素或只包含 DFE 控制/描述块。
- `FUN_001dd460` 到 `FUN_001d9554` 之间哪个参数字段是 DMM 物理地址。
- 这条 DFE HDMAC 是否最终把数据送到 `libmpr.so` 的 `/dev/dmac` 路径。

## 对后续分析的影响

后续不要用“DFE HDMAC 等于 `/dev/dmac`”来推导缓冲区。应先分别回答：

1. `FUN_00482180` 的 `local_34` 是从哪里取得的。
2. `FUN_001dd460` 的 `param_3` 结构里哪个字段是 DMM extent。
3. `FUN_00298b34` 写入 `[r5]`、`[r5+0x10]`、`[r5+0x14]` 的字段语义。
4. `0xf3000000` 区域的头/数据布局和大小。

## 补充：DFE HDMAC 描述符实际指向内部配置表

`FUN_0072d226` 调用 `FUN_001e9710` 构造 0x94 字节描述符；`FUN_001e9710` 通过 `FUN_00693984`、`FUN_00693716`、`FUN_00693ac8` 和 `FUN_00692292` 访问 DFE 全局配置/帧描述表，并用 `FUN_001e93e8` 生成 packed flag word。该函数没有直接读取 `FUN_002c2088` 保存的 `+0x5594/+0x5598/+0x559c/+0x55a0` DMM 字段。

`FUN_001e94c4` 进一步修改 DFE 内部描述表（`FUN_00692292` 返回对象的 `+0x34` 表）和 `FUN_00693ac8` 返回的两个缓冲区，并调用 `FUN_00693bfc` 提交配置。它看起来是 DFE/BIONZ 内部处理资源，不是 Linux `/dev/dmac` 的 UDIF 请求。

因此当前应把：

```text
DFE_RAW_Stage -> DFE HDMAC
```

和：

```text
MPR -> /dev/dmac -> XDMAC
```

作为两条潜在证据链分别维护。`Stage_DfeRawTrans` 的 HDMAC 入口可以证明 DFE 硬件会被启动，但不能证明它把 Bayer 像素交给 Linux `dmac.ko`。

## 产出

- `analysis_out/ghidra_stage_consumer_funcs_20260906.txt`
- `analysis_out/ghidra_raw_stage_funcs_full_20260905.txt`
- `analysis_out/avcam_dfe_mem_init_001d2214_20260906.txt`
- `analysis_out/avcam_dfe_mem_init_caller_20260906.txt`
- `analysis_out/avcam_offset_4c8_writers_20260906.txt`
- `analysis_out/avcam_hdmac_functions_20260906.txt`
- `analysis_out/avcam_rawmanager_dfesetup_20260906.txt`
