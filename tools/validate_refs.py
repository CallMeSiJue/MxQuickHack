# -*- coding: utf-8 -*-
"""检查我引用的原版记录是否真实存在（对照 tools\\redmod\\tweaks 全量源码）。"""
import os, re, io

TWEAKS = r"D:\SOFT\Steam\steamapps\common\Cyberpunk 2077\tools\redmod\tweaks"
MOD_YAML = r"D:\dsh\2077MOD\mod\r6\tweaks\XY_QuickHack"

rec_re = re.compile(r'^([A-Za-z0-9_]+)\s*:\s*[A-Za-z0-9_\.]+\s*$')
pkg_re = re.compile(r'^\s*package\s+([A-Za-z0-9_\.]+)')

vanilla = set()
for root, dirs, fs in os.walk(TWEAKS):
    for f in fs:
        if not f.endswith('.tweak'):
            continue
        text = io.open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
        pkg = None
        for line in text.splitlines():
            m = pkg_re.match(line)
            if m:
                pkg = m.group(1); break
        if not pkg:
            continue
        for line in text.splitlines():
            m = rec_re.match(line)
            if m:
                vanilla.add(pkg + '.' + m.group(1))

# 我定义的记录
mine = set()
for fname in os.listdir(MOD_YAML):
    if not fname.endswith('.yaml'):
        continue
    for line in io.open(os.path.join(MOD_YAML, fname), encoding='utf-8'):
        m = re.match(r'^([A-Za-z0-9_]+\.[A-Za-z0-9_]+):\s*$', line.rstrip())
        if m:
            mine.add(m.group(1))

# 收集引用（去掉注释）
refs = {}
for fname in sorted(os.listdir(MOD_YAML)):
    if not fname.endswith('.yaml'):
        continue
    for line in io.open(os.path.join(MOD_YAML, fname), encoding='utf-8'):
        code = line.split('#', 1)[0]
        code = re.sub(r'^\s*-\s*', '', code)
        code = code.replace('!append-once', '').replace('!append', '')
        for m in re.finditer(r'(?<![\w\.:])([A-Z][A-Za-z0-9_]*\.[A-Za-z0-9_]+)', code):
            refs.setdefault(m.group(1), set()).add(fname)

ENUM = ('Quality.', 'ItemType.', 'ItemCategory.', 'BaseStats.', 'BaseStatPools.',
        'BaseStatusEffectTypes.', 'ObjectActionReference.', 'DeviceHacks.',
        'HackCategory.', 'ObjectActionType.', 'AttackType.', 'VendorType.',
        'StatusEffectAIBehaviorType.', 'StatusEffectAIBehaviorFlag.')

missing = []
for tok, where in sorted(refs.items()):
    if tok in mine or tok.startswith(ENUM):
        continue
    if tok in vanilla:
        continue
    missing.append((tok, sorted(where)))

print("原版记录总数:", len(vanilla))
print("我定义的记录:", len(mine))
print()
print("=== 引用了但原版里没有的 ===")
if missing:
    for t, w in missing:
        print("  %-46s <- %s" % (t, ','.join(w)))
else:
    print("  （无）")

print()
print("=== 关键 $base 是否都存在 ===")
for b in ['QuickHack.CovertHack', 'QuickHack.ControlHack', 'DeviceAction.DeviceQuickHack',
          'Items.CovertHack', 'BaseStatusEffect.CovertQuickHackStatusEffect',
          'BaseStatusEffect.BaseQuickHackStatusEffect', 'BaseStatusEffect.BaseQuickHackDuration_inline0',
          'Vendors.Always_Present', 'Vendors.LegendaryQuickhackAvailability',
          'Vendors.wat_kab_techstore_01', 'Vendors.std_arr_techstore_01', 'Vendors.std_rcr_techstore_01',
          'UIIcon.MemoryWipe', 'UIIcon.Contagion',
          'ChoiceCaptionParts.MemoryWipeIcon', 'ChoiceCaptionParts.ContagionIcon',
          'Prereqs.ChimeraNoQuickHackPrereq', 'QuickHack.HackingResistanceUploadModifier',
          'QuickHack.MemoryCostReductionMod', 'QuickHack.ConsumableCostReduction',
          'QuickHack.TargetResistanceCovert', 'QuickHack.TargetResistanceControl',
          'ItemAction.ProgramDisassemble']:
    print("  %-52s %s" % (b, "OK" if b in vanilla else "缺失!"))
