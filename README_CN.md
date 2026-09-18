# MaleCNS Human Avatar CyberPet v0.2

一个可以在 Windows 本地养的 2D 赛博宠物。

画面里的主体现在是**人形角色**，食物显示为**面包**。底层控制核心仍然通过 `flybrain 0.1.0` 运行 **Janelia/FlyEM MaleCNS v1.0** 的完整 166,700 神经元连接组。

也就是说：外观换成人了，底层仍然是 MaleCNS 果蝇连接组，不是人脑模型。

## v0.2 新增内容

- 主体外观从果蝇改成人形角色。
- 食物从圆点改成面包。
- 饥饿超过约 50% 后开始产生持续的模拟疼痛信号，越饿越强。
- 撞到场地边界会产生一次强疼痛信号。
- 朝最近的面包移动时，会获得小额模拟多巴胺，用于更快形成“接近食物”的行为关联。
- 吃到面包会获得强多巴胺奖励，并降低饥饿。
- 成功发生近距离社交/pIP1 行为时也会获得奖励。
- 新增快速强化学习层 `FastValenceLearner`：
  - 读取“多巴胺 - 疼痛”作为强化信号。
  - 学习左转、右转、前进、后退或不干预。
  - 只给 MaleCNS 动作输出增加小偏置，不修改 MaleCNS 原始连接和突触权重。
  - 学到的 Q 值会随宠物存档一起保存，下次启动继续用。
- 右侧面板新增 `DOPAMINE`、`PAIN`、`RL states`、`RL updates` 和当前学习偏置。

这里的“多巴胺”和“疼痛”是程序里的强化学习信号，不代表真实生物神经递质，也不代表角色有主观痛感。

## MaleCNS 仍然负责什么

- 面包距离和方向仍编码到 `ORN_DM1` 嗅觉输入。
- 目标/伴侣视觉仍编码到 `LC10a`。
- 靠墙/逼近刺激仍编码到 `LC4 + LPLC2`。
- 转向读取 `DNa02` 左右侧活动差。
- 前进读取 `DNg100`。
- 后退读取 `MDN`。
- 逃逸读取 `DNp01`。
- 社交/求偶相关读出仍使用 MaleCNS 中的 `pIP1`。
- 疲劳过高仍会睡眠和恢复。

强化学习层是在这些 MaleCNS 输出之上加一个较小的可学习偏置。

## 学习是怎么工作的

程序会把当前环境压缩成简单状态，例如：

- 面包在左边 / 右边 / 正前方 / 没闻到。
- 墙体威胁在左边 / 右边 / 两边 / 没威胁。
- 当前饥饿程度。

每隔一小段时间，它会尝试：

- 不干预 MaleCNS。
- 左转。
- 右转。
- 加强前进。
- 后退/轻微逃逸。

然后根据反馈更新 Q 值：

- 靠近面包：小额正反馈。
- 吃到面包：强正反馈。
- 社交成功：正反馈。
- 挨饿：持续负反馈。
- 撞墙：强负反馈。

学习率故意设置得比较高，并保留约 22% 的探索概率，所以它会比上一版更快地产生可观察的行为变化。

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

`pet_state.json` 现在还会保存：

- `dopamine`
- `pain`
- `reward_events`
- `pain_events`
- `learning_updates`
- `policy_q`：强化学习 Q 表

原来的旧存档可以继续读取，新字段缺失时会自动使用默认值。

`memories.jsonl` 会记录吃面包、饥饿疼痛、撞墙疼痛、社交、逃逸、睡觉、醒来和退出等事件。

正常关窗口、按 `Q` / `Esc`、Ctrl+C，以及每 30 秒自动保存都会写盘。

## 第一次安装

确认机器有 J: 盘，然后双击：

```text
INSTALL_OFFICIAL_MALECNS.bat
```

安装器会：

1. 检查/安装 Python。
2. 创建项目自己的 `.venv`。
3. 安装 `pygame-ce` 和 `flybrain[build]==0.1.0`。
4. 设置 MaleCNS 数据目录到 `J:\FLY\male_cns_data`。
5. 从 MaleCNS 官方公开数据构建本地网络。
6. 校验 166,700 个神经元和构建结果。
7. 写入 `OFFICIAL_MALECNS_BUILD_OK.json`。

## 运行

双击：

```text
RUN_FLY.bat
```

如果自动设备模式有问题，可以试：

```text
RUN_FLY_CPU.bat
```

退出：`Q` 或 `Esc`，也可以直接关闭窗口。

## 以后更新

如果已经安装过 MaleCNS，后面代码更新不需要再次运行安装器。

直接双击：

```text
UPDATE.bat
```

然后再运行：

```text
RUN_FLY.bat
```

只要 `J:\FLY\male_cns_data\OFFICIAL_MALECNS_BUILD_OK.json` 还在，就会继续使用已经下载好的 MaleCNS 数据。

## 重置宠物

双击：

```text
RESET_PET_MEMORY.bat
```

它只删除 `J:\FLY\save`，不会删除 MaleCNS 数据。

## 关于“意识”和“学习”

MaleCNS 公开数据给出了真实连接组和突触信息，但没有证据说明把它跑在这个 2D 环境里就会产生意识。

这版的结构是：

- MaleCNS 连接组：负责神经活动传播和动作相关神经群读出。
- 人造身体需求：饥饿、疲劳、社交驱动。
- 人造强化信号：模拟多巴胺和疼痛。
- 人造快速强化学习层：把奖励/惩罚关联到动作偏置。
- 持久化记忆：保存状态、事件、食物地点和 Q 表。

所以可以把它理解成“真实 MaleCNS wiring + 人造身体 + 人造强化学习 + 长期存档”的赛博宠物实验。

## 数据来源

官方 MaleCNS：

- Project: https://male-cns.janelia.org/
- Download: https://male-cns.janelia.org/download/
- neuPrint dataset: `male-cns:v1.0`
- Official bucket: `gs://flyem-male-cns/v1.0/connectome-data/flat-connectome/`

MaleCNS 数据许可为 CC BY 4.0。项目代码本身不打包 MaleCNS 数据；安装时从公开数据源构建。
