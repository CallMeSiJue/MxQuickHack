# 赛博朋克 2077 Mod 制作手册（实测版）

> 来源：`cxyHack` → **XY Quick Hack** 项目（自我擦除 / 破解扩散两枚传说级快速破解）的完整开发过程。
> 目标版本：**2.50（Steam, build 26161058）**。所有结论都在本机实测过。
> 最后更新：2026-11-08（v1.0 定版当天）

---

## 0. 这份文档怎么用

| 我要…… | 看 |
|---|---|
| 确认某项行为到底由谁控制 | **§1 反编译源码**（先看这个） |
| 查某个原版记录怎么写的 | §2 |
| 新增一个快速破解 | §3 |
| 让目标「看不见我 / 不攻击我 / 不追踪我」 | **§4 状态效果 tag 机制**（核心） |
| 破解的时长不对 | §5 |
| 名字显示成 `LOCKEY#数字` | §6 / §7 |
| 图标空白 / 改不动 / 状态图标 | §8 |
| 装了两个破解只能用一个 | §9 |
| 脚本在什么时候跑、怎么不用轮询 | §10 |
| 分等级做同一个破解（蓝/紫/橙） | §11 |
| 商人卖 / 商店卖 | §12 |
| 在没游戏的机器上验证 | §13 |
| 进游戏报错但不知道看哪个日志 | §14 |

---

## 1. 最重要的一件事：游戏自带反编译源码

**90% 的「为什么不起作用」都能在这里直接查到答案，不要靠猜、不要靠社区帖子。**

```
Cyberpunk 2077\tools\redmod\scripts\cyberpunk\
    NPC\NPCPuppet.script
    NPC\scriptedPuppet.script
    gameplay\...\senseComponent.script
    ...
```

搜关键字就能定位：

```powershell
$S='D:\SOFT\Steam\steamapps\common\Cyberpunk 2077\tools\redmod\scripts\cyberpunk'
Get-ChildItem $S -Recurse -File -Filter *.script |
  Select-String -Pattern "'Stealth'" | ForEach-Object { "$($_.Filename):$($_.LineNumber): $($_.Line.Trim())" }
```

本项目所有关键结论都是这样得到的（行号均指 2.50 的这份源码）：

| 想知道 | 位置 |
|---|---|
| 状态效果被施加时会做什么 | `NPC\NPCPuppet.script:1505` `OnStatusEffectApplied` |
| 状态效果被移除时会做什么 | `NPC\NPCPuppet.script:2011` `OnStatusEffectRemoved` |
| `Blind` tag 干什么 | `NPCPuppet.script:1536` |
| `ClearThreats` tag 干什么 | `NPCPuppet.script:1550` |
| `Stealth` tag 干什么 | `NPCPuppet.script:1747` |
| 「破解后转敌对」的完整链条 | `NPCPuppet.script:1747` → `:1816` |
| `IsBlinded()` 判什么 | `NPC\scriptedPuppet.script:2066` |
| 检测遮断怎么用 | `sensorDevice.script:2351`（设一次即可） |

> 教训：我曾在 TweakDB 里反复调 `awarenessCost`、甚至自建了一整套状态效果，全都没解决问题 —— 因为真正的开关是一个 **gameplay tag**，只有读源码才能看到。

---

## 2. 原版数据金矿：`tools\redmod\tweaks`

游戏自带 TweakDB **源码**：2753 个 `.tweak`、约 30 MB、75286 条记录，全部明文。

```
tools\redmod\tweaks\base\gameplay\static_data\database\
├── object_actions\puppet_quick_hacks.tweak      所有快速破解动作
├── object_actions\device_actions.tweak          设备破解
├── object_actions\hack_categories.tweak         破解分类（只有名字和描述，没有行为）
├── status_effect\quickhack_status_effects.tweak 破解状态效果
├── status_effect\blindings.tweak                Blind 相关
├── senses\base_values.tweak                     感知预设（Senses.Blind 在这里）
├── items\cyberware\system_replacement\militech_paraline_fragments.tweak  破解物品
├── gameplay_logic_packages\equipment_abilities.tweak   EquipmentGLP（悬浮说明）
├── ui\icons\quickhacks_icons.tweak              图标记录
├── interactions\hack_interactions.tweak          菜单行
└── vendors\techstores.tweak / base_values.tweak  商人库存与可用性门槛
```

注意两点：

- `.tweak` 里的内联子记录编译后叫 `<记录名>_inlineN`（如 `QuickHack.QuickHack_inline10`），**源码里搜不到但运行时存在**（参考 mod 大量使用，安全）。
- `HackCategory` 记录只有 `enumName / enumComment / localizedDescription`，**没有行为字段** —— 所以「设成隐蔽类就不会被追踪」是错的（见 §4）。

---

## 3. 快速破解的完整数据链

