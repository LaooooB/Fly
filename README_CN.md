# MaleCNS CyberPet v0.1

一个可以在 Windows 本地养的 2D 赛博雄性果蝇。控制核心通过 `flybrain 0.1.0` 运行 **Janelia/FlyEM MaleCNS v1.0** 的完整 166,700 神经元连接组；安装器默认从 MaleCNS 官方公开数据构建本地脑缓存。

## 你会看到什么

- 一只在培养皿里自己移动的雄蝇。
- 食物：距离和方向被编码成 `ORN_DM1` 嗅觉输入，饥饿会改变输入增益。
- 目标/伴侣：视觉目标被编码到 `LC10a`。
- 靠墙/逼近刺激：编码到 `LC4 + LPLC2`。
- 转向：读取 `DNa02` 左右侧活动差。
- 前进：读取 `DNg100`。
- 后退：读取 `MDN`。
- 逃逸：读取 `DNp01`。
- 求偶：读取 MaleCNS 中雄性特异的 `pIP1` 活动。
- 疲劳过高会睡眠和恢复。
- 吃过的食物位置会形成长期位置记忆，下一次启动还在。

## 存档位置

固定保存到：

```text
J:\FLY\
├─ male_cns_data\
│  ├─ ... MaleCNS 本地构建数据
│  └─ OFFICIAL_MALECNS_BUILD_OK.json
└─ save\
   ├─ pet_state.json
   └─ memories.jsonl
```

`pet_state.json`：宠物当前长期状态，包括位置、方向、饥饿、疲劳、社交驱动、年龄、吃过几次、求偶次数、记住的食物位置。

`memories.jsonl`：事件记忆，例如吃东西、逃逸、睡觉、醒来、求偶、退出游戏。

正常关窗口、按 `Q` / `Esc`、Ctrl+C，以及每 30 秒自动保存都会写盘。

## 安装

### 1. 确认 J: 盘存在

此版本按你的要求固定使用 `J:\FLY`。如果机器没有 J: 盘，安装器会直接停止，不会偷偷改到 C:。

### 2. 双击

```text
INSTALL_OFFICIAL_MALECNS.bat
```

安装器会：

1. 检查/安装 Python 3.12（已有 3.10+ 也可用）。
2. 创建项目自己的 `.venv`。
3. 安装 `pygame-ce` 和 `flybrain[build]==0.1.0`。
4. 设置 MaleCNS 数据目录到 `J:\FLY\male_cns_data`。
5. 执行 `flybrain build`，从官方 MaleCNS v1.0 release 构建本地网络。首次需要下载约 1.1 GB 原始连接数据。
6. 用 SciPy 读取构建后的稀疏矩阵，检查：
   - 166,700 个神经元
   - 25,582,938 条保留的神经元连接
7. 校验成功后写入 `OFFICIAL_MALECNS_BUILD_OK.json`。

如果这一步没成功，`RUN_FLY.bat` 不会启动游戏。

## 运行

双击：

```text
RUN_FLY.bat
```

如果自动设备模式有问题，可以试：

```text
RUN_FLY_CPU.bat
```

退出：`Q` 或 `Esc`，也可以直接点窗口关闭。

## 重置宠物

双击：

```text
RESET_PET_MEMORY.bat
```

它只删除 `J:\FLY\save`，不会删 MaleCNS 数据，所以不用重新下载 1.1 GB。

## 这版的“记忆”是什么

MaleCNS 公开数据主要给出了真实神经元连接和突触权重，不包含一套已经验证好的“果蝇长期记忆动态模型”。因此 v0.1 做法是：

- MaleCNS 的连接组保持固定，负责神经活动传播和动作/求偶神经群读出。
- 长期生活记忆单独持久化，例如吃过的食物位置、生活状态、事件经历。
- 这些记忆会反过来给感知输入提供很弱的偏置，让它下一次启动时会利用以前的经历。

所以这不是“把真实果蝇意识保存下来”，也没有这种科学依据。它是 **真实 MaleCNS wiring + 明确标注的人造神经动力学/身体需求/记忆层**。

## 数据来源

官方 MaleCNS：

- Project: https://male-cns.janelia.org/
- Download: https://male-cns.janelia.org/download/
- neuPrint dataset: `male-cns:v1.0`
- Official bucket: `gs://flyem-male-cns/v1.0/connectome-data/flat-connectome/`

MaleCNS 数据许可为 CC BY 4.0。项目代码本身不打包 MaleCNS 数据；安装时从公开数据源构建。

## 如果要换成你自己画的虫

目前昆虫是 Pygame 程序绘制，不依赖外部图片。后续可以直接把 `_draw_fly()` 换成 PNG/SpriteSheet，而神经系统、生活状态和存档都不用改。
