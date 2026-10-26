#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验仓库内所有 <skill>/SKILL.md 是否符合规范。

用法：在仓库根目录执行 python scripts/validate_skills.py
"""

import os
import re
import sys


def check(root="."):
    errors = []
    found = 0

    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        found += 1

        text = open(path, encoding="utf-8").read()
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            errors.append("%s: 缺少 YAML frontmatter" % name)
            continue

        fm = m.group(1)
        fm_name = re.search(r"^name:\s*(.+)$", fm, re.M)
        desc = re.search(r"^description:\s*(.+)$", fm, re.M)

        if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
            errors.append("%s: 目录名只允许小写字母、数字、连字符，且不超过 64 字符" % name)

        if not fm_name:
            errors.append("%s: frontmatter 缺少 name" % name)
        elif fm_name.group(1).strip() != name:
            errors.append(
                "%s: name 与目录名不一致（%s）" % (name, fm_name.group(1).strip())
            )

        if not desc:
            errors.append("%s: frontmatter 缺少 description" % name)
        else:
            n = len(desc.group(1).strip())
            if not 1 <= n <= 1024:
                errors.append("%s: description 长度 %d，应在 1-1024" % (name, n))

        body = text[m.end():].strip()
        if len(body) < 50:
            errors.append("%s: 正文过短" % name)

        # SKILL.md 里引用的 references 文件必须真实存在
        for ref in re.findall(r"`?(references/[A-Za-z0-9_.-]+)`?", body):
            if not os.path.isfile(os.path.join(root, name, ref)):
                errors.append("%s: 引用的 %s 不存在" % (name, ref))

    if found == 0:
        errors.append("没有找到任何 <skill>/SKILL.md")

    return found, errors


def main():
    found, errors = check()
    if errors:
        print("\n".join(errors))
        return 1
    print("OK：%d 个技能通过校验" % found)
    return 0


if __name__ == "__main__":
    sys.exit(main())