```
Items.<Name>Program                物品（装进赛博义体槽）
  └─ objectActions:
       QuickHack.<Name>Hack        人形目标（ObjectActionType.PuppetQuickHack）
       DeviceAction.<Name>Hack     设备目标（DeviceAction.DeviceQuickHack）
     └─ startEffects / completionEffects → 给目标挂 BaseStatusEffect.<Name>
     └─ objectActionUI → Interactions.<Name>Hack（菜单那一行）
     └─ OnAttach: [EquipmentGLP.<Name>Program]   悬浮说明正文
```

### 3.1 物品记录

```yaml
Items.XY_SelfEraseProgram:
  $base: Items.CovertHack
  displayName: LocKey#990800001          # 必须数字 LocKey（§6）
  localizedDescription: LocKey#990800002
  quality: Quality.Legendary
  shardType: XY_SelfErase                # 见 §9
  icon: UIIcon.XY_SelfEraseIcon          # → UIIcon 记录 → 自己的图集
  iconPath: XY_SelfEraseIcon             # 也是「UIIcon.<名字>」，不是图集部件名！
  hideCooldownUI: True
  hideDurationUI: False                  # 想在菜单显示持续时间就 False
  tags:
    - !append-once Tier4Shard
  OnAttach:
    - EquipmentGLP.XY_SelfEraseProgram   # 悬浮说明（§3.5）
  objectActions:
    - QuickHack.XY_SelfEraseHack
    - DeviceAction.XY_SelfEraseDeviceHack
    - ItemAction.ProgramDisassemble
```

> `iconPath` 的解析规则见 §8 —— 它会被当成 `UIIcon.<值>` 去查记录，**这一点和很多老帖子写的「只能填原版部件名」不一样**。

### 3.2 人形 ObjectAction（参考 mod 的写法：写完整记录）

**不要用 `$base` 继承原版动作再改几个字段** —— 两个在用的参考 mod（Gravitational Pull、Teleport Takedown）都是完整手写：

```yaml
QuickHack.XY_SelfEraseHack:
  $type: gamedataObjectAction_Record
  actionName: XY_SelfErase                # 脚本靠它分派
  hackCategory: HackCategory.LegacyHack
  interactionLayer: remote
  objectActionType: ObjectActionType.PuppetQuickHack
  objectActionUI: Interactions.XY_SelfEraseHack
  priority: 4
  activationTime:
    - QuickHack.QuickHack_inline0
    - QuickHack.XY_SelfEraseHack_inline0     # 上传时间加成
  costs:
    - QuickHack.XY_SelfEraseHack_inline1     # RAM
  startEffects:
    - QuickHack.QuickHack_inline10           # ★ 通用机制，删了破解就彻底失效
    - QuickHack.XY_SelfEraseHack_inline3     # 我们的状态效果（见 §5.2）
  completionEffects:
    - QuickHack.QuickHack_inline2
    - QuickHack.QuickHack_inline6
    - QuickHack.QuickHack_inline8
    - QuickHack.QuickHack_inline9
    - QuickHack.ControlHack_inline5
    - QuickHack.XY_SelfEraseHack_inline3
  durationTime: []
  instigatorActivePrereqs: []
  instigatorPrereqs:
    - QuickHack.QuickHack_inline1             # 需要赛博甲板
  interruptionPrereqs: []
  rewards: []
  targetActivePrereqs:
    - Prereqs.QuickHackUploadingPrereq
    - Prereqs.ChimeraNoQuickHackPrereq
  targetPrereqs: []
  isQuickHack: True
  # ★ awarenessCost 整行不要写，见 §4.4
```

RAM 数值单独一条记录，三个修饰符是让技能/消耗品/目标抗性真正生效的关键（少了它们，数值是死的）：

```yaml
QuickHack.XY_SelfEraseHack_inline1:
  $type: gamedataStatPoolCost_Record
  statPool: BaseStatPools.Memory
  costMods:
    - QuickHack.MemoryCostReductionMod
    - QuickHack.ConsumableCostReduction
    - QuickHack.TargetResistanceCovert
    - QuickHack.XY_SelfEraseHack_inline2

QuickHack.XY_SelfEraseHack_inline2:
  $type: gamedataConstantStatModifier_Record
  value: 8
  modifierType: Additive
  statType: BaseStats.Memory
```

### 3.3 设备 ObjectAction

```yaml
DeviceAction.XY_SelfEraseDeviceHack:
  $base: DeviceAction.DeviceQuickHack        # 这个用 $base 是安全的
  actionName: XY_SelfEraseDevice
  objectActionUI: Interactions.XY_SelfEraseHack    # 可与人类共用同一行
  targetActivePrereqs:
    - Prereqs.ChimeraNoQuickHackPrereq      # 去掉 NetworkBreached，可直接黑摄像头
  deviceHackCategory: DeviceHacks.CovertHack
  hackTier: DeviceHacks.Tier5DeviceHack
  completionEffects:
    - !append-once QuickHack.XY_SelfEraseHack_inline3
```

