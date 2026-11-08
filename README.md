# XY Quick Hack 1.0

赛博朋克 2077 **2.50** 的三枚自定义快速破解（自我擦除含三个等级）。

| 破解 | 品质 | RAM | 上传 | 持续时间 | 目标 |
|---|---|---|---|---|---|
| **自我擦除** | 蓝 Rare | 6 | +1.0 秒 | **60 秒** | 人形敌人 / 摄像头 / 炮塔 |
| **自我擦除** | 紫 Epic | 7 | +1.5 秒 | **120 秒** | 人形敌人 / 摄像头 / 炮塔 |
| **自我擦除** | 橙 Legendary | 8 | +2.0 秒 | **180 秒** | 人形敌人 / 摄像头 / 炮塔 |
| **破解扩散** | 橙 Legendary | 12 | +1.5 秒 | 瞬间 | 20 米内全部敌人 + 设备（上限 99） |

---

## 1. 效果

### 自我擦除

对目标上传后，**目标不再把你当作感知对象**：

- 看不见你（玩家被排除在其检测之外）
- 听不见你（听觉关闭）
- 破解不会抬高它的警戒
- **你后续上传的破解也不会被追踪**（追踪条不会出现）

只要你在它视野之外，它就不会发现你。它仍然会对其他事情正常反应 —— 比如发现尸体后进入警戒、四处张望，只是找不到你。

**攻击会打破自我擦除**，而且只打破你攻击的那一个目标，其他目标不受影响。

### 破解扩散

把目标身上**现有的**所有快速破解效果（按 `Quickhack` 标签识别），复制给 20 米内的所有敌人与设备，上限 99 个，不包含目标自己。

扩散不计入追踪，也不会让被扩散的目标发现你。

---

## 2. 获取方式

三家芯片商人有售，与原版破解**同一套等级 / 声望门槛**：

| 商人 | 位置 |
|---|---|
| `wat_kab_techstore_01` | 歌舞伎 |
| `std_arr_techstore_01` | 圣多明戈 · 阿罗约 |
| `std_rcr_techstore_01` | 兰乔科罗纳多 |

- 蓝 / 紫 / 橙三档分别对应原版 Rare / Epic / Legendary 的可用性条件
- 售价继承原版传说级隐蔽破解的计价方式（品质系数自然拉开差价）

商人库存是**进入存档时生成**的。如果列表里没有，跳 24 小时再去看。

---

## 3. 前置

本机已装好，无需额外安装：

- **TweakXL** 1.12+
- **redscript**（编译 `r6/scripts`）

不需要 Virtual Atelier，也不需要任何其他 mod。

---

## 4. 安装

解压后把 `r6` 和 `archive` 两个文件夹丢进游戏根目录：

```
Cyberpunk 2077\r6\scripts\XY_QuickHack\XY_QuickHack.reds
Cyberpunk 2077\r6\tweaks\XY_QuickHack\*.yaml            （8 个）
Cyberpunk 2077\archive\pc\mod\XY_QuickHack.archive
Cyberpunk 2077\archive\pc\mod\XY_QuickHack.archive.xl
Cyberpunk 2077\archive\pc\mod\XY_QuickHack_icons.archive
```

用 Vortex 安装的话，**先卸掉旧版本**（旧版叫 VH_Quickhacks），否则会同时装两套。

---

## 5. 技术上是怎么做到的

这套实现是照着几个 2.5 上已经在用的社区 mod 做的，不是猜的：

| 问题 | 做法 | 来源 |
|---|---|---|
| 不推警戒 / 不被追踪 | `awarenessCost` **整行不写** —— `ScriptableDeviceAction.GetAwarenessCost` 按外键查不到时返回 0.0 | TeleportTakedown 的注释 |
| 追踪条 | `NPCPuppet.RevealPlayerPositionIfNeeded` 返回 false | No Reveal Position |
| 破解抬警戒 | `QuickHackableQueueHelper.IsAwarenessBumpingAllowed` 返回 false | Memory Wipe - No Trace on Spread |
| 状态效果时长 | 时长组必须包含 `BaseStatusEffect.BaseQuickHackDuration_inline0` | MAKING_CUSTOM_QUICKHACKS.md |
| 目标识别 | `StatusEffectHelper.HasStatusEffectWithTagConst(target, n"VH_SelfErase")` | Memory Wipe - No Trace on Spread |

三档时长由脚本自己计时（每 0.5 秒复检一次），不依赖 TweakDB 的时长覆盖是否生效。

---

## 6. 内部标识说明

记录 ID 前缀仍然是 `VH_`（例如 `BaseStatusEffect.VH_SelfErase`），archive 内部资源路径仍是 `base\vh_quickhacks\...`。

这些是 mod 的内部标识，改它们需要重打两个 archive 文件，对玩家没有任何可见影响，所以 1.0 保留原样。对外显示的名字统一为 **XY Quick Hack**。

---

## 7. 版本

**1.0.1 Beta** — 图标改为原版风格（纯视觉改动，数值未动）。**未经验证**。

- 自我擦除 → 原版 `ForceIgnoreTargets` 字形（蒙眼人头 + 感知波纹）
- 破解扩散 → 原版 `Broadcast` 字形（卫星天线 + 外扩波）
- 去掉了自制的着色、辉光和叠加装饰，回到原版的白字形模板印刷感
- 图集部件名没变（`VH_SelfEraseIcon` / `VH_HackSpreadIcon`），TweakDB 记录零改动

**1.0** — 首个正式版（已实测确认）。

- 三档自我擦除（蓝 60 / 紫 120 / 橙 180 秒）
- 破解扩散（20 米 / 上限 99）
- 不推警戒、不被追踪、目标行为正常
- 三家芯片商人可购买，门槛与原版对应品质一致
- 目标头顶显示自我擦除图标

### 命名约定

- X.Y —— 已在游戏里实测确认的版本
- X.Y Beta —— 未经验证的构建