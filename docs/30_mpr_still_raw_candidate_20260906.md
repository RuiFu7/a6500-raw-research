# MPR `0x23a` Still RAW 读取候选（2026-09-06）

## 结论

`libmpr.so` 中存在一条已经静态闭合的、可读回 `Still Stream RAW Main` 的 MPR 路径。它的 DMM unit type 是 `0x23a`，但与 `FUN_006c3dec` 的 `/dev/dmac` 路径没有直接调用关系。

这是一条“把 DMM extent 映射到 MPR 用户空间后再复制”的路径，不是一条已经证明的连续视频 DMA 路径。它仍然是下一阶段只读实验中最值得优先验证的静态候选。

## 已证实：静态调用链

```text
PlayJpegThum::CopyReadStillStream
  -> FUN_006c8ca0(0x23a, 0xffffffff, &handle)
  -> FUN_006cb85c
  -> DMM alloc/open wrapper
  -> FUN_006c8a2c(0x23a, handle)
  -> FUN_006c5658
  -> FUN_006c5484
  -> FUN_006c7424
  -> /dev/stream2 ioctl + mmap
  -> FUN_006c89a4(handle, &addr, &size)
  -> FUN_001828e0(addr, dst)
```

关键调用点：

```text
00387da4  movw r0,#0x23a
00387da8  mov.w r1,#0xffffffff
00387db0  bl 0x006c8ca0
00387dd2  bl 0x006c89a4
00387df6  bl 0x001828e0
```

`FUN_006c8a2c` 从 DMM handle 读取 extent 数量，并构造 `{phys, size}` 数组；随后：

```text
FUN_006c5658 -> FUN_006c5484 -> FUN_006c7424
```

`FUN_006c7424` 调用：

```text
/dev/stream2
ioctl 0xC0047805
mmap
```

然后把返回的虚拟地址交给 MPR。因此 `0x23a` 的 DMM extent 在应用层是可读的；这与之前只发现“某个 DMM handle”不同。

## 已证实：`0x23a` 是 Still RAW 的静态单元类型

`PlayJpegThum::CopyReadStillStream` 和 `PlayStill::CopyReadStillStream` 都：

```text
FUN_006c8ca0(0x23a, 0xffffffff, ...)
```

MPR 静态 area 表同时存在：

```text
type 0x53 = Still Stream RAW Main
```

这使 `0x23a` 成为“Still RAW Main”的 DMM unit 候选，但仍是候选，不是已证实 Bayer 像素。

## 已证实：`0x23a` 路径不调用 `/dev/dmac`

`CopyReadStillStream` 的静态调用图经 `FUN_006c8ca0 -> FUN_006c8a2c -> FUN_006c5658 -> FUN_006c5484 -> FUN_006c7424`，没有进入：

```text
FUN_006c3c84 -> open("/dev/dmac")
FUN_006c3dec -> ioctl(/dev/dmac)
FUN_006c4bf2 -> 0x20-byte descriptor chunking
```

因此不能把 `0x23a` 的 DMM/stream2 映射路径和 `Xavc`/MPR 输出路径合并成同一条 DMA 证据链。

## 对实机实验的意义

这条路径适合作为“Still RAW 抓取”的第一个候选：

1. 触发一张照片/回放仍图，并让 `CopyReadStillStream` 被调用。
2. 读取 `0x23a` 的 DMM/MPR extent 地址和大小。
3. 从 `FUN_006c7424` 得到的 mmap 虚拟地址读回数据。
4. 用不同画面、ISO、快门、白平衡做对照。
5. 只有通过 Bayer pattern、unpack、debayer 和图像语义验证后，才可升级为“已证实”。

它不能直接证明连续 Movie RAW，也不能证明 `3K/10-bit/25fps` 持续写入。

## 尚未证实

- MPR area type `0x53` 与 DMM unit type `0x23a` 的运行时一一对应。
- `0x23a` extent 大小、stride、packing 和 bit depth。
- `0x23a` 数据是否含 Bayer pattern。
- `0x23a` 是否能在连续录像过程中持续分配而不被释放。
- `Still Stream RAW Main` 是否会进入 `/dev/dmac`。

## 产出

- `analysis_out/mpr_unit_ca0_callers_20260906.txt`
- `analysis_out/mpr_dmm_copy_ops_20260906.txt`
- `analysis_out/mpr_dmm_dmac_refgraph_20260906.txt`
- `analysis_out/mpr_dmm_mapping_full_20260906.txt`
- `analysis_out/mpr_area_table_20260906.json`
