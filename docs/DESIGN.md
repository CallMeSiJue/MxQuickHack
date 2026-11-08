# 赛博朋克 2077 快速破解扩展 · 设计文档

| 项目 | 内容 |
|---|---|
| 文档版本 | v0.2（设计稿，未实现） |
| 更新日期 | 2026-11-08 |
| 目标游戏版本 | 2.50（Steam，build 26161058） |
| 技术栈 | TweakXL 1.12.0 / ArchiveXL 1.28.1 / Codeware 1.21.2 / redscript / RED4ext 1.31.0 |
| 状态 | 设计阶段，未向游戏目录写入任何文件 |

---

## 1. 项目定位

在现有快速破解体系上新增两枚**传说级（Tier 5 / Legendary）**快速破解：

1. **自我擦除（Self-Erase）** —— 让目标在持续时间内既看不见、也听不见玩家；**对设备同样生效**。
2. **破解扩散（Hack Diffusion）** —— 把目标身上已有的快速破解效果，复制给 20 米内的其他敌人**和设备**。

设计原则：

- **不改 UI**：复用原版快速破解菜单的显示逻辑，不新增界面。
- **先复用图标**：第一版直接引用原版 `UIIcon`，跑通逻辑后再考虑自绘 `.inkatlas`。
- **数据驱动优先**：能用 TweakDB 记录解决的，不写脚本；必须写脚本的部分收敛到单个 Effector。
- **可回退**：所有改动集中在独立记录前缀 `VH_`，删除即还原。

---

## 2. 总览

| 破解 | 记录代号 | 品质 | RAM 消耗 | 上传时间 | 持续时间 | 冷却 | 目标类型 |
|---|---|---|---|---|---|---|---|
| 自我擦除 | `VH_SelfEraseProgram` | 传说（Tier 5） | **8** | 【待定】 | **180 秒** | 【待定】 | 人类 / 人形敌人 + **设备** |
| 破解扩散 | `VH_HackSpreadProgram` | 传说（Tier 5） | **12** | 【待定】 | 瞬发 | 【待定】 | 人类 / 人形敌人 + **设备** |

> 说明：两个破解当前都按「5 级 / 传说」单版本实现。自我擦除预留蓝（Rare，60s）、紫（Epic，120s）两个降级变体，等传说版跑通后再加。

---

## 3. 自我擦除（Self-Erase）

### 3.1 概念

向目标上传一段「认知遮蔽」程序。程序生效期间，目标**无法把玩家识别为可感知对象**：

- 视觉：不再对玩家产生发现度、不再把玩家标记为可疑/敌对目标；
- 听觉：玩家发出的脚步、枪声、动作噪音不再触发该目标的反应；
- 战斗：若目标已进入战斗，需要额外清空其对玩家的威胁/仇恨，否则会「看不见但照打」。

### 3.2 参数

| 参数 | 值 | 说明 |
|---|---|---|
| 品质 | 传说（Tier 5） | 当前唯一版本 |
| RAM 消耗 | **8** | 用户已定 |
| 持续时间 | **180 秒** | 与「橙色 = 3 分钟」的设定一致 |
| 范围 | 单体 | 只对上传目标生效 |
| 是否可叠加 | 否 | 重复上传刷新持续时间 |
| 对设备 | **是** | 摄像头/炮塔使用同一套感知组件；设备走 `DeviceQuickHack` 类 ObjectAction，需单独记录 |

### 3.3 行为细则

1. 上传完成后目标立即失去对玩家的感知。
2. 期间目标仍会对**其他威胁**（同伴被攻击、爆炸、其他敌人）做出反应 —— 这是刻意的，避免变成「全场变木头」。
3. 结束后目标恢复感知；若玩家仍在其视野内，按原版规则重新积累发现度。
4. **玩家主动攻击目标（对其造成伤害）时，自我擦除立即对该目标失效**：移除状态效果、恢复感知，目标按原版规则重新积累发现度。
   - 只对「被攻击的那个目标」失效，其他被擦除的目标不受影响。
   - 技术落点：监听伤害事件（instigator 为玩家）→ 移除该目标身上的 `BaseStatusEffect.VH_SelfErase`。
