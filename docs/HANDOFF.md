# 交接文档（HANDOFF）

> 用途：在新会话中恢复本项目所需的全部上下文。
> 新会话开场建议直接说：「先读 `D:\dsh\2077MOD\cxyHack` 和 `DESIGN.md`，然后继续」。
> 最后更新：2026-11-08

---

## 0. 一句话概况

为赛博朋克 2077（2.50）开发一个 mod，新增两枚**传说级快速破解**：**自我擦除**（让目标看不见/听不见玩家）和**破解扩散**（把目标身上的破解效果复制给 20 米内的敌人与设备）。
当前状态：**设计完成，未开始实现，未向游戏目录写入任何文件。**

---

## 1. 用户需求（原话要点）

1. **自我擦除**
   - 上传给目标后，目标忽视主角存在：**看不见、也听不到**玩家发出的动静。
   - 持续时间按品质：蓝 60 秒 / 紫 120 秒 / 橙 180 秒。
   - 最初设定「最小蓝色」，后改为**先只做 5 级传说**（180 秒），蓝/紫以后再加。
   - **对设备也生效**（摄像头、炮塔）。
2. **破解扩散**
   - 把目标身上**已有的快速破解效果**扩散到 20 米内的目标。
   - 只有橙色（传说）。
   - **对设备也生效**。
   - **数量不设限，只限范围**；用 99 作为硬上限安全阀。
   - **可以**把「自我擦除」也扩散出去。
3. 其它
   - 玩家**攻击**某个目标时，**自我擦除只对该目标失效**（其他目标不受影响）。
   - RAM：自我擦除 **8**，破解扩散 **12**。
   - 上传时间、冷却、获取途径等细节尚未定。

---

## 2. 已拍板的决策

| # | 问题 | 决定 |
|---|---|---|
| 1 | 品质 | 两者都先做传说（Tier 5） |
| 2 | RAM | 自我擦除 8；扩散 12 |
| 3 | 对设备 | 两个都生效 |
| 4 | 攻击破除 | 是，仅对被攻击目标 |
| 5 | 扩散含自我擦除 | 是 |
| 6 | 扩散数量 | 99 硬上限，实际受 20 米范围约束 |
| 7 | 蓝/紫变体 | 传说版跑通后再加 |

---

## 3. 当前文件

| 路径 | 说明 |
|---|---|
| `D:\dsh\test\2077mod\DESIGN.md` | 设计文档 v0.2（207 行）——概念、参数、技术映射、记录清单、风险、里程碑 |
| `D:\dsh\test\2077mod\HANDOFF.md` | 本文档 |
| `D:\dsh\test\research\tweakdb_items.txt` | 从本机 `tweakdb.bin` 提取的 4682 条 `Items.*` 记录名 |
| `D:\dsh\test\research\tweakdb_qh_strings.txt` | `tweakdb.bin` 中含 quickhack 的 680 条字符串 |
| `D:\dsh\test\research\scripts_qh_strings.txt` | `final.redscripts` 中含 quickhack 的 848 条字符串（类名/函数名） |

**尚未创建**：`r6/`、`archive/`、`dist/` 等实际 mod 目录（设计文档中只是规划）。

---

## 4. 环境（实测）

### 4.1 游戏与框架

| 项目 | 值 |
|---|---|
| 游戏目录 | `D:\SOFT\Steam\steamapps\common\Cyberpunk 2077` |
| 版本 | 2.50（build 26161058，File 3.0.88.46235） |
| RED4ext | 1.31.0 |
| TweakXL | 1.12.0 |
| ArchiveXL | 1.28.1 |
| Codeware | 1.21.2 |
| input_loader | 0.2.6 |
| mod_settings | 0.2.22 |
| CET | 1.38.1 |
| redscript | 正常（scc 编译 27752 refs，输出 `final.redscripts.modded`） |
| ASI 加载器 | Ultimate ASI Loader（`bin\x64\version.dll`） |

### 4.2 已装 mod（都不与快速破解冲突）

