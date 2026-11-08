# -*- coding: utf-8 -*-
"""离线校验 TweakXL YAML：结构解析 + 字段名核对 + 记录清单。"""
import os, re, io

TWEAKS = r"D:\SOFT\Steam\steamapps\common\Cyberpunk 2077\tools\redmod\tweaks"
MOD_YAML = r"D:\dsh\2077MOD\mod\r6\tweaks\XY_QuickHack"
REPORT = r"D:\dsh\2077MOD\.build\validate_report.txt"

out = []
def p(s=""):
    out.append(s)

# ---------------- 原版字段名集合 ----------------
field_re = re.compile(r'(?:^|[\s\[])([A-Za-z_][A-Za-z0-9_]*)\s*=[^=]')
vanilla_fields = set()
for root, dirs, fs in os.walk(TWEAKS):
    for f in fs:
        if not f.endswith('.tweak'):
            continue
        text = io.open(os.path.join(root, f), encoding='utf-8', errors='ignore').read()
        for line in text.splitlines():
            s = line.strip()
            if not s or s.startswith('#') or s.startswith('[') or s.startswith(']'):
                continue
            for m in field_re.finditer(s):
                vanilla_fields.add(m.group(1))
p("原版字段名种类: %d" % len(vanilla_fields))

# ---------------- 极简 YAML 解析 ----------------
KEY_RE = re.compile(r'^([A-Za-z_\$][A-Za-z0-9_\.\$]*):(?:\s+(.*))?$')
TAG_RE = re.compile(r'^!([A-Za-z\-]+)(?:\s+(.*))?$')

def parse_document(lines, fname, errs):
    root = {}
    stack = [(-2, root)]     # (key_indent, container)
    pending = None           # (key_indent, key, parent_dict)

    def container_at(indent):
        for i in range(len(stack) - 1, -1, -1):
            if stack[i][0] < indent:
                return stack[i][1]
        return stack[0][1]

    for lineno, raw in enumerate(lines, 1):
        if '\t' in raw:
            errs.append("%s:%d 含 Tab" % (fname, lineno))
        line = raw.rstrip()
        s = line.lstrip(' ')
        if not s or s.startswith('#'):
            continue
        indent = len(line) - len(s)
        if indent % 2 != 0:
            errs.append("%s:%d 缩进非 2 的倍数: %r" % (fname, lineno, line))

        # 先把上一行挂起的 "key:" 解析成容器
        if pending and indent > pending[0]:
            pend_parent = pending[2]
            container = pend_parent.get(pending[1])
            if not isinstance(container, (dict, list)):
                container = [] if s.startswith('-') else {}
                pend_parent[pending[1]] = container
            stack = [x for x in stack if x[0] <= pending[0]]
            stack.append((pending[0], container))
            pending = None
        elif pending:
            pending = None

        if s == '-' or s.startswith('- '):
            item = s[1:].strip()
            parent = container_at(indent)
            if not isinstance(parent, list):
                errs.append("%s:%d 序列项出现在非序列上下文: %r" % (fname, lineno, line))
                continue
            m = TAG_RE.match(item)
            if m:
                parent.append({'__tag': m.group(1), '__val': (m.group(2) or '').strip()})
                continue
            km = KEY_RE.match(item)
            if km:
                d = {}
                parent.append(d)
                stack = [x for x in stack if x[0] < indent]
                stack.append((indent, d))
                key, rest = km.group(1), (km.group(2) or '').strip()
                if rest:
                    d[key] = rest
                else:
                    d[key] = None
                    pending = (indent, key, d)
                continue
            parent.append(item)
            continue

        km = KEY_RE.match(s)
        if not km:
            errs.append("%s:%d 无法解析: %r" % (fname, lineno, line))
            continue
        key = km.group(1)
        rest = (km.group(2) or '').strip()
        parent = container_at(indent)
        if isinstance(parent, list):
            errs.append("%s:%d 键值出现在序列上下文: %r" % (fname, lineno, line))
            continue
        if rest:
            parent[key] = rest
        else:
            parent[key] = None
            pending = (indent, key, parent)
            stack = [x for x in stack if x[0] < indent]
            stack.append((indent, parent))
    return root

def walk_keys(node, keys):
    if isinstance(node, dict):
        for k, v in node.items():
            if k.startswith('__'):
                continue
            keys.add(k)
            walk_keys(v, keys)
    elif isinstance(node, list):
        for i in node:
            walk_keys(i, keys)

all_errors = []
all_keys = {}
top_records = {}

for fname in sorted(os.listdir(MOD_YAML)):
    if not fname.endswith('.yaml'):
        continue
    lines = io.open(os.path.join(MOD_YAML, fname), encoding='utf-8').read().splitlines()
    errs = []
    doc = parse_document(lines, fname, errs)
    all_errors.extend(errs)
    for k in doc.keys():
        top_records[k] = fname
    keys = set()
    walk_keys(doc, keys)
    keys -= set(doc.keys())          # 顶层是记录名，不算字段名
    for k in keys:
        all_keys.setdefault(k, set()).add(fname)

p("顶层记录数: %d" % len(top_records))

bad = {k: v for k, v in all_keys.items() if k not in vanilla_fields and k not in ('$type', '$base')}
p()
p("=== 字段名在原版 .tweak 中不存在（需人工确认）===")
if bad:
    for k in sorted(bad):
        p("  %-42s <- %s" % (k, ','.join(sorted(bad[k]))))
else:
    p("  （无）")

p()
p("=== 结构问题 ===")
if all_errors:
    for e in all_errors:
        p("  " + e)
else:
    p("  （无）")

p()
p("=== 记录清单 ===")
for r in sorted(top_records):
    p("  %-48s %s" % (r, top_records[r]))

io.open(REPORT, "w", encoding="utf-8").write("\n".join(out))
print("顶层记录数:", len(top_records))
print("字段名问题:", len(bad), sorted(bad)[:20])
print("结构问题:", len(all_errors), all_errors[:6])
print("报告:", REPORT)