> 设备破解**不需要**挂到设备角色记录上，写在玩家物品的 `objectActions` 里就会对可黑设备列出。

### 3.4 菜单那一行

```yaml
Interactions.XY_SelfEraseHack:
  $type: gamedataInteractionBase_Record
  action: Choice1
  captionIcon: ChoiceCaptionParts.XY_SelfEraseIcon
  name: XY_SelfEraseHack
  prereqID: ''
  caption: LocKey#990800001        # 也是本地化字段
  description: LocKey#990800002
```

### 3.5 悬浮说明（漏了会串成别的破解）

```yaml
EquipmentGLP.XY_SelfEraseProgram:
  $type: gamedataGameplayLogicPackage_Record
  stackable: False
  UIData: EquipmentGLP.XY_SelfEraseProgram_inline0
  animationWrapperOverrides: []
  effectors: []
  items: []
  statPools: []
  stats: []

EquipmentGLP.XY_SelfEraseProgram_inline0:
  $type: gamedataGameplayLogicPackageUIData_Record
  iconPath: ability_utility
  localizedName: LocKey#990800001
  localizedDescription: LocKey#990800002
  floatValues: []
  intValues: []
  nameValues: []
  stats: []
```

### 3.6 挂到敌人身上

`Character.<faction>_base: objectActions: [!append-once QuickHack.X]`，覆盖全游戏约 95 条记录。**设备不需要。**

---

## 4. 状态效果 tag 才是真正的机制（核心章节）

**这一章是本项目花最多时间才搞对的部分。** 结论：**控制目标行为的是状态效果的 `gameplayTags`，不是 `statusEffectType`，不是 `hackCategory`，不是 `awarenessCost`。**

### 4.1 `Blind` tag —— 让目标看不见你

`NPCPuppet.script:1536`：

```c
if( gmplTags.Contains( 'Blind' ) )
{
    SenseComponent.RequestSecondaryPresetChange( this, T"Senses.Blind" );
    ttc = GetTargetTrackerComponent();
    if( ttc )
    {
        SwitchTargetPlayerTrackedAccuracy( ttc, false );
        ttc.SetThreatBeliefAccuracy( this, 0.0 );
    }
}
```

配套的预设记录（`senses\base_values.tweak`）：

```tweak
Blind : Default
{
    shapes = [ { } : Cone ];
    detectionFactor = 0.01;      // 侦测系数压到 1%
}
```

效果：感知几乎归零、威胁信念精度归零、`IsBlinded()`（`scriptedPuppet.script:2066` 判 `HasStatusEffectWithTag('Blind')`）成立。

**副作用**：目标失去所有感知目标后会进入搜索/游荡状态。这是原版重启义眼的行为，引擎层面绕不开 —— 但只有在**它已经进入警戒/搜索之后**才明显（见 §5.2 的施加时机）。

### 4.2 `Stealth` tag —— 不转敌对

`NPCPuppet.script:1747`：

```c
if( !evt.isAppliedOnSpawn && evt.instigatorEntityID == GetPlayerID()
    && !gmplTags.Contains( 'Stealth' ) )
{
    if( QuickHackableQueueHelper.IsAwarenessBumpingAllowed( this ) )
    {
        ... DelayEvent( NonStealthQuickHackVictimEvent, 0.1 ) ...
    }
    ...
}
```

`NPCPuppet.script:1816`：

```c
protected event OnNonStealthQuickHackVictimEvent( evt : NonStealthQuickHackVictimEvent )
{
    if( !( NPCPuppet.RevealPlayerPositionIfNeeded( this, evt.instigatorID ) ) )
        NPCStatesComponent.AlertPuppet( this );
    AIActionHelper.TryChangingAttitudeToHostile( this, player );   // ← 在 if 之外！
}
```

**关键点**：`TryChangingAttitudeToHostile` 在 `if` 外面、无条件执行。所以**只 wrap `RevealPlayerPositionIfNeeded` 返回 false，只能挡住「警戒」，挡不住「转敌对」** —— 我在这上面浪费了好几轮。唯一能跳过整段的是 `Stealth` tag。

### 4.3 `ClearThreats` tag —— 清掉对你的威胁

`NPCPuppet.script:1550`：

```c
if( gmplTags.Contains( 'ClearThreats' ) )
{
    ttc = GetTargetTrackerComponent();
    if( ttc ) { ttc.ClearThreats(); }
}
```

### 4.4 `awarenessCost` —— 正确写法是「整行不写」

`ScriptableDeviceAction.GetAwarenessCost` 按外键查这个 flat，**查不到就返回 0.0**。所以：

| 写法 | 结果 |
|---|---|
| 不写这一行 | 0.0，上传不推警戒条，扫描菜单也不显示「+N%」 |
| `awarenessCost: ''` | 行为不确定，别用 |
| 引用一个非零的原版组 | 会推警戒条 |

