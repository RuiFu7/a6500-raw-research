# DFE 资源编号与 2-pass 内存分配（离线还原）

> 本文件只记录离线分析证据；尚未实机执行任何 ioctl / mmap / 内存读取。
> 依据：`av-cam.bin`（Ghidra `a6500_v106` 项目）。

## 1. DFE 资源编号映射 FUN_00690242

把模式（mode）映射到 DFE 资源编号：

| 模式值 | 资源编号 |
| --- | --- |
| 0x00, 0x04 | 0x25 |
| 0x15, 0x1b, 0x1e | 0x23 |
| 0x16, 0x2b, 0x47, 0x58 | 0x2e |
| 0x1c | 0x24 |
| 0x1d | 0x38 |
| 0x1a, 0x17..0x18 | 0x22 / 0x37 |
| 0x3a, 0x68 | 0x25 |
| 0x56 | 0x23 |
| 0x69, 0x6d | 0x2a 或 0x2f（按 bit0 判定） |
| 0x21 | 0x37 |
| 其他 | 0 |

这些资源编号对应 DFE core 的 drive/Zaf/Snr/Store/Trans 资源集合；具体编号到缓冲区的映射需运行时确认。

## 2. getDfeCoreResouces FUN_001df528

- 读取 DFE 驱动状态字节 `+0x21` 的 bit0/1/4/5，组织两个标志字节。
- 调用 `FUN_00690242(param_1, &flags)` 取得资源编号。
- 失败时打印 `driveMode/Zaf/Snr/Store/Trans` 五个布尔位。

## 3. AllocDfeMemForDfe2Pass FUN_005a2618

- 组装 0x10 字节请求头（unit_id、3 个字节、2 个 u32）。
- 调用 `FUN_00743ef2`（DFE 参数下发/校验）。
- 满足 2-pass 条件后调用 DMM 请求构造例程：

```text
FUN_002e7300(0x324, 1, 0, &out, 5)
```

- 成功后在全局记录：`local_88`（u32）、`local_94`（半字句柄）、`*param_2`。
- 按驱动类型字节把 `{1,2,4,6,5}` 写入五个不同全局，标识已占用的 2-pass 资源。

## 4. DMM 请求构造例程 FUN_002e7300

- 构造 0x78 字节请求头：类型字段 `0x55`，长度字段 `0x70`，`param_5` 写入高半字，`param_1` 作为主请求值。
- 校验请求头各字段，随后调用 `FUN_0001cfe4`（消息下发）。
- 失败返回负错误码（0xfffffffa/0xfffffffb/0xfffffffd）。

## 5. 对 RAW 研究的意义

- `AllocDfeMemForDfe2Pass` 用 `0x324` 作为主请求值调用 DMM 构造例程；`0x324` 很可能就是 DFE 2-pass RAW 缓冲的 DMM 单元类型（未证实）。
- 若运行时能从 `/proc/udm/dmm_units` / `dmm_extents` 看到 `0x324` 单元的物理地址与大小，即可用 `docs/13_stream2_dmm_path.md` 的 stream2 通道只读映射抓取。

## 6. 证据分级

- 已证实（离线）：模式到 DFE 资源编号的映射存在（FUN_00690242）。
- 已证实（离线）：`AllocDfeMemForDfe2Pass` 以 0x324 调用 DMM 请求构造例程。
- 高可信推测：0x324 是 DFE 2-pass RAW 缓冲的 DMM 单元类型。
- 未证实：实机中该单元类型对应的物理地址与大小。
- 未执行：任何 ioctl / mmap / 内存读取。

## 7. 产物

- `firmware/manifests/ghidra_avcam_dfe_alloc_xrefs.tsv`
- `firmware/manifests/ghidra_avcam_dfe_alloc_funcs.txt`
- `firmware/manifests/ghidra_avcam_dfe_res_alloc.txt`
