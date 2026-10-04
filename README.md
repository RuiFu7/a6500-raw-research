# Sony α6500 (ILCE-6500) RAW Video Research

> 中文说明见下方。English abstract: an offline, evidence-graded reverse-engineering
> study of whether the Sony α6500 can expose an accessible high-bit-depth Bayer RAW
> video path. **No RAW video was obtained.** Everything here is static analysis plus
> strictly read-only runtime observations.

本仓库是对 Sony α6500（ILCE-6500）是否可能存在**可访问的高位深 Bayer RAW 视频通路**
的公开研究记录：固件解包、模块索引、静态逆向、以及受控的只读实机观察。

## 重要声明（请先读）

- **未获得 10-bit RAW 视频**。本项目没有成功导出可播放的 Bayer RAW 视频流。
- 所有结论都带证据分级：`已证实 / 高可信推测 / 未证实 / 否定`。
  完整矩阵见 [`docs/07_conclusion_matrix.md`](docs/07_conclusion_matrix.md)，
  逐条证据台账见 [`docs/evidence_ledger.tsv`](docs/evidence_ledger.tsv)。
- 研究过程**没有刷机、没有 RAM patch、没有写入相机分区或 SD 卡**。
  实机部分仅使用 PMCA `serviceshell` 只读读取。
- 仓库**不包含**任何 Sony 固件二进制、解包后的固件文件、Ghidra 工程或厂商工具。
  只保留可再生成的索引、字符串、反汇编文本和自定义脚本。
- 固件版权属于 Sony。使用这里的任何内容前请自行确认你所在地的法律与授权范围。

## 目录

| 路径 | 内容 |
| --- | --- |
| `docs/` | 阶段报告、来源清单、运行时协议、结论矩阵、证据台账 |
| `tools/` | 自定义固件解包 / ELF 解析 / DMM·DMAC 静态分析脚本 |
| `scripts/` | 相机侧只读探测脚本、电脑侧归档脚本 |
| `firmware/manifests/` | 模块索引、字符串、Ghidra 反汇编与交叉引用导出（无二进制） |
| `analysis_out/` | 2026-09-05/06 静态审计的原始文本与 JSON 产物 |
| `experiments/` | 只读实机基线与运行时实验记录（无抓取到的二进制 dump） |

## 阅读顺序

1. [`docs/00_project.md`](docs/00_project.md) — 项目定义、边界与分级标准
2. [`docs/07_conclusion_matrix.md`](docs/07_conclusion_matrix.md) — 目前能确定和不能确定的一切
3. [`docs/25_offline_target_plan.md`](docs/25_offline_target_plan.md) — 离线阶段目标与验收线
4. [`docs/33_current_goal_20260906.md`](docs/33_current_goal_20260906.md) — 停手时的状态与下一步
5. [`docs/20_model_handoff.md`](docs/20_model_handoff.md) — 给接手者的交接文档

## 主要静态结论（摘要）

- α6500 V1.06 与 α6300 V2.01 固件已解包并建立模块索引，两版高度同构。
- RAW 内存管理、DMM 分配、`Stage_DfeRawTrans` 到 DFE HDMAC 的调用链已在静态层面
  闭合到寄存器级目标附近（见 `docs/27`、`docs/31`）。
- `unit type 0x23a`、`0x1df` 等早期 RAW 候选已被**降级**为播放/回读或默认回退路径，
  不是已证实的 Bayer 像素缓冲（见 `docs/32`）。
- 下一步的关注点是 CapMode 枚举到 RAW unit / DMM handle / 下游消费者的映射。

## 复现工具

`tools/` 下的脚本需要 Python 3；Ghidra 相关导出需要自备 Ghidra。
厂商工具（fwtool.py、Ghidra、JDK、OpenMemories 系列仓库）未打包，来源见
[`docs/05_sources.md`](docs/05_sources.md)。

## 免责声明

本项目仅用于互操作性与研究目的，与 Sony 无关。不提供任何绕过版权保护、
破解或盗版固件的内容。请勿据此对他人设备进行未授权修改。

## License

未指定。如需引用或再发布，请先阅读 `docs/05_sources.md` 中的原始来源与各自的许可。
