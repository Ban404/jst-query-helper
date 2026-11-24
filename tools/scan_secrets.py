#!/usr/bin/env python3
"""全仓隐私扫描：确保没有二进制、真实凭据、本机路径、真实序列号或真实数据文件。

CI 与本地都能跑；只读，不改动任何文件。退出码 0 = 干净，1 = 发现问题。
只用 Python 标准库。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 明确禁止出现在本仓库的敏感词（真实账号 / 人名 / 公司名 / 店铺 ID / 本机用户名 / 示例真 SN）
FORBIDDEN_LITERALS = [
    "24184",            # 本机 Windows 用户名 / 路径片段
    "瑞伦达", "范世泽",  # 真实公司 / 人名
    "1000137210",       # 真实店铺 ID
    "74CA60D3A1CA7",    # 早期文档里用过的真实序列号示例
    "jst-open-platform-connections",  # 真实连接记录文件名
]

# 通用敏感模式（宁可误报也不漏报；误报时在文档里用占位符规避）
PATTERNS = [
    ("JWT/token 字面量", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.")),
    ("Windows 用户目录绝对路径", re.compile(r"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+")),
    ("WorkBuddy 会话绝对路径", re.compile(r"WorkBuddy[/\\]20\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}")),
    ("疑似手机号", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("疑似身份证号", re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")),
]

TEXT_EXT = {".md", ".py", ".mjs", ".js", ".json", ".yml", ".yaml", ".svg", ".txt", ".example"}
BINARY_EXT = {".exe", ".dll", ".so", ".dylib", ".bin", ".db", ".pyc", ".zip", ".msi", ".dmg"}
ALLOW_DIRS = {".git", "__pycache__", ".pytest_cache", "dist", "_verify"}
# 这些文件即使命中字面量也放行（本文件自身、即用于检测这些词）
SELF = {"tools/scan_secrets.py", "tools/verify_offline.py"}


def scan():
    issues = []
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ALLOW_DIRS]
        for fn in files:
            full = os.path.join(folder, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            ext = os.path.splitext(fn)[1].lower()
            if ext in BINARY_EXT:
                issues.append((rel, "二进制文件：" + fn))
                continue
            if ext not in TEXT_EXT:
                continue
            try:
                with open(full, encoding="utf-8") as fh:
                    text = fh.read()
            except Exception:
                continue
            if rel in SELF:
                continue
            for word in FORBIDDEN_LITERALS:
                if word in text:
                    issues.append((rel, "敏感字面量：" + word))
            for label, pattern in PATTERNS:
                m = pattern.search(text)
                if m:
                    issues.append((rel, label + "：" + m.group(0)[:24]))
    return issues


def main():
    issues = scan()
    if issues:
        print("发现 %d 处需要处理：" % len(issues))
        for rel, why in issues[:50]:
            print("  [!] %s  ->  %s" % (rel, why))
        return 1
    print("隐私扫描通过：无二进制、无凭据、无本机路径、无真实数据残留")
    return 0


if __name__ == "__main__":
    sys.exit(main())