5. 对设备同样适用「攻击破除」：玩家射击摄像头/炮塔时，该设备的擦除状态解除。

### 3.4 技术映射（研究结论）

原版 `SenseComponent` 暴露了可直接调用的接口，无需改渲染：

| 需求 | 接口 |
|---|---|
| 关听觉 | `SetHearingEnabled(false)` |
| 取消对玩家的检测 | `SetDetectionOverwrite(playerEntityID)` + `SetDetectionAttitudeOverwrite(n"player")` |
| 整体关闭感知 | `ToggleSenses(false)` / `ToggleComponent(false)` |
| 强制立即重算 | `ReevaluateDetectionOverwrite(player)` |
| 已致盲判定 | `ScriptedPuppet.IsBlinded(owner)`（内部已有「致盲不检测」分支） |

实现方式：一条状态效果 + 一个自定义 Effector（`VH_SelfEraseEffector`），在 `ActionOn` 里施加上述状态，在 `ActionOff` / `Uninitialize` 里还原。设备与人形共用同一个 Effector，按目标类型走不同分支（设备没有 TargetTracker，需单独处理「脱战」逻辑）。

### 3.5 已知风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| 小队情报共享 | 目标看不见玩家，但其队友可能照常锁定玩家 | 第一版接受；后续可评估压制小队播报 |
| 已锁定仇恨 | 光关感知不足以让其停止攻击 | `ActionOn` 内清空 TargetTracker 威胁，强制脱战（需实测） |
| 剧情强制敌对 | 任务脚本写死的敌对状态无法压制 | 文档标注为已知限制 |
| 对 Boss 生效 | 可能破坏 Boss 战设计 | 通过 Prereq 排除 Boss/剧情 NPC，或接受 |
| 攻击破除的判定 | 需要区分「玩家造成的伤害」与「环境/队友伤害」 | 伤害事件里校验 instigator 实体，只认玩家 |
| 设备差异 | 设备没有仇恨系统，视觉判定路径与人形不同 | 设备分支单独实测 |

---

## 4. 破解扩散（Hack Diffusion）

### 4.1 概念

对目标上传后，读取目标身上**当前生效的快速破解类状态效果**，将其复制给 20 米内的其他敌人与设备。

与「寡妇之网」这类 mod 的区别：本设计是**立即复制既有 debuff**，而不是等目标死亡/到期后扩散自身效果。

### 4.2 参数

| 参数 | 值 | 说明 |
|---|---|---|
| 品质 | 传说（Tier 5） | 仅此一档 |
| RAM 消耗 | **12** | 用户已定 |
| 半径 | 20 米 | 以目标为圆心 |
| 目标数上限 | **99**（硬上限） | 实际受 20 米范围约束；99 只作安全阀 |
| 是否对设备生效 | **是** | 摄像头/炮塔也会被扩散、也会成为扩散源 |
| 是否扩散 DoT | 是 | 需限制层数/刷新规则 |
| 是否扩散「自我擦除」 | **是** | 会把失明状态传出去，可能一片敌人集体失明 |
| 命中判定 | 视线内 / 无视墙体 | 【待定】 |

### 4.3 行为细则

1. 读取目标已应用效果 → 过滤出「破解类」。
2. 过滤规则（按优先级）：
   - 白名单：带 `QuickHack` 相关 GameplayTag 的效果；
   - **「自我擦除」在白名单内**（用户确认允许扩散）；
   - 黑名单：本扩散效果自身、玩家增益、非破解 debuff（流血/中毒等）。
3. 对 20 米内每个符合条件的敌人/设备，以玩家为施法者重新施加同一状态效果记录。
4. 被扩散的效果**不再触发扩散**（加递归标记），避免 A→B→A 无限循环。
5. 扩散不消耗额外 RAM（RAM 只在施放时扣一次）。
6. 目标数达到 99 或范围耗尽时停止。

### 4.4 技术映射（研究结论）

原版已有扩散框架可参考/复用：