CET mods：AutoLoot、BetterOpticalCamo、nativeSettings、simplemenu、StreamingBugWorkaround、VirtualAtelierCore
r6/scripts：EquipmentEx、VirtualAtelier、VirtualCarDealer、BrowserExtension、ItemModificationUnlocker、NoIntroVideos、RemoveModsMenu 等
archive/pc/mod：服装类（Hizuki、Panam、Judy、Misty、Sub_* 系列、VirtualAtelier、VirtualCarDealer、EquipmentEx）

### 4.3 工具

- **WolvenKit：未安装**（做自定义 `.inkatlas` 图标、TweakDB 记录浏览需要，第一版可不装）
- Python 3.13、Git、Node、dotnet：都有
- **PowerShell 无外网出口**（curl 全部 000）；网页抓取工具只能拿文本，**无法下载 mod 文件**
- **Nexus 全站 403**（Cloudflare），API 需要 key → **无法代下载**

---

## 5. 技术调研结论（重要，别重复查）

### 5.1 快速破解的数据链

```
Items.*Program（ItemType.Program，装进 cyberdeck 槽）
  └─ ObjectAction 记录（gamedataObjectActionType.PuppetQuickHack / DeviceQuickHack）
       └─ 状态效果（BaseStatusEffect.*）+ Effector
            └─ flat：RAM 消耗、上传时间、持续时间、伤害、传播…
```

- 官方 wiki 明确：伤害型破解（Overheat/Contagion/短路）的物品、上传流程、状态效果、数值**几乎全在 TweakDB**。
- 本机 `tweakdb.bin` 实测存在的原版记录家族：
  `Items.OverheatProgram / OverheatLvl2..Lvl4PlusPlusProgram`、`PingProgram`、`ContagionProgram`、`MemoryWipeProgram`、`SuicideLvl3/4Program`、`WeaponMalfunctionProgram`、`LocomotionMalfunctionProgram`、`BlindProgram`，以及对应 `Items.Recipe_*`。
- 反编译代码里 `ApplyQuickhackEffector` 从记录读 `.objectAction`、`.uploadChance`、`.uploadTime` 三个 flat。

### 5.2 感知系统（自我擦除的核心）

2.5 版 `SenseComponent`（`core/components/senseComponent.swift`）可直接调用：

| 需求 | 接口 |
|---|---|
| 关听觉 | `SetHearingEnabled(false)` |
| 取消对玩家检测 | `SetDetectionOverwrite(entityID)` + `SetDetectionAttitudeOverwrite(n"player")` |
| 整体关感知 | `ToggleSenses(false)` / `ToggleComponent(false)` |
| 强制重算 | `ReevaluateDetectionOverwrite(target)` |
| 致盲判断 | `ScriptedPuppet.IsBlinded(owner)` |

已知：设备与人形共用同一组件；设备**没有** TargetTracker，脱战逻辑要单独处理。

### 5.3 扩散系统

原版实体：`SpreadInitEffector`、`SpreadEffector`、`SpreadAreaEffector`、`HackingDataDef.AddItemToSpreadMap()`。
本设计不改原版扩散，另写 `VH_HackSpreadEffector`；核心 API 是 `StatusEffectSystem.GetAppliedEffects()` + 范围取目标。
**注意**：设备不在 `GetNPCsAroundObject` 结果里，需要单独的设备范围查询（待实测）。

### 5.4 反编译源码（极有用）

<https://codeberg.org/adamsmasher/cyberpunk>（branch `master`，commit `17c62d0`，提交信息就是 "2.5"，与本机版本一致）
- `core/gameplay/effectors/applyQuickhackEffector.swift`
- `core/gameplay/effectors/quickhackEffectors.swift`（Spread/Madness/Ping/SetFriendly 等）
- `core/components/senseComponent.swift`
- 注意：raw 链接要用 `/raw/branch/master/<path>`；API 内容列表用 `https://codeberg.org/api/v1/repos/adamsmasher/cyberpunk/contents/<path>`；仓库目录搜索比整树拉取更省流量。

