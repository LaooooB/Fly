# MaleCNS CyberPet v0.1

一个可以在 Windows 本地养的 2D 赛博雄性果蝇。控制核心通过 `flybrain 0.1.0` 运行 **Janelia/FlyEM MaleCNS v1.0** 的完整 166,700 神经元连接组；安装器默认从 MaleCNS 官方公开数据构建本地脑缓存。

## 快速开始

1. 确认电脑存在 `J:` 盘。
2. 首次运行双击 `INSTALL_OFFICIAL_MALECNS.bat`。
3. 安装和 MaleCNS 校验完成后，双击 `RUN_FLY.bat`。
4. 正常关窗口、按 `Q` / `Esc` 都会保存。

长期数据固定保存在：

```text
J:\FLY\
├─ male_cns_data\
└─ save\
   ├─ pet_state.json
   └─ memories.jsonl
```

以后更新代码直接 `git pull`，不需要重新下载 MaleCNS；只要 `J:\FLY\male_cns_data` 和校验标记还在即可。

完整说明见 [README_CN.md](README_CN.md)。
