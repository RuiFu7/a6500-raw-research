# MPR DMAC 离线审计（2026-09-06）

## 范围

只解析 α6500 V1.06 `libmpr.so` 和 `dmac.ko`，不接触相机。本文件记录本次新增证据，修正“DMM 似乎与 DMAC 无关”的判断。

## 已证实：MPR 库打开并调用 DMAC

`libmpr.so` 包含 `/dev/dmac`、`DMAC_MEM_TRANSFER`、`dmac_request`、`lli_phys`、`DMACLIB` 等字符串，Ghidra 将相关函数定位为：

| 地址 | 行为 |
| --- | --- |
| `006c3c84` | 打开 `/dev/dmac`，执行 `fcntl(O_NONBLOCK)` |
| `006c3dec` | 构造 `{mode/type, request}`，通过 `ioctl` 提交 DMAC |
| `006c3da0` | DMAC 未配置时的等待/回退路径 |
| `006c4bb8` | 结束一个 DMAC 批处理 |
| `006c4bf2` | 把 0x20 字节描述符条目按 0x40000 字节分块，反复提交 |

`dmac_ioctl` 的静态入参检查为：

```text
arg[0] == 1
arg[1] 指向 { channel <= 7, descriptor/request 地址 }
```

`dmac.ko` 的 `dmac_mem_transfer_async` 读取请求 `+0x28`、`+0x2c` 等字段，加入异步队列，并调用中断/唤醒路径。该驱动确实有真实寄存器写入和等待完成逻辑。

## 已证实：DMM extent 查询闭环

`FUN_006a7d6a` 的高层同步调用把 `FUN_002e7e44` 返回的 0x70 字节响应复制到调用方。`FUN_002c2088` 保存字段与响应偏移的关系为：

```text
response + 0x04 = handle
response + 0x08 = extent count
response + 0x10 = extent 起始地址
response + 0x14 = extent size
```

这与 `0x1df` 实测 `address=0xa6000000`、`size=0x03000000` 一致。`0x1df` 的额外字段 `+0x5594` 被计算为 `align(size / 2, 0x80)`，与 2-pass/分半缓冲语义一致，但至今不能证明内容已经刷新为 Bayer。

## 高可信推测

`libmpr.so` 的 MPR 复制/流路径与 DMM extent 管理、`stream2` 物理映射和 DMAC 描述符提交属于同一套内存搬运基础设施。`MemInfo`/`DmmAccess` 查询 extent，随后把物理地址传给 `stream2` 或 DMAC。

## `Still Stream RAW Main` 已定位

`libmpr.so` 的静态 `.data` 面积表中：

```text
area type 0x53 = Still Stream RAW Main
table display address = 0xb69738
table actual address = 0xb59738
```

`FUN_006c6604` 使用该表打印 `Buf Info`，`FUN_006c6498` 按类型 ID 返回 label。因此该字符串不是孤立日志，而是 MPR memory-map/buffer 表里一个可索引的面积类型。可用 `tools/mpr_area_map.py` 提取完整 ID-label 表，输出 `analysis_out/mpr_area_table_20260906.json`。

## 新的离线闭环片段

`FUN_006c8ca0` 是 DMM 单元打开/分配包装层，随后 `FUN_006c8a2c` 和 `FUN_006c5658` 把 DMM 单元/物理 extent 组装为 MPR area 描述符。`FUN_006c5484` 进一步：

1. 从 area 描述符读取 extent 数组；
2. 构建 `{phys,size}` 表；
3. 调用 `FUN_006c7424`，通过 `/dev/stream2` `ioctl 0xC0047805` 和 `mmap` 建立 MPR 可访问虚拟地址。

这已经把“MPR area 类型 -> DMM/extent -> stream2 物理映射”连到了应用层，和之前确认的 `/dev/dmac` 描述符提交位于同一 MPR 基础设施内。

该推测必须继续确认 area type `0x53` 的分配调用者和 DMM unit 映射，再判断它是否被上述 DMAC 路径消费。

## DMM unit `0x23a` 与 MPR area `0x53`

对照 α6300 和 α6500 的 `libmpr.so` 静态表：

| 固件 | `Still Stream RAW Main` 的 MPR area ID |
| --- | --- |
| α6500 V1.06 | `0x53` |
| α6300 V2.01 | `0x52`（无 `Meta Buffer 2` 一项，后续 ID 相应前移） |

两条固件都在 `CopyReadStillStream` 中直接调用 `FUN_006c8ca0(0x23a, ...)`。`FUN_006c8ca0` 再调用 DMM 打开/分配包装 `FUN_006cb85c`，因此下面路径可以静态闭合到 DMM unit 层：

```text
MPR still-stream RAW path
  -> unit type 0x23a
  -> FUN_006c8ca0 -> FUN_006cb85c
  -> DMM cmd=1 alloc, cmd=2 open
  -> DMM response handle/extent
  -> FUN_006c8a2c -> FUN_006c5658 -> FUN_006c5484
  -> {phys,size} -> FUN_006c7424 -> /dev/stream2 mmap
```

`FUN_006cb498` 是 `Mem_DmmAccess::SendAndReceiveDmmMsg`。DMM 请求/响应布局由 `FUN_006cb428`、`FUN_006cb438`、`FUN_006cb440`、`FUN_006cb44c`、`FUN_006cb458` 确认：

```text
request +0x00 = DMM command (1=alloc, 2=open, 4=free, 6=close)
request +0x04 = unit type / handle
request +0x08..+0x0c = options / requested fields
response +0x04 = unit handle
response +0x08 = extent count
response +0x10 + i*8 = extent address
response +0x14 + i*8 = extent size
```

因此 `0x23a` 是可以直接放入下一阶段只读观察的 DMM unit type 候选，比之前只列 `0x236/0x1df/0x23e/0x2b3` 更具体。仍不能据此认为 `0x23a` 就是传感器像素帧；它至少是 MPR “Still Stream RAW Main” 的内存单元入口。

## 仍未证实

- `Still Stream RAW Main` 的实际 unit type 和分配大小。
- `0x1df`、`0x236`、`0x23e` 是否最终进入 DMAC。
- `Stage_DfeRawTrans` 与 `libmpr.so` DMAC 调用者之间是否存在共同句柄。
- Bayer pattern、packing、位深、帧宽和帧时序。
- 是否有 Movie 连续 RAW 通路。

## 产物

- `analysis_out/mpr_dmac_xrefs_20260906.tsv`
- `analysis_out/mpr_dmac_core_20260906.txt`
- `analysis_out/mpr_dmac_callers_20260906.txt`
- `analysis_out/mpr_dmac_callgraph_20260906.txt`
- `analysis_out/mpr_dmm_copy_ops_20260906.txt`
- `analysis_out/dmm_ext_tbl_annotated_20260906.txt`
- `analysis_out/dmac_reloc_annotated_20260906.txt`
- `analysis_out/mpr_area_table_20260906.json`
- `analysis_out/mpr_dmmaccess_wrappers_20260906.txt`
- `analysis_out/mpr_unit_ca0_callers_20260906.txt`
