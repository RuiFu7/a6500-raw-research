# XDMAC 与 DFE HDMAC 的硬件身份判定（2026-09-06）

## 结论

已从内核 `vmlinux.bin` 的 `udif_platform_register` 平台设备表中定位到 `dmac` 设备，并读出其 8 个资源项。`/dev/dmac` 使用的 XDMAC 基址与 av-cam 侧 DFE HDMAC 不是同一组寄存器地址，不能把二者直接视为同一个控制器。

当前证据下的名称对应关系：

```text
内核平台设备 "dmac"         -> 自定义 /dev/dmac / XDMAC
内核 AMBA 设备 "pl08xdmac"  -> 标准 PL08X DMA（另一条路径）
av-cam "HDMAC"              -> DFE 内部硬件 DMA（基址 0xfc000000）
```

## 已证实：`dmac` 平台设备及资源表

`FUN_403b2d38` 遍历 `0x403f497c` 开始的平台设备表，每条记录 0x28 字节。`dmac` 是第 3 项：

```text
表项地址   0x403f49f4
名称       "dmac"
资源数量   8
资源指针   0x403f5588
```

资源表每项 0x5c 字节，名称分别是：

```text
dmac_ch0
dmac_ch1
dmac_ch2
dmac_ch3
dmac_ch4
dmac_ch5
dmac_ch6
dmac_ch7
```

`dmac_probe @ 0x8d0` 读取 `pdev->resource`，按 0x5c 索引资源项，并取 `resource+0x10` 作为通道基址写入全局表。得到的 8 个通道基址为：

| 通道 | 基址 | 通道寄存器基址（`boss_lld_get_base_addr_dmac_ch`） |
| --- | --- | --- |
| 0 | `0xf0000000` | `0xf0000010` |
| 1 | `0xf0000000` | `0xf0000040` |
| 2 | `0xf0000000` | `0xf0000070` |
| 3 | `0xf0000000` | `0xf00000a0` |
| 4 | `0xf0010000` | `0xf0010010` |
| 5 | `0xf0010000` | `0xf0010040` |
| 6 | `0xf0010000` | `0xf0010070` |
| 7 | `0xf0010000` | `0xf00100a0` |

推导依据：

```text
channel <= 3: base = global_base(channel)
                 + 0x30 * channel + 0x10
channel >= 4: base = global_base(channel - 4)
                 + 0x30 * (channel - 4) + 0x10
```

因此 XDMAC 的通道布局是“每组 4 通道、组内 `0x30` 步长”，不是 av-cam HDMAC 的“每通道 `0x10` 步长”。

## 已证实：DFE HDMAC 基址和访问方式

`FUN_001d9554` 的源码及反汇编直接写入：

```text
0xfc000000 + 0x1d000 + channel * 0x10
```

可见的寄存器字段包括：

```text
+0x00
+0x04
+0x08
+0x0c
+0x10
+0x14
+0x18
+0x1c
```

`FUN_0068da4e` 写入 `*param_2`，`FUN_0068da5a` 写入 `param_2[1]`，随后通过 `FUN_0068da12/FUN_0068da20` 发送控制字和大小/状态字。

## 证据等级

| 结论 | 等级 |
| --- | --- |
| 内核 `dmac` 平台设备项为 `0x403f49f4`，资源表为 `0x403f5588` | 已证实 |
| 资源表包含 8 个 `dmac_ch0..7` 项 | 已证实 |
| `dmac_probe` 使用 `pdev->resource + index*0x5c + 0x10` 存基址 | 已证实（代码级） |
| XDMAC ch0-3 基址为 `0xf0000000`，ch4-7 为 `0xf0010000` | 已证实（静态静态资源表 + 反汇编） |
| XDMAC 通道组内步长为 `0x30` | 已证实 |
| av-cam DFE HDMAC 基址为 `0xfc000000 + 0x1d000 + ch*0x10` | 已证实 |
| 该 HDMAC 就是内核 `dmac.ko` 的 XDMAC | 否定（当前证据） |
| XDMAC 与 DFE HDMAC 一定是两个完全不相干的硬件 | 高可信推测，仍有 SoC 别名/地址转换的残余不确定性 |

## 为何不能继续直接画等号

1. 地址窗口不同：XDMAC 资源表明确是 `0xf0000000` 和 `0xf0010000`；DFE HDMAC 是 `0xfc000000`。
2. 通道步长不同：XDMAC 是 `0x30`，DFE HDMAC 是 `0x10`。
3. 资源命名不同：平台设备表和 `boss_lld` 是 `dmac_ch0..7`；DFE 路径没有使用这组 `dmac_chN` 资源名。
4. 框架不同：`dmac.ko` 走 UDIF `/dev/dmac` 字符设备和 `boss_lld`；DFE 路径位于 av-cam 应用/固件内部，直接使用 `0xfc000000`。

旧文档中“DFE HDMAC 与 `/dev/dmac` XDMAC 是否同一硬件：未证实”现在应升级为：按现有静态证据，二者不是同一条已证实路径，直接等价为“否定”。

## 产出

- `analysis_out/ghidra_kernel_udif_platform_words_20260906.txt`
- `analysis_out/ghidra_kernel_dmac_resources_20260906.txt`
- `analysis_out/ghidra_cxd90014_literals_20260906.txt`
- `analysis_out/ghidra_cxd90014_init_annotated_20260906.txt`
- `analysis_out/avcam_hdmac_literals_20260906.txt`
- `analysis_out/avcam_hdmac_functions_20260906.txt`
- `analysis_out/avcam_dfe_hdmac_chain_20260906.txt`
- `analysis_out/dmac_probe_annotated_20260906.txt`

## 下一步

不再把 `sensor -> DFE -> HDMAC -> /dev/dmac` 当成一条已闭合链。下一项工作应是分别确认两条路径的最终目的：

1. DFE HDMAC 的源/目标地址来自哪个对象，以及是否就是 DMM extent。
2. `libmpr.so` 的 `/dev/dmac` 请求是否消费 `Still Stream RAW Main`。
3. 若两者都不构成同一 DMA 链，再验证 DFE RAW 是否直接落到内部 SRAM，再由另一条总线/处理器搬运。
