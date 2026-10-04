# α6500 实机 DMM 分配表基线（2026-09-01）

## 已证实

1. `/proc/udm/dmm_info`、`dmm_units`、`dmm_extents`、`dmm_reserve`、`dmm_rule` 在实机可读（PMCA service shell）。
2. `dmm_units` 表头：`handle type status alloc open rdv serial relation address size extent(suspend)`。
3. 所有单元地址位于 `0x80000000-0xbfffffff`（1GB DRAM）。
4. `dmm_extents` 中存在 unit type `0x2b3` 的 extent：
   - id `0069`，parent `0011`，type `000002b3`，地址 `b8c00000+05276000=bde76000`，size `0xc000`（48KB）。
5. 当前未触发拍摄，RAW 候选 unit type `0x236/0x1df/0x23e` 未作为 unit type 出现在表中。

## 关键观察

- grep `0236|01df|023e|02b3` 在 `dmm_units` 命中的两行实际是 extent 后缀列（`0236 < 0010` / `023e < 0010`），其 unit type 为 `00121e00`，不是 RAW 类型。
- `dmm_extents` 命中三行：`0069`（真实 type `0x2b3`）、`0236`/`023e`（是 extent id，type 为 `0xca`）。
- 结论：当前唯一出现的 RAW 候选 unit type 是 `0x2b3`，大小 48KB，不是 640x480x10bit 级别的 Bayer 缓冲。

## 下一步

- 触发 DualRec / 正常快门后，重读 `/proc/udm/dmm_units`，观察 `0x236/0x1df` 是否出现、地址与大小。
- 若 RAW 单元出现，再用 stream2 通道只读映射抓取。
