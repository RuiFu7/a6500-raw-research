# α6500 只读实验记录模板

复制此目录为 `experiments/readonly/<日期>_<编号>/` 后填写。模板不包含任何相机 dump。

执行顺序：

1. 连接前阅读 `docs/10_readonly_preflight.md`。
2. 只运行电脑侧 `scripts/capture_readonly_probe.ps1`。
3. 检查 `probe.stdout.txt` 中的 `/proc/iomem`、`/proc/modules`、`/proc/devices` 和候选节点。
4. 未完成基线记录前，不触发 DualRec，不运行 `devmem`，不读写 `/dev/mem`，不加载模块。

本模板属于只读阶段；任何需要改变模式、发送 SET 命令、调用 gdb 或修改文件的动作都要另行审批并升级实验阶段。