TeleportTakedown 的源文件注释里写得很清楚，这也是它作为**潜行**破解的关键。

### 4.5 完整配方（本项目实测有效）

```yaml
gameplayTags:
  - Debuff
  - Quickhack
  - Stealth        # 不转敌对
  - Blind          # 看不见你（引擎内建，脚本替代不了）
  - ClearThreats   # 脱战
  - XY_SelfErase   # 自己的识别 tag，只给自己的脚本用
```

`Blind` + `Stealth` + `ClearThreats` 三者组合 = 原版记忆清除的 tag 集合（`quickhack_status_effects.tweak:6350`：`"MemoryWipe", "Blind", "Stealth", "ClearThreats"`）。把 `MemoryWipe` 换成自己的 tag 即可。

### 4.6 不要用脚本硬扛

我曾以为可以不用 `Blind`、只靠脚本 `SetDetectionOverwrite` 达到同样效果。**不行** —— 那是给 SenseComponent 设一个覆盖值，游戏重算时会推翻；`Blind` 是引擎自己把整条感知链路切走，两者不是一个层级。

---

## 5. 状态效果记录与时长

### 5.1 完整手写（不要继承）

两个参考 mod 都是完整记录、`packages: []`：

```yaml
BaseStatusEffect.XY_SelfErase:
  $type: gamedataStatusEffect_Record
  duration: BaseStatusEffect.XY_SelfEraseDuration
  dynamicDuration: False
  isAffectedByTimeDilationNPC: True
  isAffectedByTimeDilationPlayer: True
  maxStacks: RTDB.StatusEffect_inline0
  reapplyPackagesOnMaxStacks: True
  removeAllStacksWhenDurationEnds: False
  removeOnStoryTier: False
  replicated: True
  savable: False
  statusEffectType: BaseStatusEffectTypes.Blind
  stopActiveSfxOnDeactivate: True
  debugTags: []
  gameplayTags: [Debuff, Quickhack, Stealth, Blind, ClearThreats, XY_SelfErase]
  packages: []
  SFX: []
  VFX: []
```

### 5.2 时长：一条 `MaxDuration` 就够

```yaml
BaseStatusEffect.XY_SelfEraseDuration:
  $type: gamedataStatModifierGroup_Record
  drawBasedOnStatType: False
  optimiseCombinedModifiers: False
  saveBasedOnStatType: False
  statModsLimit: -1
  relatedModifierGroups: []
  statModifiers:
    - BaseStatusEffect.XY_SelfEraseDurationValue

BaseStatusEffect.XY_SelfEraseDurationValue:
  $type: gamedataConstantStatModifier_Record
  value: 180.0
  modifierType: Additive
  statType: BaseStats.MaxDuration
```

**踩过的坑**：

- 继承原版记录再改 `duration` 不可靠，实测退回默认 8 秒。
- 「时长组必须包含 `BaseQuickHackDuration_inline0`」**只是个例**（Gravitational Pull 这么做），Teleport Takedown 就没有，照样工作。
- 状态效果**满层时重复施加不会续期**。想延长只能「先移除再施加」。
- 更好的做法：让记录的时长负责生命周期，脚本不要自己计时（§10）。

### 5.3 `startEffects` 还是 `completionEffects`？时机决定成败

`Stealth`/`Blind` 的判断发生在**效果被施加的那一瞬间**。如果你的效果挂在 `completionEffects`（上传完成才挂），那上传的这几秒里目标没有 tag，警觉已经发生了 —— 效果落地时它早就进入警戒/搜索状态。

**要「上传一开始就生效」就挂 `startEffects`。** 本项目改到 `startEffects` 后，目标的游荡行为也随之消失（因为它从来没进入过搜索状态）。

---

## 6. 本地化（必须打进 `.archive`）

### 6.1 三条硬事实

1. 本地化资源**只能从 `.archive` 里的 CR2W `JsonResource` 加载**；散装 json + `.xl` 实测无效。
2. `redMod.exe archive-make` 不收裸 json（报 `Nothing to save as the archive is empty`）。
3. 汉化包里通常只有一个 `.archive`，没有 `.xl`。

### 6.2 序列化 JSON 的样子

```json
{
  "Header": { "WolvenKitVersion": "10.0.0-beta.1", "WKitJsonVersion": "0.0.9", "GameVersion": 2500,
              "DataType": "CR2W", "ArchiveFileName": "xy_quickhacks.json" },
  "Data": { "Version": 195, "BuildVersion": 0,
    "RootChunk": { "$type": "JsonResource", "cookingPlatform": "PLATFORM_None",
      "root": { "HandleId": "0", "Data": {
        "$type": "localizationPersistenceOnScreenEntries",
        "entries": [
          { "$type": "localizationPersistenceOnScreenEntry",
            "femaleVariant": "自我擦除", "maleVariant": "自我擦除",
            "primaryKey": "990800001", "secondaryKey": "xy_self_erase_name" }
        ]}}}}}
```