| 原版实体 | 作用 |
|---|---|
| `SpreadInitEffector` | 初始化扩散目标池、次数、半径 |
| `SpreadEffector` | 执行一次扩散 |
| `SpreadAreaEffector` | 范围扩散 |
| `HackingDataDef.AddItemToSpreadMap()` | 扩散目标池 |
| `StatusEffectSystem.GetAppliedEffects()` | 读取已应用效果（本设计核心） |
| `GameObject.GetNPCsAroundObject(range)` | 取范围内 NPC |

实现方式：`VH_HackSpreadEffector`（自定义 Effector），按 4.3 的流程执行；不直接改原版扩散框架，避免与其他 mod 冲突。设备需要单独的取目标路径（设备不在 NPC 列表里），走 `GetDevicesAroundObject` 或等价接口（待实测）。

### 4.5 已知风险

| 风险 | 说明 | 缓解 |
|---|---|---|
| 递归扩散 | A 扩散给 B，B 又扩散 | 递归标记 + 只允许一层 |
| 扩散非破解效果 | 把流血/燃烧散出去 | 严格白名单 + GameplayTag 过滤 |
| 性能 | 20 米内目标多（上限 99）+ DoT 叠加 | 按范围收敛；仍需压测人群场景 |
| 集体失明 | 自我擦除被扩散，20 米内敌人全瞎 | 用户明确允许；作为「高 RAM 换强力」的设计接受 |
| 设备取目标 | 设备不在 NPC 查询结果里 | 单独实现设备范围查询 |
| 与其他 mod 冲突 | Ultimate Spreader 等也改扩散 | 不接管原版扩散，只新增独立 Effector |

---

## 5. 技术实现方案

### 5.1 目录结构（规划）

```
2077mod/
├── DESIGN.md                        ← 本文档
├── r6/
│   └── tweaks/
│       └── VH_Quickhacks.yaml       ← TweakXL 记录定义
├── r6/scripts/
│   └── VH_Quickhacks/
│       ├── VH_SelfEraseEffector.reds
│       └── VH_HackSpreadEffector.reds
├── archive/pc/mod/
│   └── VH_Quickhacks.archive.xl     ← 图标/本地化（后续）
└── dist/                            ← 打包输出（zip）
```

### 5.2 数据层记录清单

| 记录 ID | 类型 | 说明 |
|---|---|---|
| `Items.VH_SelfEraseProgram` | `gamedataItem_Record` | 自我擦除物品，`ItemType.Program` |
| `Items.VH_HackSpreadProgram` | `gamedataItem_Record` | 破解扩散物品 |
| `Items.Recipe_VH_SelfEraseProgram` | 配方 | 制作解锁 |
| `Items.Recipe_VH_HackSpreadProgram` | 配方 | 制作解锁 |
| `ObjectAction.VH_SelfErase` | `ObjectAction_Record` | 人形目标，类型 `PuppetQuickHack` |
| `ObjectAction.VH_SelfEraseDevice` | `ObjectAction_Record` | 设备目标，类型 `DeviceQuickHack` |
| `ObjectAction.VH_HackSpread` | `ObjectAction_Record` | 人形目标，类型 `PuppetQuickHack` |
| `ObjectAction.VH_HackSpreadDevice` | `ObjectAction_Record` | 设备目标，类型 `DeviceQuickHack` |
| `BaseStatusEffect.VH_SelfErase` | `StatusEffect_Record` | 持续 180s，挂 Effector |
| `BaseStatusEffect.VH_HackSpread` | `StatusEffect_Record` | 瞬发，挂 Effector |
| `Effector.VH_SelfEraseEffector` | 自定义 Effector | 感知遮断 + 攻击破除 |
| `Effector.VH_HackSpreadEffector` | 自定义 Effector | 效果复制 |

> 具体字段（`cost` / `uploadTime` / `duration` / `icon` / `localizedDescription`）在动手前用 TweakDB 浏览工具对照 2.5 实际记录确认，不凭记忆写。

### 5.3 资源层

- **图标**：第一版复用原版 `UIIcon`（如记忆清除/系统重置的图标），零依赖、零美术。
- **本地化**：名称与描述走 ArchiveXL 的本地化文件，先英文，中文可选。
- **获取途径**：优先「制作配方」，其次商人库存；测试阶段用 CET 直接刷物品。

