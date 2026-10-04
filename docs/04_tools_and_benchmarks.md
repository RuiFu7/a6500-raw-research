# 工具链与压缩基准

## 工具

常规分析工具使用 bundled Python 运行（`python.exe`，3.12）；静态反汇编另使用 Ghidra 12.1.3 + Temurin JDK21（位于 `tools/vendor/`，不入库）。

| 工具 | 用途 | 输入 -> 输出 |
| --- | --- | --- |
| `tools/fw_extract.py` | 新式 updater .exe 切片出 DAT 并调用 fwtool 解包 | updater/dat -> 解包目录 |
| `tools/index_modules.py` | 固件文件索引（size/magic/sha256） | 目录 -> CSV+JSON |
| `tools/strings_scan.py` | ASCII 字符串提取与关键词过滤 | 二进制 -> stdout/UTF-8 文件 |
| `tools/raw_analyze.py` | dump 位深/packing/Bayer 分析 | raw + w/h/bits -> JSON（可选 PNG） |
| `tools/debayer.py` | 双线性 Bayer 还原 | raw + w/h/bits -> PNG |
| `tools/compression_bench.py` | Bayer predictor + Rice 压缩基准 | raw（或 `--synthetic`）-> JSON |
| `tools/partial_zip_extract.py` | 截断 zip 的本地头顺序恢复 | partial.zip -> 目录 |
| `tools/avcam_xref.py` | av-cam.bin 的 PC 相对字符串引用扫描（启发式） | av-cam.bin -> 命中地址 |
| `tools/avcam_disasm.py` | av-cam.bin 分支跟踪反汇编（实验性，覆盖有限） | av-cam.bin -> 命中地址 |
| `tools/elf_reloc_disasm.py` | ET_REL/ET_DYN 重定位与符号调用标注 | ELF module -> 注释反汇编 |
| `tools/mpr_area_map.py` | 从 libmpr.so 静态面积表提取 MPR type/label | libmpr.so -> stdout/JSON |
| `tools/ghidra_scripts/GhidraXrefSearch.java` | Ghidra 字符串字节搜索 + 交叉引用 | av-cam.bin 项目 -> TSV |
| `tools/ghidra_scripts/GhidraDumpFunctions.java` | 函数反汇编 + 伪代码导出 | 地址列表 -> TXT |
| `tools/ghidra_scripts/GhidraFindMemoryOffset.java` | 扫描对象字段偏移引用 | offset -> TXT |
| `tools/ghidra_scripts/GhidraFindStateWriters.java` | 扫描对象字段写入并输出上下文 | offset -> TXT |
| `tools/ghidra_scripts/GhidraDumpRange.java` | 地址区间反汇编/数据导出 | start end -> TXT |
| `tools/ghidra_scripts/GhidraDumpWords.java` | 从已加载的 Ghidra 程序内存读取 32 位字 | start end -> TXT |
| `tools/ghidra_scripts/GhidraRefs.java` | 地址的入/出引用查询 | 地址列表 -> TXT |
| `tools/ghidra_scripts/GhidraFindPcAddRef.java` | 函数内 `ldr+add rN,pc` 目标扫描（修正 PC 基址） | 目标地址列表 -> 命中 TXT |
| `tools/ghidra_scripts/GhidraFindImmediate.java` | 立即数操作数扫描 | 目标值列表 -> 命中 TXT |
| `tools/test_tools.py` | 自测 | `python -m unittest tools.test_tools -v` |

## 自测结果

`python -m unittest tools.test_tools -v`：8/8 通过（10/12-bit packed 往返、Bayer pattern 检测、raw_analyze CLI、debayer CLI、ELF 反汇编、符号查找、Rice 往返与压缩率）。

## 3K 压缩基准（v1，合成数据）

参数：3072x1728 / 10-bit / 25fps / left-up predictor / 按行自适应 k 的 Rice 码。

结果：

| 指标 | 数值 |
| --- | --- |
| 原始未压缩 | 166.0 MB/s |
| 压缩后 | 101.6 MB/s |
| 压缩比 | 2.613:1 |

目标 50-70 MB/s 需要 2.37-3.32:1。v1 达到 2.61:1，说明方向可行，但单靠 left-up + Rice 不足以下探到 70 MB/s 以下。

## v2 优化方向（未实现）

- LOCO-I 风格中值梯度预测器（水平/垂直/对角梯度选择）。
- JPEG-LS 式上下文建模 + Golomb 参数自适应（按上下文分桶估计 k）。
- 行/块级零游程与 sign 分离；Bayer 双色平面分离（G 平面单独处理）。
- 用真实 RAW dump（来自运行时实验）替代合成数据再评估。

## 说明

压缩基准只验证算法可行性，不涉及相机；RAW 数据源仍需运行时实验（见 `03_runtime_experiments.md`）。