### 6.3 流程

```powershell
& $dn $cli convert d zh-cn.json -o out        # → 输出没有扩展名，自己改名
# 摆成 pack\base\<mod>\localization\{zh-cn.json, en-us.json}（CR2W）
& $dn $cli pack pack -o out                   # → out\pack.archive
```

注册：

```yaml
localization:
  onscreens:
    zh-cn: base\xy_quickhack\localization\zh-cn.json
    en-us: base\xy_quickhack\localization\en-us.json
```

tweak 里引用数字键：`displayName: LocKey#990800001`。号段自己挑高位（本项目用 `990800001+`）。

验证：`red4ext\plugins\ArchiveXL\ArchiveXL-*.log` 里出现 `Merging entries from ...`。

---

## 7. 名字与文本的常见坑

| 现象 | 根因 | 解法 |
|---|---|---|
| `LOCKEY#16664142960970199336` | `displayName` / `caption` / `localizedDescription` 是本地化键类型，写纯文本会被哈希成 64 位键名 | 用数字 LocKey + archive 里的条目（§6） |
| 悬浮框写着别的破解的文案 | 那段文字来自 `OnAttach` 的 `EquipmentGLP.UIData`，没挂就落到别处 | 建自己的 GLP（§3.5） |
| 物品名对、菜单名不对 | 菜单那行是 `Interactions.caption`，独立字段 | 两个都要配 |

---

## 8. 图标

### 8.1 三条链路，别混

| 字段 | 用在哪 | 解析规则 |
|---|---|---|
| `Items.*.icon` | 物品图标 | TweakDBID → `UIIcon` 记录 |
| `Items.*.iconPath` | 物品图标 | **`"UIIcon." + 值`** → `UIIcon` 记录 → 图集 |
| `Items.*.captionIcon`（实际在 Interactions） | 扫描菜单 | `ChoiceCaptionParts` → `UIIcon` |
| `StatusEffectUIData.iconPath` | 头顶状态图标 | **同样是 `"UIIcon." + 值`** |

所以自定义图集**三种都能用**，只要把 `UIIcon` 记录指向自己的 atlas：

```yaml
UIIcon.XY_SelfEraseIcon:
  $type: gamedataUIIcon_Record
  atlasPartName: XY_SelfEraseIcon
  atlasResourcePath: base\xy_quickhack\ui\xy_se_icon.inkatlas
```

> 旧版手册说「`iconPath` 只认原版图集部件名」是**错的** —— 实测填自己的名字 `XY_SelfEraseIcon` 能正常显示，因为它是按 `UIIcon.<名字>` 解析的。

### 8.2 头顶状态图标

状态效果加一个 `uiData`：

```yaml
BaseStatusEffect.XY_SelfEraseUI:
  $type: gamedataStatusEffectUIData_Record
  description: ''
  displayName: LocKey#990800001     # 图标旁的文字
  fluffText: ''
  iconPath: XY_SelfEraseIcon        # → UIIcon.XY_SelfEraseIcon
  priority: -9
  floatValues: []
  intValues: []
  nameValues: []
  stats: []
```

然后在状态效果里 `uiData: BaseStatusEffect.XY_SelfEraseUI`。

> `uiData` 只被 `singleCooldownManager.script:55` 这类 UI 代码读取，**不会影响 AI**。如果加图标后行为变了，原因是别的。

### 8.3 做图流程（全命令行）

```powershell
& $dn $cli unbundle -p "basegame_1_engine.archive" -o probe -w '*quickhacks_icons*'
& $dn $cli export  -p probe -o png --uext png -gp $Game -w '*.xbm'
# 用 Pillow 改图
& $dn $cli import  -p png_src -o xbm_out                 # png → xbm
& $dn $cli convert s some.inkatlas -o atlas.json         # 模板
& $dn $cli convert d xy_se_icon.inkatlas.json -o cr      # json → CR2W（无扩展名）
& $dn $cli pack pack -o out                              # 目录 → .archive
& $dn $cli unbundle -p out\pack.archive -o verify        # 回读校验
```

图集 JSON 关键结构：

```json
"slots": { "Elements": [
  { "$type": "inkTextureSlot",
    "parts": [ { "$type": "inkTextureAtlasMapper",
                 "partName": { "$type": "CName", "$storage": "string", "$value": "XY_SelfEraseIcon" },
                 "clippingRectInUVCoords": { "Bottom": 1, "Left": 0, "Right": 1, "Top": 0 } } ],
    "texture": { "DepotPath": { "$type": "ResourcePath", "$storage": "string",
                                "$value": "base\\xy_quickhack\\ui\\xy_se_icon.xbm" } } }
]}
```

---

## 9. `shardType`