---

## 6. 兼容性与风险（全局）

1. **版本敏感**：游戏 2.50，官方/社区数据随更新变动，2.0 之前的老攻略不可照抄。
2. **存档安全**：新增物品首次进入存档，先用测试存档验证。
3. **与其他快速破解 mod 冲突**：若对方也改原版扩散/感知逻辑，需要人工排查加载顺序。
4. **授权**：若参考/复用第三方 mod 的素材或记录结构，发布前确认其 permissions 并署名。
5. **命名隔离**：所有记录使用 `VH_` 前缀，绝不复用他人记录名。

---

## 7. 待验证清单（动手前必须确认）

- [ ] `SenseComponent` 的 `SetHearingEnabled` / `SetDetectionOverwrite` 在 2.5 的脚本绑定中可直接调用（已从反编译源码确认存在，待实测权限）。
- [ ] 强制脱战/清仇恨的正确调用点（`TargetTracker` / `ReactionManager`）。
- [ ] 设备目标的感知组件行为差异（无 TargetTracker，视觉判定路径不同）。
- [ ] 快速破解物品在菜单中的发现规则（是否仅靠 `ItemType.Program`，还是需要额外标记）。
- [ ] 状态效果的 GameplayTag 中，哪些能稳定标识「破解类」。
- [ ] 20 米内「人 + 设备」混合查询的正确接口与性能。
- [ ] 伤害事件监听：只认玩家为 instigator 的判定方式。
- [ ] 传说级物品的制作配方前置（需要哪些材料/图纸）。

---

## 8. 里程碑

| 阶段 | 内容 | 产出 |
|---|---|---|
| M0 | 环境与记录确认 | 原版记录字段对照表 |
| M1 | 自我擦除（数据层） | 可上传、无效果的占位破解 |
| M2 | 自我擦除（脚本层） | 感知遮断生效（人 + 设备） |
| M3 | 破解扩散（数据 + 脚本） | 20 米复制生效（人 + 设备） |
| M4 | 打磨 | 图标、本地化、配方、平衡 |
| M5 | 打包发布（可选） | zip / Vortex 可安装包 |

---

## 9. 决策记录（已拍板）

| # | 问题 | 决定 |
|---|---|---|
| 1 | 两个破解的 RAM 消耗 | **自我擦除 8，破解扩散 12** |
| 2 | 自我擦除是否对设备生效 | **是** |
| 3 | 破解扩散是否对设备生效 | **是** |
| 4 | 玩家攻击是否破除自我擦除 | **是，仅对被打的目标破除** |
| 5 | 扩散是否包含「自我擦除」 | **是** |
| 6 | 破解扩散的目标数上限 | **99（安全阀，实际受 20 米范围约束）** |
| 7 | 是否需要蓝/紫降级版本 | 传说版跑通后再加 |

---

## 10. 参考与依据

- TweakDB 中快速破解的实现方式（官方 wiki）：<https://wiki.redmodding.org/scripting-cyberpunk/scripting/game-systems/tweakdb.md>
- TweakXL 记录改写基础：<https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators-theory/core-mods-explained/tweakxl/tweakxl-changing-game-records/how-to-yaml-tweak-modding-basics>
- 2.5 版反编译脚本（感知组件、Effector 实现）：<https://codeberg.org/adamsmasher/cyberpunk>
- 同类 mod 参考：Ultimate Spreader（Nexus 32994）、寡妇之网（Nexus 35195）、Memory Wipe - No Trace on Spread（Nexus 35499）、Quickhack Combos（Nexus 33920）
- 本机数据：`Items.OverheatProgram` / `PingProgram` / `SuicideLvl3Program` 等家族（取自本机 `r6/cache/tweakdb.bin`）

---

## 11. 变更记录

| 版本 | 日期 | 变更 |
|---|---|---|
| v0.1 | 2026-11-08 | 初稿：确定两个破解的概念、参数、技术路线与风险 |
| v0.2 | 2026-11-08 | 定稿参数：RAM 8/12；两者对设备生效；攻击破除自我擦除；扩散包含自我擦除；扩散上限 99 |
