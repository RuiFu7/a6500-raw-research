# RAW 内存单元类型（GetRawUnitTypeBase_Normal 已还原）

> 离线分析；尚未实机读取。依据：`av-cam.bin` Ghidra。

## 1. 结论

`FUN_002c1ab0` = `GetRawUnitTypeBase_Normal`，根据拍摄状态返回 RAW 缓冲的 DMM 单元类型：

| 条件 | 返回单元类型 |
| --- | --- |
| 默认 | 0x236 |
| mode==0x1b | 0x23e |
| mode==0x0a（开发状态 0/1 时） | 0x236 或配置值（0x1e8 非零取配置） |
| mode==0x0a（其他状态） | 0x1df |
| mode==0x09，状态位 0x15 | 0x1df |
| mode==0x09，状态位 0x22 | 0x1df（配置==1 时改 0x236） |
| mode==0x09，状态位 0x08 | 0x2b3（配置==1 时改 0x236） |

即 RAW 主缓冲单元类型集合：`0x236`、`0x1df`、`0x23e`、`0x2b3`。

## 2. RAW 内存管理器

`FUN_002c2088`（GetMem_RawCor 附近）流程：

- 调用 `FUN_002c1ab0` 得到 unit_type。
- 通过 DMM 分配例程 `FUN_006a7d6a(unit_type, 0, 1, 0xffffffff, &out)` 或 `FUN_006a7c84`。
- 成功后写入：
  - `param_1+0x5208`：句柄（u16）
  - `param_1+0x5598`：unit_type
  - `param_1+0x559c` / `+0x55a0`：物理地址/大小信息
- unit_type==0x1df 时额外做 2-pass 处理。

## 3. 运行时确认目标

相机接入后，读：

```sh
cat /proc/udm/dmm_units
cat /proc/udm/dmm_extents
cat /proc/udm/dmm_info
```

重点查找单元类型：

```text
0x236   # RAW 默认
0x1df   # RAW 2-pass / 双拍
0x23e   # RAW 特定模式
0x2b3   # RAW 特定位
```

确认对应物理地址、大小、状态后，再用 `docs/13_stream2_dmm_path.md` 的 stream2 通道只读映射抓取。

## 4. 证据分级

- 已证实（离线）：`GetRawUnitTypeBase_Normal` 存在，返回 `0x236/0x1df/0x23e/0x2b3`。
- 已证实（离线）：RAW 内存管理器调用 DMM 分配并记录句柄/unit_type/物理信息。
- 未证实：实机中这些单元类型对应的物理地址与 Bayer 布局。
- 未执行：任何 ioctl / mmap / 内存读取。

## 5. 产物

- `firmware/manifests/ghidra_avcam_rawunit_func.txt`
- `firmware/manifests/ghidra_avcam_rawmem_func.txt`
- `firmware/manifests/ghidra_avcam_rawunit_names.txt`
- `firmware/manifests/ghidra_avcam_rawunit_xrefs.tsv`