`ItemModificationSystem.RemoveOtherShards`（`itemModificationSystem.script:112-130`）在每次安装时遍历甲板，**同 `shardType` 的其它程序会被静默卸下**：

```
if( GetCName( partData + T".shardType" ) == GetCName( shardID + T".shardType" ) && partData != shardID )
    RemoveItemPart( obj, item, usedSlots[ i ], false );
```

| 情况 | 结果 |
|---|---|
| 两个物品都写 `''` | 被当成同一个，只能装一个 |
| 借用原版值（`MemoryWipe`） | 会把原版那个顶掉 |
| **每个「不同破解」一个独占值** | 正确 |
| **同一破解的不同等级共用** | 也是正确的（原版记忆清除 Lvl2/3/4 都是 `MemoryWipe`），表现是互斥升级 |

---

## 10. redscript：事件驱动，不要轮询

### 10.1 为什么不能轮询

我最初每 0.5 秒重设一次 `SetDetectionOverwrite`，结果目标的**警戒条每 0.5 秒红一下又清零**，非常明显。因为每次重设都会触发重新判定。

引擎自己的用法是**设一次**（`sensorDevice.script:2351`）。

### 10.2 正确写法：状态效果的两个事件

```redscript
@wrapMethod(NPCPuppet)
protected cb func OnStatusEffectApplied(evt: ref<ApplyStatusEffectEvent>) -> Bool {
  let result: Bool = wrappedMethod(evt);
  if IsDefined(evt) && IsDefined(evt.staticData)
     && ArrayContains(evt.staticData.GameplayTags(), n"XY_SelfErase") {
    // 设置一次
  };
  return result;
}

@wrapMethod(NPCPuppet)
protected cb func OnStatusEffectRemoved(evt: ref<RemoveStatusEffect>) -> Bool {
  let result: Bool = wrappedMethod(evt);
  // 还原一次
  return result;
}
```

签名来自 `NPCPuppet.script:1505` / `:2011`。**效果时长由记录负责，脚本不要自己计时** —— 到期时引擎会触发 `OnStatusEffectRemoved`，顺势还原即可。

### 10.3 其他钩子

| 需求 | 钩子 |
|---|---|
| 上传完成时做事 | `@wrapMethod(QuickHackUploadListener) SendUploadFinishedEvent()`，取 `this.m_action` 的 `GetExecutor()` / `GetRequesterID()` / `GetObjectActionRecord().ActionName()` |
| 攻击破除 | `@wrapMethod(ScriptedPuppet) PuppetDamagePipelineFinalized(evt)`，用 `evt.attackData.GetInstigator().IsPlayer()`；DoT 用 `GetAttackType() == gamedataAttackType.Effect` 排除 |
| 拦追踪 | `NPCPuppet.RevealPlayerPositionIfNeeded(...)` 返回 false（挡「暴露」） |
| 拦警戒抬升 | `QuickHackableQueueHelper.IsAwarenessBumpingAllowed(target)` 返回 false |
| 菜单不显示「会暴露位置」 | `QuickHackableHelper.WillHackRevealPlayer(...)` 返回 false |

> `isUntraceableHack` 曾在脚本符号表里出现过，**它不是 TweakDB 字段**，只是 `WillHackRevealPlayer` 内部的局部变量。别去找它。

### 10.4 语言坑

| 坑 | 说明 |
|---|---|
| 没有 `continue` / `goto` | 只能 if/else 收尾 |
| `extends` 不能带点 | `extends Codeware.Localization.X` 报 `syntax error` |
| 跨模块类型可能解析不到 | `VirtualAtelierStoresManager` 在全局作用域直接引用会 `UNRESOLVED_TYPE`，要避开或换写法 |
| `let` 必须在函数开头声明 | 中途声明会报错 |
| `script_ref<array<...>>` 要 `Deref()` | `ArrayPush(Deref(targets), x)` |
| 枚举转字符串 | `IntToString(Cast<Int32>(enumValue))`；`EntityID.ToString()` 不存在 |
| `private` 方法跨类调用 | `@addMethod` 加的 `private` 方法在别的类里调用**能编译**（实测），但别依赖这个 |

---

## 11. 同一个破解分等级（蓝 / 紫 / 橙）

原版命名：`Lvl2 = Rare`、`Lvl3 = Epic`、`Lvl4 = Legendary`、`Lvl4PlusPlus = Legendary 强化`。

每个等级需要：**独立的 ObjectAction（人形+设备）+ 独立的状态效果（时长不同）**，但可以共用：

- `Interactions.*` 菜单行（原版记忆清除三档共用一条）
- `UIIcon` / `ChoiceCaptionParts`（同一个图标）
- 本地化条目（同名）
- `shardType`（同一种破解共用，表现互斥）

脚本侧如果要区分，用 `actionName` 分派，例如 `XY_SelfErase` / `XY_SelfEraseLvl2` / `XY_SelfEraseLvl3`。

