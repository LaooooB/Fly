# MaleCNS Human Avatar CyberPet v0.2

一个可以在 Windows 本地养的 2D 赛博宠物。

画面里的主体已经换成**人形角色**，食物换成**面包**；底层控制核心仍然通过 `flybrain 0.1.0` 运行 **Janelia/FlyEM MaleCNS v1.0** 的完整 166,700 神经元连接组。

v0.2 新增了可持久化的快速强化学习层：接近/吃到面包会获得模拟多巴胺，挨饿和撞到边界会产生模拟疼痛，学习结果保存在 `J:\FLY\save\pet_state.json`，下次启动继续使用。

> 这里的多巴胺和疼痛是程序强化信号，不代表真实生物神经递质或主观感受。人形只是外观，底层仍是 MaleCNS 果蝇连接组。

## 推荐目录

代码仓库放在：

```text
J:\FLY\app\
```

MaleCNS 和宠物长期数据放在：

```text
J:\FLY\
├─ app\
├─ male_cns_data\
└─ save\
   ├─ pet_state.json
   └─ memories.jsonl
```

这样后续更新代码不会碰 MaleCNS 数据和宠物记忆。

## 第一次安装

在命令行执行：

```bat
J:
mkdir J:\FLY 2>nul
cd /d J:\FLY
git clone https://github.com/LaooooB/Fly.git app
cd /d J:\FLY\app
```

然后双击：

```text
INSTALL_OFFICIAL_MALECNS.bat
```

安装和 MaleCNS 校验完成后，双击：

```text
RUN_FLY.bat
```

## 以后更新

直接双击：

```text
UPDATE.bat
```

或者命令行：

```bat
cd /d J:\FLY\app
git pull --ff-only
```

不需要重新运行 `INSTALL_OFFICIAL_MALECNS.bat`。只要 `J:\FLY\male_cns_data\OFFICIAL_MALECNS_BUILD_OK.json` 仍存在，更新后的程序继续使用原来的 MaleCNS 数据。

完整说明见 [README_CN.md](README_CN.md)。
