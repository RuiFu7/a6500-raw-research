# /dev/stream2 物理缓冲映射机制（已还原）

> 本文件只描述离线分析证据。尚未在实机执行任何 ioctl / mmap / 内存读取。
> 依据：`libmpr.so`（Ghidra `a6500_mpr` 项目）与 `stream2.ko`（ET_REL 符号/反汇编）。

## 1. 结论

α6500 存在官方用户态物理 DRAM 映射通道：

1. `libmpr.so` 打开 `/dev/stream2`（`open` flags `0x1002`）。
2. 构造 `ConnectAddrsTbl`：连续 `{phys_addr u32, size u32}` 8 字节表项。
3. `ioctl(fd, 0xC0047805, table)` 把该表注册给当前进程。
4. `mmap(NULL, total_size, PROT_READ|PROT_WRITE, MAP_SHARED, fd, 0)` 把整段物理区映射到用户态。

## 2. libmpr.so 关键地址（Ghidra 地址 = ELF VA）

| 符号/函数 | 地址 | 作用 |
| --- | --- | --- |
| `FUN_006c7e7c` | `0x006c7e7c` | 初始化：打开 `/dev/stream2`，fd 存全局 |
| `FUN_006c81d0` | `0x006c81d0` | `GetConnectedSNCVAdrs` 外壳：查 extent 表、构造链 |
| `FUN_006c7424` | `0x006c7424` | 核心：拷贝表、`ioctl(0xC0047805)`、`mmap`、返回虚拟地址 |
| ioctl 命令常量 | `0x006c7604` | `0xC0047805` |
| mmap 调用 | `0x006c7508` | `blx 0x001813c8`（mmap），`prot=3, flags=1` |

## 3. stream2.ko 侧（与 libmpr 对应）

- `stream2_ioctl`（`.text+0x0`，ARM）：只接受命令类型 `0x78`；`ldr r3,[pc,#...]` 与 `0xC0047805` 比较；登记表到当前进程条目（最多 5 个，每项 `{addr,size}`）。
- `stream2_mmap`（`.text+0x13c`）：遍历当前进程表项，`remap_pfn_range` 逐段映射；每项 8 字节：`+0`=phys（`lsr #12` 得 pfn），`+4`=size；偏移累计。

## 4. 对 RAW 研究的意义

- 这不是 `/dev/mem` 裸读，而是索尼自身用于 `MemInfo`/DFE 缓冲管理的受控映射路径。
- 若能确认某 DMM 分配单元（如 DFE RAW / DualRec Bayer 缓冲）的物理地址，就可用同一机制只读映射后抓取。
- 只读映射本身不写固件；但 `ioctl(0xC0047805)` 会改变 stream2 驱动的进程登记状态，属于“运行时读取”阶段，需先完成只读基线、确认回滚条件后再执行。

## 5. 证据分级

- 已证实（离线）：`libmpr.so` 用 `ioctl(0xC0047805)` + `mmap` 映射 DMM 物理区；`stream2.ko` 实现该命令与逐段 `remap_pfn_range`。
- 已证实（离线）：表项格式为 `{phys u32, size u32}`，与 `stream2.ko` mmap 循环一致。
- 未证实：哪个具体 DMM unit 承载 RAW/DFE 缓冲；实机可用性。
- 未执行：任何 ioctl / mmap / 内存读取。

## 6. 产物

- `firmware/manifests/ghidra_mpr_stream2_xrefs.tsv`：字符串引用。
- `firmware/manifests/ghidra_mpr_stream2_funcs.txt`：`FUN_006c7424` / `FUN_006c81d0` 反汇编与反编译。
- `firmware/manifests/ghidra_mpr_stream2_data.txt`：常量区（含 `0xC0047805`）。
- `firmware/manifests/ghidra_mpr_stream2_open.txt`：`/dev/stream2` 打开函数。