---

## 12. 获取方式

### 12.1 商人库存

```yaml
Vendors.XY_SelfEraseStock:
  $type: gamedataVendorItem_Record
  item: Items.XY_SelfEraseProgram
  quantity:
    - Vendors.Always_Present
  generationPrereqs:
    - Vendors.LegendaryQuickhackAvailability    # 按品质选门槛
```

可用性门槛（`vendors\base_values.tweak`）：`UncommonQuickhackAvailability` / `RareQuickhackAvailability` / `EpicQuickhackAvailability` / `LegendaryQuickhackAvailability` / `LegendaryPlusPlusQuickhackAvailability`。

三家芯片商人：`Vendors.wat_kab_techstore_01` / `std_arr_techstore_01` / `std_rcr_techstore_01`。库存是**进档时生成**的，改完要跳 24 小时才刷新。

### 12.2 售价

不覆盖就继承基类（`Items.CovertHack` → `Price.BaseHackPrice + ItemQualityMultiplier + BuyPrice_StreetCred_Discount + CovertHackMultiplier`），品质差由 `ItemQualityMultiplier` 拉开。想改档位就显式写 `buyPrice` / `sellPrice`，选项如 `Price.UltimateHackMultiplier`。

### 12.3 Virtual Atelier 商店（可选依赖）

参考 mod 的做法，整个文件必须用 `@if(ModuleExists("VirtualAtelier.Systems"))` 包住，否则没装的人会**整个脚本构建失败**（redscript 是编译期解析类型）。

```redscript
@if(ModuleExists("VirtualAtelier.Systems"))
@addMethod(gameuiInGameMenuGameController)
protected cb func RegisterXyStore(event: ref<VirtualShopRegistration>) -> Bool {
  // AddStore(storeID: CName, storeName: String, items: array<String>,
  //          prices: array<Int32>, atlasResource: ResRef, texturePart: CName,
  //          opt qualities: array<String>, opt quantities: array<Int32>)
  event.AddStore(n"XyQuickHack", "XY Quick Hack",
    [ "Items.XY_SelfEraseProgram" ], [ 45000 ],
    r"base\\xy_quickhack\\ui\\xy_se_icon.inkatlas", n"XY_SelfEraseIcon",
    [ "Legendary" ]);
  return false;
}
```

注意：`AddStore` 不去重，同一 `storeID` 注册两次会**崩溃**；用自己 `@addField` 的 bool 防重复。

---

## 13. 离线校验流水线

### 13.1 脚本编译（scc）

`tools\redmod\bin\scc.exe` 或 `engine\tools\scc.exe` 都能离线编译，但**输出会写回缓存路径，绝不能把 CWD 指向游戏目录**（我第一次就覆盖了 `final.redscripts`，进游戏弹「备份已损坏」）。

```powershell
$Game='D:\SOFT\Steam\steamapps\common\Cyberpunk 2077'
$W='D:\dsh\2077MOD'
$stage="$W\.build\check\scripts"
Copy-Item "$Game\r6\scripts\*" $stage -Recurse                    # 真实环境
Copy-Item "$W\mod\r6\scripts\XY_QuickHack" $stage -Recurse       # 自己的
$i=0; Get-ChildItem "$Game\red4ext\plugins" -Directory | ForEach-Object {
  $s=Join-Path $_.FullName 'Scripts'; if(Test-Path $s){ $i++; Copy-Item $s "$stage\_plugin$i" -Recurse }
}
$env="$W\.build\env"; New-Item -ItemType Directory -Force -Path "$env\r6\cache"
Copy-Item "$W\.build\pristine_final.redscripts" "$env\r6\cache\final.redscripts" -Force
Push-Location $env
& "$Game\engine\tools\scc.exe" -compile $stage "$env\r6\cache\final.redscripts" 2>&1
Pop-Location
```

判定：输出里要有 `Compiling files in ...` 和列出的文件名 + `Compilation complete`。「exit=0 但没列文件」= **其实一个文件都没编译**，别当成通过。

### 13.2 YAML 结构与字段名

自己写极简解析器（键名可含 `.`，序列项可能是 `- !append-once X` 或 `- $type: ...`）：

1. **结构**：缩进 2 的倍数、`key:` 后必须有空格、无 Tab
2. **字段名**：把原版所有 `.tweak` 的 `字段名 =` 抽成集合，自己的每个字段名都必须在里面

### 13.3 引用校验

把 75286 条原版记录名建成集合，检查自己引用的每个 `Ns.Name`。会剩下内联名（`*_inlineN`）被判缺失，**那是正常的**。

---

## 14. 部署、日志、排查

### 14.1 部署

- 手动：解压出 `r6` + `archive` 丢进游戏根目录
- Vortex：装完**去磁盘确认**目录真实存在、没有多套一层；换名后要**先卸旧版**，否则 `r6\scripts` 下两套同名函数会编译冲突

