# DFE RAW 传输到 HDMAC 硬件链已闭合（2026-09-06）

## 结论

离线静态分析已找到从 DFE RAW 传输阶段到 HDMAC 硬件的直接调用链：

```text
FUN_0028d388 (Stage_DfeRawTrans)
  -> FUN_0028c514
  -> FUN_0072d4ce 或 FUN_0072d558
  -> FUN_0072d226
  -> FUN_0072dd40
  -> FUN_00482180
  -> FUN_0068db2c
  -> FUN_001d9554
  -> FUN_0068da36/da20/da12/da2e/da4e/da5a (DFE HDMAC 寄存器访问)
```

该路径不是“同时存在”的推测，而是调用点交叉引用已确认。

这里的“闭合”只表示 DFE 内部的软件调用和 HDMAC MMIO 入口已定位；不表示已经证明输出的是 Bayer RAW，也不表示它与 Linux `/dev/dmac` 的 XDMAC 是同一硬件。详见 `docs/28_xdmac_hdmac_identity_20260906.md` 和 `docs/29_dfe_internal_memory_and_dmm_separation_20260906.md`。

命名说明：av-cam 侧字符串把该 DMA 称为 `HDMAC`，内核 `dmac.ko` 字符串称为 `XDMAC`。当前能证明的是 DFE 侧存在一条 HDMAC 硬件启动链；`dmac.ko` 的 XDMAC 基址/寄存器布局与 av-cam `0xfc000000` HDMAC 布局是否完全相同，仍未通过静态证据收敛。

同一条 DFE 路径的 DMM 侧证据：

```text
FUN_002c1ab0 -> RAW unit type
  -> FUN_002c2088 -> DMM alloc/reuse
  -> context +0x5594/+0x5598/+0x559c/+0x55a0
  -> FUN_0028d388 -> FUN_0028c514
  -> HDMAC
```

因此这里的 HDMAC 不是普通 MPR 内存搬运动作，而是 DFE RAW 描述符之后的目标。

## 已证实的具体调用点

### Stage -> shared processor

`FUN_0028d388` 的 `CALLERS` 中出现 `0028d5e2 -> 0028c514` 等调用。`FUN_0028c514` 主体内：

```text
0028c514  FUN_0028c514 entry
0028cd48  bl 0x0072d4ce
0028cd5e  bl 0x0072d558
```

### shared processor -> HDMAC setup

`FUN_0072d4ce` 和 `FUN_0072d558` 都调用：

```text
0072d54e  bl 0x0072d226
0072d5cc  bl 0x0072d226
```

`FUN_0072d5d6` 是第三入口，也从其他 DFE 调用上下文进入同一函数。

`FUN_0028c514` 的分支为：

```text
context +0x7c8 == 1: FUN_0072d4ce
context +0x7c8 == 2: 满足附加条件时 FUN_0072d4ce，否则 FUN_0072d558
其他：FUN_0072d558
```

这表示 HDMAC 启动不是无条件，而是由 DFE 状态选择具体转移模式。

### HDMAC setup -> transfer descriptor

`FUN_0072d226` 调用：

```text
0072d428  bl 0x0072dd40
0072d4be  bl 0x0072dd40
```

### descriptor -> HDMAC functional API

`FUN_0072dd40` 调用 `FUN_00482180`：

```text
0072dde4  bl 0x00482180
```

### functional API -> low-level transfer

`FUN_00482180` 调用 `FUN_0068db2c`，后者调用：

```text
0068db32  bl 0x001d9554
```

### MMIO

`FUN_001d9554` 内直接调用：

```text
0068da36  bl 0x0068da36   # 状态检查
0068da20  bl 0x0068da20   # 写入控制/状态
0068da12  bl 0x0068da12
0068da2e  bl 0x0068da2e
0068da4e  bl 0x0068da4e
0068da5a  bl 0x0068da5a
```

`FUN_001d9554` 的参数结构：

- 通道 0..4；
- 源/目标地址；
- 大小；
- 回调；
- 控制标志。

该函数是 DFE HDMAC 的寄存器级启动路径。

## 证据等级

| 结论 | 等级 |
| --- | --- |
| `Stage_DfeRawTrans` 调用 `FUN_0028c514` | 已证实 |
| `FUN_0028c514` 调用 `FUN_0072d4ce` / `FUN_0072d558` | 已证实 |
| `FUN_0072d4ce` / `FUN_0072d558` 调用 `FUN_0072d226` | 已证实 |
| `FUN_0072d226` 调用 `FUN_0072dd40` | 已证实 |
| `FUN_0072dd40` 调用 `FUN_00482180` | 已证实 |
| `FUN_00482180` 调用 `FUN_0068db2c` | 已证实 |
| `FUN_0068db2c` 调用 `FUN_001d9554` | 已证实 |
| `FUN_001d9554` 直接写 DFE HDMAC 寄存器 | 已证实（代码级） |
| 该转移一定产生 Sony Bayer RAW 像素 | 未证实（需运行时抓取验证） |
| 该 HDMAC 通道一定使用 `0x236/0x1df/0x23e/0x2b3` 之一 | 未证实 |
| DFE HDMAC 与 `/dev/dmac` 的 XDMAC 是同一硬件 | 未证实 |

## 意义

这条链证明 DFE RAW 阶段确实具备：

```text
RAW 状态/描述符
  -> DMM 分配
  -> DFE 资源管理
  -> HDMAC 硬件启动
```

下一阶段不再需要猜测 DFE 是否只停留在软件 API。运行时实验可以沿这条链抓取 HDMAC 源/目标地址，再验证数据是否为 Bayer。

## 产物

- `analysis_out/ghidra_stage_consumer_funcs_20260906.txt`
- `analysis_out/avcam_hdmac_functions_20260906.txt`
- `analysis_out/avcam_hdmac_refs_20260906.txt`
- `analysis_out/avcam_hdmac_callers_20260906.txt`
- `analysis_out/avcam_hdmac_wrappers_20260906.txt`
- `analysis_out/avcam_hdmac_wrappers_refs_20260906.txt`
- `analysis_out/avcam_xdmac_xrefs_20260906.tsv`
- `analysis_out/avcam_dmm_to_hdmac_chain_20260906.txt`

## 剩余离线任务

1. ~~解析 `dmac.ko` 的 `udif_devices/udif_devnodes` 或内核平台资源表~~：已完成，见 `docs/28_xdmac_hdmac_identity_20260906.md`。
2. ~~对比通道基址/寄存器偏移~~：已完成；XDMAC 使用 `0xf0000000/0xf0010000` 和 `0x30` 步长，DFE HDMAC 使用 `0xfc000000` 和 `0x10` 步长。
3. 结论更新：当前静态证据下，DFE HDMAC 与 `/dev/dmac` XDMAC 的“同一硬件”关系为否定；两者不是同一条已闭合路径。
4. 下一步改为追踪 DFE HDMAC 的源/目标地址来自哪个对象，并确认 `libmpr.so` 的 `/dev/dmac` 请求是否消费 `Still Stream RAW Main`。
