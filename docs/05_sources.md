# 来源清单

## 固件

| 项目 | 值 |
| --- | --- |
| 固件 | α6500 Ver.1.06（Windows updater） |
| 下载 | `https://support.d-imaging.sony.co.jp/download/IMT/Update_ILCE6500V106.exe?fm=cn` |
| SHA256 | `9832A5597A1EB8AE495157EF476E0210AF40B5B8999C45C0DC0E5929BA32F3FC` |
| 解包工具 | ma1co/fwtool.py（v1，含新式 updater 切片流程） |

## 公开逆向资料（本地归档于 `tools/vendor/`）

| 仓库/资料 | 来源 | 用途 |
| --- | --- | --- |
| Sony-PMCA-RE | github.com/ma1co/Sony-PMCA-RE | USB 交互、updatershell/serviceshell |
| OpenMemories-Symbols | github.com/ma1co/OpenMemories-Symbols | 固件符号库（当前无 ILCE-6500） |
| OpenMemories-Docs | github.com/ma1co/OpenMemories-Docs | hardware.rst（BIONZ/DFE/codec/SA DSP） |
| OpenMemories-Framework | github.com/ma1co/OpenMemories-Framework | 相机 App API、机型表 |
| OpenMemories-Tweak | github.com/ma1co/OpenMemories-Tweak | telnet/ADB/设置解锁 |
| OpenMemories-Platform | github.com/ma1co/OpenMemories-Platform | 相机原生代码 |
| OpenMemories-AppList | github.com/ma1co/OpenMemories-AppList | App 清单 |
| fwtool.py | github.com/ma1co/fwtool.py | 固件解包 |
| fwtool_ori / alpha-fwtools | github.com/madwyn、ewindisch | 原版 fwtool 参考 |
| nex-hack | github.com/erik-smit/nex-hack | 早期索尼 hack 源码镜像 |
| a6300_updater_emu（部分） | github.com/BI2QFA/a6300_updater_emu | a6300 QEMU 更新器参考 |
| OpenMemories-CI（部分） | github.com/ma1co/OpenMemories-CI | QEMU 仿真 CI、`di.update.sony.net` URL 模式 |
| Sony-PMCA-RE-0.18 | github.com/luiyisaki/Sony-PMCA-RE-0.18 | a6300 录时长扩展参考 |

注：`a6300_updater_emu`（34MB）与 `OpenMemories-CI`（27MB，含 `tests/test_cxd90014.py`、`runner/kernel_patch.py` 等）均已通过 ghproxy 镜像（`gh-proxy.com`）完整下载；a6300 模拟已成功启动，CI 测试脚本提供了 CXD90014 内核基址推导方法。

## 官方资料

- Sony 中国服务页下载 API（`service.sony.com.cn/casch/homePageExt`）用于定位固件条目。
- OpenMemories-Docs `hardware.rst`：CXD90014/SA DSP/DFE/codec 硬件表（已归档）。

## 本地工具链（不入库）

- Ghidra 12.1.3 PUBLIC：NSA 官方 release，解压至 `tools/vendor/ghidra_12.1.3_PUBLIC`。
- Temurin OpenJDK 21：解压至 `tools/vendor/jdk21`。
- Headless 项目：`firmware/ghidra_projects/a6500_v106`（`av-cam.bin`，`ARM:LE:32:v7`，base 0；分析约 387s）。

## α6300 固件对比输入

- 官方下载条目：Sony China 服务 API 返回的 `ILCE-6300 Ver2.01` Windows 更新包。
- 下载文件：`firmware/a6300-raw/Update_ILCE6300V201.exe`。
- SHA256：`0677B93F7BA550BD33C9C8732B20FB3D3302C14E943436F22B60AE8264188942`。
- 解包索引：`firmware/manifests/module_index_a6300_v201.csv.json`。
- 对比工具：`tools/compare_firmware_manifests.py`。
