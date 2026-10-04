# α6500 实机只读基线报告

## 连接

- 型号：`ILCE-6500`
- 固件：`1.06`
- 序列号：`[REDACTED]`
- 镜头：`0xa0f148`，固件 `1.01`
- 流程：Mass Storage `054C/0AC4` -> PMCA service mode `054C/0336` -> 平台 shell
- 结果：成功进入 shell 并正常退出

## 内核与内存

- 内核：`Linux 3.0.27_nl-rt106+ #1 SMP PREEMPT RT Fri Feb 15 16:10:08 JST 2019`
- 架构：`armv7l`
- 物理 DRAM：启动参数 `mem=1024M@0x80000000@0`
- `/proc/iomem`：`80000000-bfffffff : System RAM`
- `/proc/iomem` 还显示：`arm7sram`、`arm7io`、`nandreg`、`nandc`、PCI non-prefetchable、USB、UART
- `/proc/meminfo`：`MemTotal: 201416 kB`
- 关键保留区：`wbimem`、`warm.mem_dst`、`warm.mem_work`、`wbi_cmpr.waddr`、`memrsv`

`MemTotal` 不是物理 DRAM 总量；大量地址空间由固件、设备和温启动机制保留。

## 运行时模块

实机 `/proc/modules` 确认加载：

`dmm`、`stream`、`stream2`、`dmac`、`osal_uipc`、`ldec`、`lld`、`nand`、`hdmi`、`usbg_sen`、`usbg_stillimage`、`mcmn_drv`、`mmc_drv`、`ms_drv`、`backup`、`upm`、`liro`、`beaune_drv`、`grm_gles`、`usbg_storage` 等。

## 关键设备节点

| 节点 | 实机设备号 |
| --- | --- |
| `/dev/stream` | `249,7` |
| `/dev/stream2` | `249,8` |
| `/dev/dmac` | `251,206` |
| `/dev/uipc` | `251,207` |
| `/dev/mcmn` | `249,1` |
| `/dev/ldec` | `251,205` |
| `/dev/hdmi` | `248,25` |
| `/dev/mmca1` | `250,11` |
| `/dev/ms1` | `249,1` |
| `/dev/dnflasha7` | `252,135` |
| `/dev/dnflasha15` | `252,143` |
| `/dev/dnflasha16` | `252,144` |
| `/dev/nflasha1` | `252,1` |
| `/dev/nflasha3` | `252,3` |
| `/dev/nflasha7` | `252,7` |
| `/dev/nflasha15` | `252,15` |

`/dev/dmm*` 没有在本轮关键节点命令中显示，但 `dmm` 模块已加载；不能把模块名直接等同于一个特定字符设备节点。

## 内核日志

定向日志出现：

- `UDIF: resume start/end: dmac`
- `UDIF: resume start/end: stream`
- `UDIF: resume start/end: stream2`
- `UDIF: resume start/end: dmm`
- service shell 终端启用：`console [usbgcon-1] enabled`

这确认 DFE 相关的 Linux 侧基础组件在实机启动并工作。

## 结论

- **已证实**：α6500 V1.06 可通过 PMCA 临时进入 service shell；真实 1 GB DRAM 地址范围、内核版本、模块和关键设备节点均可读取。
- **高可信推测**：实机的 DFE/DMM/stream/DMAC/uIPC/LDEC 运行时环境与离线固件分析的链路对应。
- **未证实**：任何具体 Bayer buffer、RAW 位深、packing、Bayer pattern、帧时序或连续 RAW 输出。

本轮没有读取 `/dev/mem`、`/dev/dmac`、`/dev/stream` 数据，也没有触发 DualRec、发送 `SET_*`、加载/卸载模块或写入相机文件。