### 14.2 日志

| 症状 | 日志 |
|---|---|
| 弹「REDScript compilation has failed」 | `r6\logs\redscript_rCURRENT.log`（末尾有文件名与行号） |
| 弹「备份已损坏」 | 删 `r6\cache\final.redscripts.modded` 和 `final.redscripts.ts`，别删 `final.redscripts` |
| 记录没生效 / 物品不存在 | `red4ext\plugins\TweakXL\TweakXL-*.log` |
| 本地化没生效 | `red4ext\plugins\ArchiveXL\ArchiveXL-*.log` 搜 `Merging entries from` |
| 自己的 `FTLog` | `bin\x64\plugins\cyber_engine_tweaks\gamelog.log` |

### 14.3 排查节奏

TweakXL 是否读完 → archive 是否合并 → 自己的 FTLog → 最后再去读反编译源码。**顺序反了就会像我一样在 TweakDB 里瞎调半天。**

---

## 15. 编码与工程习惯（血泪）

1. **不要在 PowerShell 里给 YAML/reds 写中文注释。** 这里字符串会被按 ANSI 解释，写进文件变成 `鈽?鎶勫師鐗堣` 这种乱码。YAML 要求合法 UTF-8，注释乱码有让解析失败的风险。**注释一律写英文**；必须写中文时用编辑工具写文件，别用命令行拼接。
2. 用 `[System.IO.File]::WriteAllText(path, text, (New-Object System.Text.UTF8Encoding($false)))` 写入，避免 BOM。
3. **改名要想清楚范围**：对外名（zip、目录、日志前缀）随便改；**记录前缀和 archive 内部资源路径**改了就要重打 archive，没有必要就别动。
4. 每次交付前跑一遍：scc 编译 + YAML 结构/字段名 + 引用校验 + 打包回读。
5. **版本命名**：`X.Y` = 实测确认过；`X.Y Beta` = 未验证，别当稳定版发。

---

## 16. 发版检查清单

- [ ] 记录全部用自己前缀
- [ ] `displayName` / `caption` / `localizedDescription` 都指向数字 LocKey，archive 里有对应条目
- [ ] 每个物品都挂了 `OnAttach → EquipmentGLP`，悬浮说明是自己的文案
- [ ] `icon` 与 `iconPath` 都填，且都指向自己的 `UIIcon.<名字>`
- [ ] 状态效果有 `uiData`，头顶图标正常
- [ ] `awarenessCost` **整行没写**
- [ ] 状态效果 tag 完整：`Stealth` + `Blind` + `ClearThreats` + 自己的识别 tag
- [ ] 效果挂在 `startEffects`（需要上传期间就生效时）
- [ ] 脚本里没有 `DelayEvent` 轮询
- [ ] `shardType`：不同破解互斥、同破解多等级共用
- [ ] 商人门槛按品质对应原版
- [ ] 本地编译 0 error / 0 warning（且日志确认列出了自己的文件）
- [ ] YAML 结构 0 问题、字段名 0 错误、引用只差内联名
- [ ] archive 打完 `unbundle` 回读
- [ ] 卸旧版再装新版
- [ ] 存档先备份

---

## 17. 参考

- 游戏自带反编译源码：`Cyberpunk 2077\tools\redmod\scripts\cyberpunk\` ← **最有用**
- 游戏自带 TweakDB 源码：`Cyberpunk 2077\tools\redmod\tweaks\` ← **第二有用**
- 社区 wiki：<https://wiki.redmodding.org/cyberpunk-2077-modding>
- WolvenKit CLI：<https://wiki.redmodding.org/wolvenkit/wolvenkit-cli/usage/command-list>
- 本地化 json：<https://wiki.redmodding.org/cyberpunk-2077-modding/for-mod-creators-theory/files-and-what-they-do/file-formats/translation-files--json>

在本机解包研究过的参考 mod：

| mod | 学到什么 |
|---|---|
| Gravitational Pull（Nexus 31872） | 完整手写记录；自定义状态图标走 `UIIcon`；时长组可以带 `BaseQuickHackDuration_inline0`（个例） |
| Teleport Takedown（Nexus 34325） | 附 `MAKING_CUSTOM_QUICKHACKS.md`；`startEffects` 必须保留 `QuickHack_inline10`；`shardType` 机制；**`awarenessCost` 整行不写**；`Stealth` tag 的完整解释；状态效果事件驱动写法 |
| No Reveal Position（Nexus 36277） | 追踪/暴露的三个拦截点（`RevealPlayerPositionIfNeeded` / `IsAwarenessBumpingAllowed` / `WillHackRevealPlayer`） |
| Memory Wipe - No Trace on Spread（Nexus 35499） | 按 tag 判定 `HasStatusEffectWithTagConst`；扩散保护沿链继承 |
