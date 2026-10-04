# 运行时速查表（第二阶段用）

## 候选设备节点（待实机确认）

来自固件模块名与脚本，运行时用 `ls -la /dev`、`find /sys -maxdepth 4 ...` 核对：

| 候选节点/模块 | 依据 | 期望作用 |
| --- | --- | --- |
| `/dev/stream` / `/dev/stream2` | 模拟器已确认（char 249,7 / 249,8） | 数据流设备 |
| `/dev/dmm*` | `dmm.ko`（`DmmConfig` 参数） | DRAM 管理 |
| `/dev/beaune*` | `beaune_drv.ko` | Beaune codec 控制 |
| `/dev/sen*` | `usbg_sen.ko`、`sen.elf` | sensor 相关 USB gadget |
| `/dev/dmac` / `/dev/uipc` / `/dev/mcmn` / `/dev/ldec` | 模拟器已确认 | DMA / uIPC / 公共 / LSI 解码 |
| `/dev/mmca1` | `common.src` | SD 卡 |
| `/dev/ms1` | `common.src` | 记忆棒 |
| `/dev/dnflasha16` | `s_start_android.sh` | Android system 分区 |

## 消息 ID / 命令字

| 值 | 来源 | 含义 |
| --- | --- | --- |
| `0xDC0000` | RAW 场景 `osal_set_msg_src` | RAW 外部输出消息源 |
| `0x40BD` | RAW 场景应答字 | 命令完成码 |
| `0x2008 / 0x106` | `SdiCh::setRawResolution` | SDI RAW 分辨率数据流命令 |
| `0x5012 / 0x5017` | STM `extractImageInstance` / `rawparseImageInstance` | STM 图像实例命令 |

## 模块加载确认

```sh
lsmod | grep -E 'stream|dmm|beaune|osal|usbg|mmc'
cat /proc/modules
```

## 内存布局

```sh
cat /proc/iomem
cat /proc/meminfo
cat /proc/zoneinfo
```

## 启动模式

```sh
cat /setting/mode/dmode
cat /setting/updater/mode
```

## 只读探测

直接运行 `scripts/probe_readonly.sh`（相机 root shell）并把输出存到电脑端。