### 5.5 社区先例

- 新增破解：Gravitational Force（Nexus 31872）、Thunderclap（31484）、Blackwall Takedown（32126）、Blackwall NewGen（36105）、Teleport Takedown（34325）、寡妇之网/Widow's Web（35195）
- 扩散类：Ultimate Spreader（32994，RedScript，改扩散次数，**已停更**）、Memory Wipe - No Trace on Spread（35499）
- 组合类：Quickhack Combos - 21 New Synergies（33920）
- Cyberscript 的 quickhack JSON 字段样例（cost/uploadtime/duration/action/icon）：<https://raw.githubusercontent.com/cyberscript77/wiki/refs/heads/main/create-custom-quickhack.md>

---

## 6. 待确认 / 未决

1. **DoT 算不算「攻击」**：建议只有玩家直接命中才破除自我擦除，燃烧/中毒跳伤不算。否则 8 RAM 白花。（未定）
2. **扩散到设备时的效果过滤**：设备吃不下人类 debuff（义体故障、致盲等），计划按目标类型过滤。（未定，倾向按此做）
3. **上传时间 / 冷却 / 获取途径**：全部未定。
4. **99 目标同时失明的性能**：先按设计做，实测再定是否需要同屏上限。
5. 用户在某个客户端看不到回复（可能是鸿蒙/手机端不显示文件卡片），原因未确认——**不影响项目**，但沟通时尽量用纯文字。

---

## 7. 下一步（建议顺序）

### M0 记录核对（先做，纯只读）
目标：拿到 2.5 版本下这几个记录的真实字段：
- `Items.OverheatProgram`、`Items.PingProgram`（物品记录）
- 对应的 ObjectAction、BaseStatusEffect
- 状态效果挂 Effector 的写法

两条路：
- **A. 装 WolvenKit**，用 TweakDB 浏览器直接看（最稳，但需要用户同意安装）
- **B. 进游戏用 CET 控制台**：`TweakDB:GetRecord("Items.OverheatProgram")` / `TweakDB:DebugStats()`（需要用户启动游戏）

### M1 数据层
在 `2077mod/r6/tweaks/VH_Quickhacks.yaml` 写物品、ObjectAction、状态效果、配方记录；先不挂 Effector，验证物品能出现在菜单/能上传。

### M2 自我擦除脚本
`VH_SelfEraseEffector`：ActionOn 施加感知遮断；ActionOff 还原；监听玩家伤害事件，对被打目标移除效果。

### M3 破解扩散脚本
`VH_HackSpreadEffector`：读效果 → 过滤 → 20 米内人+设备 → 重新施加；防递归标记；99 上限。

### M4 打磨
图标（先复用原版 `UIIcon`）、本地化、配方前置、平衡。

### M5 打包
`2077mod/dist/` 输出可安装 zip。

---

## 8. 硬约束（务必遵守）

- 可写范围：**仅 `D:\dsh\test`**（工作区）。游戏目录在 `D:\SOFT\...`，**在工作区外**，写入需要用户逐次批准。
- 因此：**在 `2077mod/` 里开发，不直接写游戏目录**；需要安装时先问用户。
- 所有记录用 `VH_` 前缀，避免与其它 mod 冲突。
- 改动前先备份存档；新增物品先用测试存档验证。
- 参考第三方 mod 时注意授权，发布前看 permissions。

---

## 9. 参考链接

- TweakDB 官方说明：<https://wiki.redmodding.org/scripting-cyberpunk/scripting/game-systems/tweakdb.md>
- TweakXL YAML 基础：<https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators-theory/core-mods-explained/tweakxl/tweakxl-changing-game-records/how-to-yaml-tweak-modding-basics>
- 反编译源码：<https://codeberg.org/adamsmasher/cyberpunk>
- 官方 wiki 索引（可加 `.md` 取纯文本）：<https://wiki.redmodding.org/cyberpunk-2077-modding/llms.txt>、<https://wiki.redmodding.org/scripting-cyberpunk/llms.txt>
